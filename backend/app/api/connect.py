from __future__ import annotations

import json
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..crud.lead import create_lead
from ..models.core import ConnectSettings, User, _utcnow
from ..services.retell_gateway import create_demo_phone_call
from ..services.twilio_gateway import normalize_us_phone, send_sms_message
from .auth import get_current_user


router = APIRouter()


class ConnectSettingsUpdate(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)
    completed: bool = False


class ConnectTestCallRequest(BaseModel):
    customer_name: str | None = None
    customer_phone: str | None = None


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


def _setting(settings: dict[str, Any], key: str) -> str:
    return str(settings.get(key) or "").strip()


@router.post("/connect/test-call")
def run_connect_test_call(
    payload: ConnectTestCallRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    org_id = int(cast(int, current_user.organization_id))
    profile = (
        db.query(ConnectSettings)
        .filter(ConnectSettings.organization_id == org_id)
        .first()
    )
    settings = _decode_settings(cast(str | None, profile.settings_json) if profile else None)

    business_name = _setting(settings, "business_name") or "GoFieldWise customer"
    trade_type = _setting(settings, "trade_type") or "home services"
    service_area = _setting(settings, "service_area") or "not provided"
    owner_phone = normalize_us_phone(_setting(settings, "owner_notification_phone"))
    customer_name = (payload.customer_name or _setting(settings, "test_customer_name") or "Test Customer").strip()
    customer_phone = normalize_us_phone(payload.customer_phone or _setting(settings, "test_customer_phone") or _setting(settings, "test_call_phone"))
    workflow_mode = _setting(settings, "workflow_mode") or "hybrid"
    emergency_rules = _setting(settings, "emergency_rules") or "No emergency rules configured yet."

    raw_message = (
        "Connect Center test AI call activation.\n"
        f"Business: {business_name}\n"
        f"Trade: {trade_type}\n"
        f"Service area: {service_area}\n"
        f"Workflow mode: {workflow_mode}\n"
        f"Emergency rules: {emergency_rules}\n"
        f"Test customer: {customer_name}\n"
        f"Test customer phone: {customer_phone or 'not provided'}"
    )
    lead = create_lead(
        db,
        {
            "name": customer_name,
            "phone": customer_phone or None,
            "source": "connect_test_call",
            "raw_message": raw_message,
            "notes": "Created by Connect Center test activation flow.",
        },
        org_id,
    )
    lead_id = int(cast(int, lead.id))

    owner_body = (
        f"GoFieldWise test lead created for {business_name}.\n"
        f"Lead #{lead_id}: {customer_name} {customer_phone or ''}\n"
        f"Trade: {trade_type}\n"
        f"Mode: {workflow_mode}\n"
        "Your AI front office setup is ready for review."
    )
    owner_sms_sent = False
    owner_sms_error = None
    owner_sms_id = None
    if owner_phone:
        owner_sms_sent, owner_sms_id, owner_sms_error = send_sms_message(
            db,
            organization_id=org_id,
            to_phone=owner_phone,
            body=owner_body,
        )

    customer_sms_sent = False
    customer_sms_error = None
    customer_sms_id = None
    if customer_phone:
        customer_sms_sent, customer_sms_id, customer_sms_error = send_sms_message(
            db,
            organization_id=org_id,
            to_phone=customer_phone,
            body=(
                f"Thanks for testing {business_name}'s AI front office. "
                "This is a confirmation message from GoFieldWise."
            ),
        )

    call_started = False
    call_id = None
    call_error = None
    if customer_phone:
        call_started, call_payload, call_error = create_demo_phone_call(
            db,
            organization_id=org_id,
            to_number=customer_phone,
            caller_name=customer_name,
            caller_email=str(cast(str, current_user.email)),
            lead_id=lead_id,
        )
        call_id = (call_payload or {}).get("call_id") if call_payload else None
    else:
        call_error = "Customer test phone is required to start an AI call."

    return {
        "ok": True,
        "lead_id": lead_id,
        "call_started": bool(call_started),
        "call_id": call_id,
        "owner_sms_sent": bool(owner_sms_sent),
        "owner_sms_id": owner_sms_id,
        "customer_sms_sent": bool(customer_sms_sent),
        "customer_sms_id": customer_sms_id,
        "message": (
            "Test lead created, SMS notifications processed, and AI call started."
            if call_started
            else "Test lead created and SMS notifications processed. AI call was simulated because Retell/Twilio call configuration is incomplete."
        ),
        "errors": {
            "owner_sms": owner_sms_error,
            "customer_sms": customer_sms_error,
            "call": call_error,
        },
    }


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
