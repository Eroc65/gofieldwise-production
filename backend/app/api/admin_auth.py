from __future__ import annotations

import hashlib
import hmac
import os
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.auth import hash_password, verify_password
from ..core.db import get_db
from ..core.jwt import create_access_token, decode_access_token
from ..models.core import AdminCredential, AdminPasswordReset, _utcnow


router = APIRouter()
security = HTTPBearer(auto_error=False)

RESET_EMAIL_TO = "erock004@gmail.com"
ADMIN_SCOPE = "admin_portal"


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminForgotPasswordRequest(BaseModel):
    username: str | None = None


class AdminResetPasswordRequest(BaseModel):
    token: str
    password: str


def _admin_username() -> str:
    return os.getenv("ADMIN_USERNAME", "").strip()


def _admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _reset_base_url() -> str:
    return (
        os.getenv("ADMIN_RESET_BASE_URL")
        or os.getenv("FRONTEND_BASE_URL")
        or os.getenv("NEXT_PUBLIC_SITE_URL")
        or "https://gofieldwise-production.vercel.app"
    ).rstrip("/")


def _send_reset_email(reset_url: str) -> bool:
    smtp_password = os.getenv("SMTP_PASSWORD") or os.getenv("GOFIELDWISE_EMAIL_PASSWORD")
    smtp_user = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER") or "biz@gofieldwise.com"
    smtp_host = os.getenv("SMTP_HOST") or "mail.privateemail.com"
    smtp_port = int(os.getenv("SMTP_PORT") or "465")
    smtp_from = os.getenv("SMTP_FROM") or smtp_user

    if not smtp_password:
        print("[admin-auth] Reset email not sent: missing SMTP_PASSWORD or GOFIELDWISE_EMAIL_PASSWORD.")
        return False

    message = EmailMessage()
    message["Subject"] = "GoFieldWise admin password reset"
    message["From"] = smtp_from
    message["To"] = os.getenv("ADMIN_RESET_EMAIL_TO") or RESET_EMAIL_TO
    message.set_content(
        "A password reset was requested for the GoFieldWise admin portal.\n\n"
        f"Reset link:\n{reset_url}\n\n"
        "This link expires in 30 minutes. If you did not request it, ignore this email."
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=20) as server:
        server.login(smtp_user, smtp_password)
        server.send_message(message)
    return True


def _credential_password_hash(db: Session, username: str) -> str | None:
    credential = db.query(AdminCredential).filter(AdminCredential.username == username).first()
    return credential.password_hash if credential else None


def _verify_admin_password(db: Session, username: str, password: str) -> bool:
    expected_username = _admin_username()
    env_password = _admin_password()
    if not expected_username or not env_password:
        raise HTTPException(
            status_code=503,
            detail="Admin portal credentials are not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD.",
        )
    if not hmac.compare_digest(username, expected_username):
        return False

    db_password_hash = _credential_password_hash(db, username)
    if db_password_hash:
        return verify_password(password, db_password_hash)
    return hmac.compare_digest(password, env_password)


def create_admin_token(username: str) -> str:
    return create_access_token(
        {"sub": username, "scope": ADMIN_SCOPE},
        expires_delta=timedelta(hours=8),
    )


def require_admin_session(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Admin session required.")
    payload = decode_access_token(credentials.credentials)
    if not payload or payload.get("scope") != ADMIN_SCOPE:
        raise HTTPException(status_code=401, detail="Invalid admin session.")
    if payload.get("sub") != _admin_username():
        raise HTTPException(status_code=401, detail="Invalid admin session.")
    return {"username": payload["sub"]}


@router.post("/admin/auth/login")
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)) -> dict:
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(status_code=422, detail="Username and password are required.")
    if not _verify_admin_password(db, username, payload.password):
        raise HTTPException(status_code=401, detail="Incorrect admin username or password.")
    return {
        "access_token": create_admin_token(username),
        "token_type": "bearer",
        "username": username,
    }


@router.post("/admin/auth/forgot-password")
def admin_forgot_password(payload: AdminForgotPasswordRequest, db: Session = Depends(get_db)) -> dict:
    expected_username = _admin_username()
    requested_username = (payload.username or expected_username).strip()

    if expected_username and requested_username == expected_username:
        raw_token = f"apr_{token_urlsafe(32)}"
        reset = AdminPasswordReset(
            token_hash=_token_hash(raw_token),
            username=expected_username,
            status="pending",
            expires_at=_utcnow() + timedelta(minutes=30),
        )
        db.add(reset)
        db.commit()
        reset_url = f"{_reset_base_url()}/admin?reset={raw_token}"
        try:
            sent = _send_reset_email(reset_url)
        except Exception as exc:  # pragma: no cover - depends on external SMTP
            sent = False
            print(f"[admin-auth] Reset email failed: {exc}")
        if os.getenv("APP_TESTING") == "1":
            return {"ok": True, "sent": sent, "reset_url": reset_url}

    return {
        "ok": True,
        "message": f"If the admin username is valid, a reset link was sent to {os.getenv('ADMIN_RESET_EMAIL_TO') or RESET_EMAIL_TO}.",
    }


@router.post("/admin/auth/reset-password")
def admin_reset_password(payload: AdminResetPasswordRequest, db: Session = Depends(get_db)) -> dict:
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    reset = db.query(AdminPasswordReset).filter(AdminPasswordReset.token_hash == _token_hash(payload.token)).first()
    if reset is None or reset.status != "pending":
        raise HTTPException(status_code=404, detail="Reset link is invalid or already used.")
    if reset.expires_at < _utcnow():
        reset.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Reset link has expired.")
    if reset.username != _admin_username():
        raise HTTPException(status_code=403, detail="Reset link does not match configured admin username.")

    credential = db.query(AdminCredential).filter(AdminCredential.username == reset.username).first()
    if credential is None:
        credential = AdminCredential(username=reset.username, password_hash=hash_password(payload.password))
        db.add(credential)
    else:
        credential.password_hash = hash_password(payload.password)
        credential.updated_at = _utcnow()
    reset.status = "used"
    reset.used_at = _utcnow()
    db.commit()

    return {
        "ok": True,
        "access_token": create_admin_token(reset.username),
        "token_type": "bearer",
        "username": reset.username,
    }
