from app.core.db import Base, engine


ADMIN_USERNAME = "owner-admin"
PASSWORD = "testpass123"


def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login(client, username=ADMIN_USERNAME, password=PASSWORD):
    login = client.post("/api/admin/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_admin_monitoring_summary_includes_system_health_and_flows(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)
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


def test_admin_system_healthcheck_returns_ai_helper_context(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)

    response = client.get("/api/admin/monitoring/system-health", headers=_login(client))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["ai_helper_context"]["flow_count"] == len(payload["troubleshooting_flows"])
    assert payload["checks"]
    assert payload["system_health"]["status"] in {"green", "yellow", "red"}


def test_admin_troubleshooting_doc_download(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)

    response = client.get("/api/admin/monitoring/troubleshooting-doc", headers=_login(client))

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/markdown")
    assert "GoFieldWise AI Helper Troubleshooting Playbook" in response.text
    assert "Stripe checkout to operator setup" in response.text


def test_admin_monitoring_requires_admin_session(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD", PASSWORD)

    response = client.get("/api/admin/monitoring/system-health")
    assert response.status_code == 401

    bad_login = client.post("/api/admin/auth/login", json={"username": "not-admin", "password": PASSWORD})
    assert bad_login.status_code == 401
