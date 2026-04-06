from __future__ import annotations

import os
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
