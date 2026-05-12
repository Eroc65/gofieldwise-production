from __future__ import annotations

import os
import time


def _ensure_crm_tables():
    from app.core.db import Base, engine
    import app.models.crm_hub  # noqa: F401
    import app.models.core  # noqa: F401
    import app.models.user  # noqa: F401

    Base.metadata.create_all(bind=engine)


def _auth_headers(client, email: str, password: str, org_name: str = "Jobber Org"):
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
    return {"Authorization": f"Bearer {token}"}


def test_jobber_oauth_start_returns_authorize_url(client, monkeypatch):
    monkeypatch.setenv("JOBBER_CLIENT_ID", "jobber-client-id")
    monkeypatch.setenv("JOBBER_REDIRECT_URI", "https://app.example.com/api/crm-hub/jobber/oauth/callback")
    monkeypatch.setenv("JOBBER_OAUTH_SCOPES", "read_clients write_clients")
    monkeypatch.setenv("JOBBER_OAUTH_STATE_SECRET", "test-secret")

    headers = _auth_headers(client, "jobber-start@example.com", "password123!")
    response = client.get("/api/crm-hub/jobber/oauth/start", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "authorize_url" in payload
    assert "client_id=jobber-client-id" in payload["authorize_url"]
    assert "state=" in payload["authorize_url"]


def test_jobber_oauth_callback_creates_config(client, monkeypatch):
    _ensure_crm_tables()
    monkeypatch.setenv("JOBBER_CLIENT_ID", "jobber-client-id")
    monkeypatch.setenv("JOBBER_CLIENT_SECRET", "jobber-client-secret")
    monkeypatch.setenv("JOBBER_REDIRECT_URI", "https://app.example.com/api/crm-hub/jobber/oauth/callback")
    monkeypatch.setenv("JOBBER_OAUTH_STATE_SECRET", "test-secret")

    headers = _auth_headers(client, "jobber-callback@example.com", "password123!")
    start = client.get("/api/crm-hub/jobber/oauth/start", headers=headers)
    state = start.json()["state"]

    class _FakeResponse:
        status_code = 200

        @staticmethod
        def json():
            return {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
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

    monkeypatch.setattr(crm_hub_api.httpx, "AsyncClient", _FakeAsyncClient)

    callback = client.get(f"/api/crm-hub/jobber/oauth/callback?code=test-code&state={state}")
    assert callback.status_code == 200, callback.text
    body = callback.json()
    assert body["ok"] is True
    assert body["crm_provider"] == "jobber"
    assert body["handoff_status"] == "ready"


def test_jobber_config_requires_mapping_contract(client):
    headers = _auth_headers(client, "jobber-map@example.com", "password123!")
    create = client.post(
        "/api/crm-hub/configs",
        headers=headers,
        json={
            "crm_provider": "jobber",
            "integration_mode": "oauth",
            "name": "Jobber Missing Mapping",
            "config_data": {"access_token": "abc"},
            "field_mapping": {},
        },
    )
    assert create.status_code == 400, create.text
    assert "Failed to create config" in create.text
