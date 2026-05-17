from app.core.db import Base, engine


ADMIN_EMAIL = "support@gofieldwise.com"
PASSWORD = "testpass123"


def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login(client, email=ADMIN_EMAIL):
    signup = client.post(
        "/api/auth/signup",
        json={
            "email": email,
            "password": PASSWORD,
            "organization_name": f"{email}-org",
            "role": "owner",
        },
    )
    assert signup.status_code == 200, signup.text

    login = client.post("/api/auth/login", data={"username": email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_monitoring_summary_includes_system_health_and_flows(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setenv("BILLING_SYNC_SECRET", "billing-secret")
    monkeypatch.setenv("OPERATOR_INVITE_SYNC_SECRET", "billing-secret")
    monkeypatch.setenv("CONNECT_SERVICE_KEY", "connect-secret")

    response = client.get("/api/admin/monitoring/summary", headers=_login(client))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "system_health" in payload
    assert payload["system_health"]["green_count"] >= 1
    assert payload["landing_page_health"]
    flow_ids = {flow["id"] for flow in payload["troubleshooting_flows"]}
    assert "stripe_operator_onboarding" in flow_ids
    assert "voice_ai_calls" in flow_ids
    assert "lead_pipeline" in flow_ids


def test_admin_system_healthcheck_returns_ai_helper_context(client):
    _reset_db()

    response = client.get("/api/admin/monitoring/system-health", headers=_login(client))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ai_helper_context"]["flow_count"] == len(payload["troubleshooting_flows"])
    assert payload["checks"]
    assert payload["system_health"]["status"] in {"green", "yellow", "red"}


def test_admin_monitoring_rejects_non_admin_user(client):
    _reset_db()

    response = client.get(
        "/api/admin/monitoring/system-health",
        headers=_login(client, email="not-admin@example.com"),
    )

    assert response.status_code == 403
