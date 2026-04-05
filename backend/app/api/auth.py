from secrets import token_urlsafe
import csv
import io
from datetime import timedelta
from typing import Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..core.auth import hash_password, verify_password
from ..core.db import get_db
from ..core.jwt import create_access_token, decode_access_token
from ..models.core import Organization, User, UserRoleAuditEvent, _utcnow
from ..schemas.organization import OrganizationOut
from ..schemas.user import UserCreate, UserOut
from ..schemas.user import UserRoleAuditListOut
from ..schemas.user import UserRoleUpdate

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
ALLOWED_USER_ROLES = {"owner", "admin", "dispatcher", "technician"}
ROLE_MANAGE_ALLOWED = {"owner", "admin"}


def _new_intake_key() -> str:
    return f"org_{token_urlsafe(12)}"


def normalize_user_role(role: str | None) -> str:
    if role is None:
        return "owner"
    normalized = role.strip().lower()
    if normalized not in ALLOWED_USER_ROLES:
        valid = ", ".join(sorted(ALLOWED_USER_ROLES))
        raise HTTPException(status_code=422, detail=f"Invalid role '{role}'. Allowed roles: {valid}.")
    return normalized


def _ensure_role_manager(current_user: User) -> None:
    user_role = normalize_user_role(cast(str | None, current_user.role))
    if user_role not in ROLE_MANAGE_ALLOWED:
        allowed = ", ".join(sorted(ROLE_MANAGE_ALLOWED))
        raise HTTPException(
            status_code=403,
            detail=f"Role '{user_role}' cannot manage user roles. Allowed roles: {allowed}.",
        )


def _ensure_not_last_owner_demotion(db: Session, current_user: User, target: User, new_role: str) -> None:
    current_target_role = normalize_user_role(cast(str | None, target.role))
    if current_target_role != "owner" or new_role == "owner":
        return

    owner_count = (
        db.query(User)
        .filter(
            User.organization_id == current_user.organization_id,
            User.role == "owner",
        )
        .count()
    )
    if owner_count <= 1:
        raise HTTPException(
            status_code=422,
            detail="Cannot demote the last owner in the organization.",
        )


def _record_role_change_event(
    db: Session,
    *,
    actor_user_id: int,
    target_user_id: int,
    from_role: str,
    to_role: str,
    organization_id: int,
    note: str | None = None,
) -> None:
    event = UserRoleAuditEvent(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        from_role=from_role,
        to_role=to_role,
        note=note,
        organization_id=organization_id,
    )
    db.add(event)


def _load_role_audit_rows(
    db: Session,
    *,
    organization_id: int,
    limit: int,
    actor_user_id: int | None = None,
    target_user_id: int | None = None,
    days: int | None = None,
) -> list[dict]:
    query = (
        db.query(UserRoleAuditEvent)
        .filter(UserRoleAuditEvent.organization_id == organization_id)
    )
    if actor_user_id is not None:
        query = query.filter(UserRoleAuditEvent.actor_user_id == actor_user_id)
    if target_user_id is not None:
        query = query.filter(UserRoleAuditEvent.target_user_id == target_user_id)
    if days is not None:
        cutoff = _utcnow() - timedelta(days=days)
        query = query.filter(UserRoleAuditEvent.created_at >= cutoff)

    events = (
        query.order_by(UserRoleAuditEvent.created_at.desc(), UserRoleAuditEvent.id.desc())
        .limit(limit)
        .all()
    )
    user_ids = {int(cast(int, e.actor_user_id)) for e in events}
    user_ids.update({int(cast(int, e.target_user_id)) for e in events})
    users = (
        db.query(User)
        .filter(User.organization_id == organization_id, User.id.in_(user_ids))
        .all()
        if user_ids
        else []
    )
    email_by_id = {int(cast(int, u.id)): str(cast(str, u.email)) for u in users}

    out: list[dict] = []
    for event in events:
        actor_id = int(cast(int, event.actor_user_id))
        target_id = int(cast(int, event.target_user_id))
        out.append(
            {
                "id": int(cast(int, event.id)),
                "actor_user_id": actor_id,
                "actor_email": email_by_id.get(actor_id),
                "target_user_id": target_id,
                "target_email": email_by_id.get(target_id),
                "from_role": str(cast(str, event.from_role)),
                "to_role": str(cast(str, event.to_role)),
                "note": event.note,
                "organization_id": int(cast(int, event.organization_id)),
                "created_at": event.created_at,
            }
        )
    return out

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    if not user.organization_name:
        raise HTTPException(status_code=400, detail="Organization name is required")

    organization = (
        db.query(Organization)
        .filter(Organization.name == user.organization_name)
        .first()
    )
    if organization is None:
        organization = Organization(name=user.organization_name, intake_key=_new_intake_key())
        db.add(organization)
        db.flush()

    db_user = User(
        email=user.email,
        hashed_password=hash_password(user.password),
        role=normalize_user_role(user.role),
        organization_id=organization.id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserOut])
def list_org_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_role_manager(current_user)
    return (
        db.query(User)
        .filter(User.organization_id == current_user.organization_id)
        .order_by(User.id.asc())
        .all()
    )


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_role_manager(current_user)

    target = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    new_role = normalize_user_role(payload.role)
    prior_role = normalize_user_role(cast(str | None, target.role))
    _ensure_not_last_owner_demotion(db, current_user, target, new_role)
    if prior_role == new_role:
        return target

    target.role = new_role
    _record_role_change_event(
        db,
        actor_user_id=int(cast(int, current_user.id)),
        target_user_id=int(cast(int, target.id)),
        from_role=prior_role,
        to_role=new_role,
        organization_id=int(cast(int, current_user.organization_id)),
        note="Role updated via /api/auth/users/{user_id}/role",
    )
    db.commit()
    db.refresh(target)
    return target


@router.get("/users/role-audit", response_model=UserRoleAuditListOut)
def role_audit_log(
    limit: int = Query(100, ge=1, le=500),
    actor_user_id: int | None = Query(None),
    target_user_id: int | None = Query(None),
    days: int | None = Query(None, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_role_manager(current_user)
    organization_id = int(cast(int, current_user.organization_id))
    events = _load_role_audit_rows(
        db,
        organization_id=organization_id,
        limit=limit,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        days=days,
    )
    return {
        "organization_id": organization_id,
        "total": len(events),
        "events": events,
    }


@router.get("/users/role-audit/export.csv")
def role_audit_export_csv(
    limit: int = Query(500, ge=1, le=5000),
    actor_user_id: int | None = Query(None),
    target_user_id: int | None = Query(None),
    days: int | None = Query(None, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_role_manager(current_user)
    organization_id = int(cast(int, current_user.organization_id))
    rows = _load_role_audit_rows(
        db,
        organization_id=organization_id,
        limit=limit,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        days=days,
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "created_at",
            "organization_id",
            "actor_user_id",
            "actor_email",
            "target_user_id",
            "target_email",
            "from_role",
            "to_role",
            "note",
        ]
    )
    for row in rows:
        created_at = row["created_at"]
        writer.writerow(
            [
                row["id"],
                created_at.isoformat() if created_at is not None else "",
                row["organization_id"],
                row["actor_user_id"],
                row["actor_email"] or "",
                row["target_user_id"],
                row["target_email"] or "",
                row["from_role"],
                row["to_role"],
                row["note"] or "",
            ]
        )

    csv_body = buffer.getvalue()
    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=role_audit_events.csv"},
    )

@router.get("/org", response_model=OrganizationOut)
def current_org(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    organization = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization