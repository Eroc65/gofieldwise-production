from __future__ import annotations

import hashlib
import hmac
import os
from datetime import timedelta
from secrets import token_urlsafe
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..core.auth import hash_password
from ..core.db import get_db
from ..core.jwt import create_access_token
from ..models.core import OperatorInvite, Organization, User, _utcnow

router = APIRouter()


class OperatorInviteProvisionRequest(BaseModel):
    org_id: Optional[int] = None
    email: Optional[EmailStr] = None
    owner_name: Optional[str] = None
    business_name: Optional[str] = None
    phone: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    setup_base_url: Optional[str] = None
    expires_in_days: int = 14


class OperatorInviteVerifyRequest(BaseModel):
    key: str


class OperatorInviteRedeemRequest(BaseModel):
    key: str
    email: EmailStr
    password: str
    owner_name: str
    business_name: str
    phone: Optional[str] = None


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _new_operator_key() -> str:
    return f"op_{token_urlsafe(24)}"


def _setup_base_url(payload: OperatorInviteProvisionRequest) -> str:
    configured = (
        payload.setup_base_url
        or os.getenv("OPERATOR_SETUP_BASE_URL")
        or os.getenv("FRONTEND_BASE_URL")
        or os.getenv("NEXT_PUBLIC_APP_URL")
        or "https://gofieldwise.com"
    )
    return configured.rstrip("/")


def _verify_internal_secret(x_billing_sync_secret: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("OPERATOR_INVITE_SYNC_SECRET") or os.getenv("BILLING_SYNC_SECRET", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Operator invite provisioning is not configured")
    if not x_billing_sync_secret:
        raise HTTPException(status_code=401, detail="Missing X-Billing-Sync-Secret header")
    if not hmac.compare_digest(x_billing_sync_secret.strip(), expected.strip()):
        raise HTTPException(status_code=403, detail="Invalid provisioning secret")


def _load_invite_or_error(db: Session, raw_key: str) -> OperatorInvite:
    key = raw_key.strip()
    if not key:
        raise HTTPException(status_code=422, detail="Operator key is required")
    invite = db.query(OperatorInvite).filter(OperatorInvite.key_hash == _hash_key(key)).first()
    if invite is None:
        raise HTTPException(status_code=404, detail="Invalid operator key")
    if invite.redeemed_at is not None or invite.status == "redeemed":
        raise HTTPException(status_code=409, detail="Operator key has already been redeemed")
    if invite.expires_at < _utcnow():
        invite.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Operator key has expired")
    return invite


def _unique_org_name(db: Session, desired: str) -> str:
    base = desired.strip() or "GoFieldWise Operator"
    name = base
    suffix = 2
    while db.query(Organization).filter(Organization.name == name).first() is not None:
        name = f"{base} {suffix}"
        suffix += 1
    return name


@router.post("/operator/invite/provision")
def provision_operator_invite(
    payload: OperatorInviteProvisionRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_internal_secret),
):
    org: Optional[Organization] = None
    if payload.org_id is not None:
        org = db.query(Organization).filter(Organization.id == payload.org_id).first()
        if org is None:
            raise HTTPException(status_code=404, detail="Organization not found")

    raw_key = _new_operator_key()
    days = max(1, min(int(payload.expires_in_days or 14), 30))
    expires_at = _utcnow() + timedelta(days=days)
    setup_url = f"{_setup_base_url(payload)}/operator/setup?key={raw_key}"

    invite = OperatorInvite(
        key_hash=_hash_key(raw_key),
        email=str(payload.email) if payload.email else None,
        owner_name=(payload.owner_name or "").strip() or None,
        business_name=(payload.business_name or "").strip() or (org.name if org else None),
        phone=(payload.phone or "").strip() or None,
        stripe_customer_id=payload.stripe_customer_id,
        stripe_subscription_id=payload.stripe_subscription_id,
        setup_url=setup_url,
        expires_at=expires_at,
        organization_id=org.id if org else None,
        status="pending",
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return {
        "ok": True,
        "invite_id": invite.id,
        "org_id": invite.organization_id,
        "operator_key": raw_key,
        "setup_url": setup_url,
        "expires_at": expires_at,
    }


@router.post("/operator/invite/verify")
def verify_operator_invite(payload: OperatorInviteVerifyRequest, db: Session = Depends(get_db)):
    invite = _load_invite_or_error(db, payload.key)
    return {
        "valid": True,
        "invite_id": invite.id,
        "org_id": invite.organization_id,
        "email": invite.email,
        "owner_name": invite.owner_name,
        "business_name": invite.business_name,
        "phone": invite.phone,
        "expires_at": invite.expires_at,
    }


@router.post("/operator/invite/redeem")
def redeem_operator_invite(payload: OperatorInviteRedeemRequest, db: Session = Depends(get_db)):
    invite = _load_invite_or_error(db, payload.key)

    password = payload.password.strip()
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    email = str(payload.email).strip().lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    org: Optional[Organization] = None
    if invite.organization_id is not None:
        org = db.query(Organization).filter(Organization.id == invite.organization_id).first()
        if org is None:
            raise HTTPException(status_code=404, detail="Invite organization not found")

    if org is None:
        org = Organization(name=_unique_org_name(db, payload.business_name), is_active=True)
        db.add(org)
        db.flush()

    user = User(
        email=email,
        hashed_password=hash_password(password),
        role="owner",
        organization_id=org.id,
    )
    db.add(user)
    db.flush()

    invite.email = email
    invite.owner_name = payload.owner_name.strip()
    invite.business_name = payload.business_name.strip()
    invite.phone = (payload.phone or "").strip() or invite.phone
    invite.status = "redeemed"
    invite.redeemed_at = _utcnow()
    invite.redeemed_user_id = user.id
    invite.organization_id = org.id

    db.commit()
    db.refresh(user)

    access_token = create_access_token({"sub": user.email})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "organization_id": user.organization_id,
        },
        "organization": {
            "id": org.id,
            "name": org.name,
        },
        "redirect_to": "/connect-center",
    }
