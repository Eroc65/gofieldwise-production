from __future__ import annotations

import json
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models.core import ConnectSettings, User, _utcnow
from .auth import get_current_user


router = APIRouter()


class ConnectSettingsUpdate(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)
    completed: bool = False


def _decode_settings(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _serialize(profile: ConnectSettings, organization_id: int) -> dict[str, Any]:
    return {
        "organization_id": organization_id,
        "settings": _decode_settings(cast(str | None, profile.settings_json)),
        "completed": bool(profile.completed),
        "updated_at": profile.updated_at,
    }


@router.get("/connect/settings")
def get_connect_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    org_id = int(cast(int, current_user.organization_id))
    profile = (
        db.query(ConnectSettings)
        .filter(ConnectSettings.organization_id == org_id)
        .first()
    )
    if profile is None:
        return {
            "organization_id": org_id,
            "settings": {},
            "completed": False,
            "updated_at": None,
        }
    return _serialize(profile, org_id)


@router.patch("/connect/settings")
def update_connect_settings(
    payload: ConnectSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    org_id = int(cast(int, current_user.organization_id))
    try:
        settings_json = json.dumps(payload.settings, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Settings must be JSON serializable") from exc

    profile = (
        db.query(ConnectSettings)
        .filter(ConnectSettings.organization_id == org_id)
        .first()
    )
    if profile is None:
        profile = ConnectSettings(organization_id=org_id)
        db.add(profile)
        db.flush()

    profile.settings_json = settings_json
    profile.completed = bool(payload.completed)
    profile.updated_at = _utcnow()
    db.commit()
    db.refresh(profile)
    return _serialize(profile, org_id)
