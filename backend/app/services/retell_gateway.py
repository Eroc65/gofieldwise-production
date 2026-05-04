from __future__ import annotations

import os
from typing import Any, cast

import httpx
from sqlalchemy.orm import Session

from ..models.core import CommunicationTenantProfile
from .twilio_gateway import normalize_us_phone


DEFAULT_DEMO_AGENT_ID = "agent_08985605972e2e1b5d8a92dd52"
DEFAULT_DEMO_FROM_NUMBER = "+16029320967"


def _resolve_retell_profile(db: Session, organization_id: int) -> dict[str, str]:
    profile = (
        db.query(CommunicationTenantProfile)
        .filter(CommunicationTenantProfile.organization_id == organization_id)
        .first()
    )
    tenant_agent_id = ""
    tenant_from_number = ""
    if profile and int(cast(int, profile.active)) == 1:
        tenant_agent_id = (cast(str | None, profile.retell_agent_id) or "").strip()
        tenant_from_number = normalize_us_phone(cast(str | None, profile.retell_phone_number))

    return {
        "api_key": (os.getenv("RETELL_API_KEY") or "").strip(),
        "agent_id": tenant_agent_id or (os.getenv("RETELL_AGENT_ID") or DEFAULT_DEMO_AGENT_ID).strip(),
        "from_number": tenant_from_number
        or normalize_us_phone(os.getenv("RETELL_FROM_NUMBER"))
        or DEFAULT_DEMO_FROM_NUMBER,
    }


def create_demo_phone_call(
    db: Session,
    *,
    organization_id: int,
    to_number: str,
    caller_name: str,
    caller_email: str,
    lead_id: int,
) -> tuple[bool, dict[str, Any] | None, str | None]:
    profile = _resolve_retell_profile(db, organization_id)
    api_key = profile["api_key"]
    if not api_key:
        return False, None, "RETELL_API_KEY is not configured"

    payload = {
        "from_number": profile["from_number"],
        "to_number": normalize_us_phone(to_number),
        "override_agent_id": profile["agent_id"],
        "metadata": {
            "caller_name": caller_name,
            "caller_email": caller_email,
            "demo_mode": True,
            "lead_id": lead_id,
            "organization_id": organization_id,
        },
        "retell_llm_dynamic_variables": {
            "caller_name": caller_name,
            "caller_email": caller_email,
            "demo_mode": "true",
        },
    }

    try:
        resp = httpx.post(
            "https://api.retellai.com/v2/create-phone-call",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=20.0,
        )
        if resp.status_code >= 400:
            return False, None, f"Retell error {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        call_id = (data or {}).get("call_id")
        if not call_id:
            detail = (
                (data or {}).get("message")
                or (data or {}).get("error")
                or "Retell did not return a call_id."
            )
            return False, data, str(detail)
        return True, data, None
    except Exception as exc:  # pragma: no cover
        return False, None, str(exc)
