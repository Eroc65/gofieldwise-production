from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Optional
from typing import cast

import httpx
from sqlalchemy.orm import Session

from ..models.core import CommunicationTenantProfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _resolve_twilio_profile(db: Session, organization_id: int) -> dict[str, str | None]:
    profile = (
        db.query(CommunicationTenantProfile)
        .filter(CommunicationTenantProfile.organization_id == organization_id)
        .first()
    )

    if profile and int(cast(int, profile.active)) == 1:
        return {
            "account_sid": cast(str | None, profile.twilio_account_sid),
            "auth_token": cast(str | None, profile.twilio_auth_token),
            "messaging_service_sid": cast(str | None, profile.twilio_messaging_service_sid),
            "from_phone": cast(str | None, profile.twilio_phone_number),
        }

    return {
        "account_sid": os.getenv("TWILIO_ACCOUNT_SID"),
        "auth_token": os.getenv("TWILIO_AUTH_TOKEN"),
        "messaging_service_sid": os.getenv("TWILIO_MESSAGING_SERVICE_SID"),
        "from_phone": os.getenv("TWILIO_PHONE_NUMBER"),
    }


def normalize_us_phone(value: str | None) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if text.startswith("+"):
        return "+" + re.sub(r"\D", "", text)

    digits = re.sub(r"\D", "", text)
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return text


def resolve_demo_connect_number(db: Session, organization_id: int) -> str:
    profile = (
        db.query(CommunicationTenantProfile)
        .filter(CommunicationTenantProfile.organization_id == organization_id)
        .first()
    )
    if profile and int(cast(int, profile.active)) == 1:
        tenant_number = normalize_us_phone(cast(str | None, profile.retell_phone_number))
        if tenant_number:
            return tenant_number

    configured = normalize_us_phone(os.getenv("TWILIO_DEMO_CONNECT_NUMBER"))
    if configured:
        return configured
    return "+16029320967"


def send_sms_message(
    db: Session,
    *,
    organization_id: int,
    to_phone: str,
    body: str,
) -> tuple[bool, str | None, str | None]:
    """Send an SMS via Twilio when configured, otherwise simulate send for local/dev.

    Returns: (ok, external_message_id, error)
    """
    profile = _resolve_twilio_profile(db, organization_id)
    account_sid = (profile.get("account_sid") or "").strip()
    auth_token = (profile.get("auth_token") or "").strip()
    messaging_service_sid = (profile.get("messaging_service_sid") or "").strip()
    from_phone = (profile.get("from_phone") or "").strip()

    strict_real_delivery = os.getenv("REQUIRE_REAL_SMS_DELIVERY", "").strip().lower() in {"1", "true", "yes", "on"}

    if not account_sid or not auth_token or (not messaging_service_sid and not from_phone):
        if strict_real_delivery:
            return False, None, "REQUIRE_REAL_SMS_DELIVERY is enabled but Twilio credentials are not configured"
        simulated_id = f"simulated-{organization_id}-{int(_utcnow().timestamp())}"
        return True, simulated_id, None

    payload = {
        "To": to_phone,
        "Body": body,
    }
    if messaging_service_sid:
        payload["MessagingServiceSid"] = messaging_service_sid
    else:
        payload["From"] = from_phone

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    try:
        resp = httpx.post(
            url,
            data=payload,
            auth=(account_sid, auth_token),
            timeout=20.0,
        )
        if resp.status_code >= 400:
            return False, None, f"Twilio error {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        sid = data.get("sid")
        return True, str(sid) if sid else None, None
    except Exception as exc:  # pragma: no cover
        return False, None, str(exc)


def start_demo_voice_call(
    db: Session,
    *,
    organization_id: int,
    to_phone: str | None,
    twiml_url: str,
) -> tuple[bool, str | None, str | None]:
    """Start an outbound Twilio voice call for the public demo flow.

    Returns: (ok, call_sid, error)
    """
    profile = _resolve_twilio_profile(db, organization_id)
    account_sid = (profile.get("account_sid") or "").strip()
    auth_token = (profile.get("auth_token") or "").strip()
    from_phone = (profile.get("from_phone") or "").strip()
    destination = normalize_us_phone(to_phone)

    if not destination:
        return False, None, "Phone number is required to start a demo call"
    if not account_sid or not auth_token or not from_phone:
        return False, None, "Twilio voice credentials are not configured"

    payload = {
        "To": destination,
        "From": from_phone,
        "Url": twiml_url,
        "Method": "GET",
    }
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls.json"
    try:
        resp = httpx.post(
            url,
            data=payload,
            auth=(account_sid, auth_token),
            timeout=20.0,
        )
        if resp.status_code >= 400:
            return False, None, f"Twilio voice error {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        sid = data.get("sid")
        return True, str(sid) if sid else None, None
    except Exception as exc:  # pragma: no cover
        return False, None, str(exc)
