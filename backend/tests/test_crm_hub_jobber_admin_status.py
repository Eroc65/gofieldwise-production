from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from app.core.db import Base, SessionLocal, engine
from app.models.crm_hub import CRMConfiguration, CRMProvider, HandoffStatus, IntegrationMode
import app.models.core  # noqa: F401
import app.models.crm_hub  # noqa: F401
import app.models.user  # noqa: F401
from app.services.token_crypto import encrypt_secret


def _auth_headers(client, email: str, password: str, org_name: str = "Jobber Admin Status Org", role: str = "owner"):
    unique_email = email.replace("@", f"+{int(time.time() * 1000)}@")
    signup = client.post(
        "/api/auth/signup",
        json={"email": unique_email, "password": password, "organization_name": org_name, "role": role},
    )
    assert signup.status_code in (200, 201), signup.text
    login = client.post(
        "/api/auth/login",
        data={"username": unique_email, "password": password},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    return {"Authorization": f"Bearer {token}"}, me.json()


def _ensure_tables():
    Base.metadata.create_all(bind=engine)


def test_jobber_admin_status_requires_owner_or_admin(client):
    _ensure_tables()
    headers, _me = _auth_headers(client, "jobber-tech@example.com", "password123!", role="technician")
    response = client.get("/api/crm-hub/admin/jobber/token-expiry", headers=headers)
    assert response.status_code == 403


def test_jobber_admin_status_returns_risk_buckets(client):
    _ensure_tables()
    headers, me = _auth_headers(client, "jobber-owner@example.com", "password123!", role="owner")

    now = datetime.now(timezone.utc)
    ok_expiry = (now + timedelta(hours=5)).isoformat()
    warn_expiry = (now + timedelta(minutes=30)).isoformat()
    critical_expiry = (now + timedelta(minutes=5)).isoformat()

    db = SessionLocal()
    try:
        db.add_all(
            [
                CRMConfiguration(
                    organization_id=me["organization_id"],
                    crm_provider=CRMProvider.JOBBER,
                    integration_mode=IntegrationMode.OAUTH,
                    name="Jobber OK",
                    config_data={
                        "access_token": encrypt_secret("tok-ok"),
                        "refresh_token": encrypt_secret("ref-ok"),
                        "expires_at": ok_expiry,
                    },
                    field_mapping={"caller_name": "firstName", "caller_phone": "phoneNumber", "service_type": "title"},
                    is_active=True,
                    handoff_status=HandoffStatus.LIVE,
                    requires_approval=True,
                ),
                CRMConfiguration(
                    organization_id=me["organization_id"],
                    crm_provider=CRMProvider.JOBBER,
                    integration_mode=IntegrationMode.OAUTH,
                    name="Jobber Warn",
                    config_data={
                        "access_token": encrypt_secret("tok-warn"),
                        "refresh_token": encrypt_secret("ref-warn"),
                        "expires_at": warn_expiry,
                    },
                    field_mapping={"caller_name": "firstName", "caller_phone": "phoneNumber", "service_type": "title"},
                    is_active=True,
                    handoff_status=HandoffStatus.LIVE,
                    requires_approval=True,
                ),
                CRMConfiguration(
                    organization_id=me["organization_id"],
                    crm_provider=CRMProvider.JOBBER,
                    integration_mode=IntegrationMode.OAUTH,
                    name="Jobber Critical",
                    config_data={
                        "access_token": encrypt_secret("tok-critical"),
                        "refresh_token": encrypt_secret("ref-critical"),
                        "expires_at": critical_expiry,
                    },
                    field_mapping={"caller_name": "firstName", "caller_phone": "phoneNumber", "service_type": "title"},
                    is_active=True,
                    handoff_status=HandoffStatus.LIVE,
                    requires_approval=True,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/crm-hub/admin/jobber/token-expiry?warning_seconds=3600&critical_seconds=900",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    risks = {item["name"]: item["risk"] for item in body["items"]}
    assert risks["Jobber OK"] == "ok"
    assert risks["Jobber Warn"] == "warning"
    assert risks["Jobber Critical"] == "critical"
