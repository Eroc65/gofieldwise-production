from __future__ import annotations

import time
import asyncio

from app.core.db import Base, engine
from app.core.db import SessionLocal
from app.models.crm_hub import CRMConfiguration, CRMProvider, HandoffStatus, IntegrationMode, IntakeCapture, IntakeType
import app.models.core  # noqa: F401
import app.models.crm_hub  # noqa: F401
import app.models.user  # noqa: F401
from app.services.crm_adapter import HandoffMethod, HandoffResult
from app.services.token_crypto import decrypt_secret, encrypt_secret


def _auth_headers(client, email: str, password: str, org_name: str = "Jobber Phase B Org"):
    unique_email = email.replace("@", f"+{int(time.time() * 1000)}@")
    signup = client.post(
        "/api/auth/signup",
        json={"email": unique_email, "password": password, "organization_name": org_name},
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


def _ensure_crm_tables():
    Base.metadata.create_all(bind=engine)


def test_token_crypto_round_trip():
    value = "secret-token"
    encrypted = encrypt_secret(value)
    assert encrypted.startswith("enc:v1:")
    assert decrypt_secret(encrypted) == value


def test_jobber_oauth_callback_persists_encrypted_tokens(client, monkeypatch):
    _ensure_crm_tables()
    monkeypatch.setenv("JOBBER_CLIENT_ID", "jobber-client-id")
    monkeypatch.setenv("JOBBER_CLIENT_SECRET", "jobber-client-secret")
    monkeypatch.setenv("JOBBER_REDIRECT_URI", "https://app.example.com/api/crm-hub/jobber/oauth/callback")
    monkeypatch.setenv("JOBBER_OAUTH_STATE_SECRET", "test-secret")

    headers, me = _auth_headers(client, "jobber-enc@example.com", "password123!")
    start = client.get("/api/crm-hub/jobber/oauth/start", headers=headers)
    state = start.json()["state"]

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "access_token": "phase-b-access",
                "refresh_token": "phase-b-refresh",
                "expires_in": 3600,
            }

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse()

    import app.api.crm_hub as crm_hub_api
    import app.services.crm_hub as hub_service

    hub_service._hub_instance = None
    monkeypatch.setattr(crm_hub_api.httpx, "AsyncClient", _FakeAsyncClient)

    callback = client.get(f"/api/crm-hub/jobber/oauth/callback?code=test-code&state={state}")
    assert callback.status_code == 200, callback.text

    db = SessionLocal()
    try:
        cfg = (
            db.query(CRMConfiguration)
            .filter(
                CRMConfiguration.organization_id == me["organization_id"],
                CRMConfiguration.crm_provider == CRMProvider.JOBBER,
            )
            .first()
        )
        assert cfg is not None
        assert str(cfg.config_data.get("access_token", "")).startswith("enc:v1:")
        assert str(cfg.config_data.get("refresh_token", "")).startswith("enc:v1:")
    finally:
        db.close()


def test_jobber_handoff_is_idempotent(client, monkeypatch):
    _ensure_crm_tables()
    headers, me = _auth_headers(client, "jobber-idem@example.com", "password123!")
    db = SessionLocal()
    try:
        cfg = CRMConfiguration(
            organization_id=me["organization_id"],
            crm_provider=CRMProvider.JOBBER,
            integration_mode=IntegrationMode.OAUTH,
            name="Jobber Live Config",
            config_data={
                "access_token": encrypt_secret("access-token"),
                "refresh_token": encrypt_secret("refresh-token"),
                "expires_at": "2099-01-01T00:00:00Z",
            },
            field_mapping={
                "caller_name": "firstName",
                "caller_phone": "phoneNumber",
                "service_type": "title",
            },
            is_active=True,
            handoff_status=HandoffStatus.LIVE,
            requires_approval=True,
            approved_by_user_id=me["id"],
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
        cfg_id = cfg.id
    finally:
        db.close()

    db = SessionLocal()
    try:
        intake = IntakeCapture(
            organization_id=me["organization_id"],
            crm_config_id=cfg_id,
            intake_type=IntakeType.INCOMING_CALL,
            source="test",
            caller_name="Idem Test",
            caller_phone="555-0100",
            service_type="HVAC",
            is_processed=False,
        )
        db.add(intake)
        db.commit()
        db.refresh(intake)
        intake_id = intake.id
    finally:
        db.close()

    calls = {"count": 0}

    async def _fake_send_intake(self, _intake):
        calls["count"] += 1
        return HandoffResult(
            success=True,
            method=HandoffMethod.API,
            external_record_id="jobber-123",
            payload_sent={"ok": True},
            response_received={"ok": True},
        )

    import app.services.crm_connectors as connectors
    import app.services.crm_hub as hub_service

    hub_service._hub_instance = None
    monkeypatch.setattr(connectors.JobberAdapter, "send_intake", _fake_send_intake)

    db = SessionLocal()
    try:
        hub = hub_service.CRMIntegrationHub(db)
        first = asyncio.run(hub.handoff_to_crm(intake_id, me["organization_id"]))
        second = asyncio.run(hub.handoff_to_crm(intake_id, me["organization_id"]))
        assert first is not None
        assert second is not None
    finally:
        db.close()

    assert first.id == second.id
    assert calls["count"] == 1
