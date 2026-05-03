from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import cast

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "missedcall@example.com"
_PASSWORD = "missedcallpass"
_ORG = "Missed Call Org"


def _auth_headers(client: TestClient):
    resp = client.post("/api/auth/login", data={"username": _EMAIL, "password": _PASSWORD})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        org = Organization(name=_ORG)
        db.add(org)
        db.flush()
        db.add(User(email=_EMAIL, hashed_password=hash_password(_PASSWORD), organization_id=org.id))
        db.commit()
    finally:
        db.close()


def _get_org_id() -> int:
    db: Session = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.name == _ORG).first()
        assert org is not None
        return int(cast(int, org.id))
    finally:
        db.close()


def _get_org_intake_key() -> str:
    db: Session = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.name == _ORG).first()
        assert org is not None
        return str(cast(str, org.intake_key))
    finally:
        db.close()


def test_missed_call_creates_lead_and_immediate_reminder():
    client = TestClient(app)
    org_id = _get_org_id()
    headers = _auth_headers(client)

    resp = client.post(
        f"/api/leads/intake/missed-call/{org_id}",
        json={"phone": "555-4000", "name": "Caller A", "call_sid": "CA123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deduplicated"] is False
    assert body["reminder_created"] is True
    assert body["lead"]["source"] == "missed_call"

    lead_id = body["lead"]["id"]
    reminders = client.get(f"/api/reminders?lead_id={lead_id}", headers=headers)
    assert reminders.status_code == 200
    assert len(reminders.json()) >= 1


def test_missed_call_deduplicates_recent_phone_and_no_extra_reminder():
    client = TestClient(app)
    org_id = _get_org_id()
    headers = _auth_headers(client)

    first = client.post(
        f"/api/leads/intake/missed-call/{org_id}",
        json={"phone": "555-4001", "name": "Caller B", "call_sid": "CA200"},
    )
    assert first.status_code == 200
    lead_id = first.json()["lead"]["id"]

    before = client.get(f"/api/reminders?lead_id={lead_id}", headers=headers).json()

    second = client.post(
        f"/api/leads/intake/missed-call/{org_id}",
        json={"phone": "555-4001", "raw_message": "Second missed call", "call_sid": "CA201"},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["deduplicated"] is True
    assert body["reminder_created"] is False
    assert body["lead"]["id"] == lead_id

    after = client.get(f"/api/reminders?lead_id={lead_id}", headers=headers).json()
    assert len(after) == len(before)


def test_missed_call_unknown_org_404():
    client = TestClient(app)
    resp = client.post(
        "/api/leads/intake/missed-call/99999",
        json={"phone": "555-4999"},
    )
    assert resp.status_code == 404


def test_missed_call_by_key_creates_lead():
    client = TestClient(app)
    intake_key = _get_org_intake_key()

    resp = client.post(
        f"/api/leads/intake/missed-call/by-key/{intake_key}",
        json={"phone": "555-4555", "name": "Caller Key", "call_sid": "CAKEY1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["deduplicated"] is False
    assert body["lead"]["source"] == "missed_call"


def test_demo_call_intake_by_key_creates_lead_and_returns_transcript():
    client = TestClient(app)
    intake_key = _get_org_intake_key()

    resp = client.post(
        f"/api/leads/intake/demo-call/by-key/{intake_key}",
        json={
            "name": "Demo Caller",
            "email": "demo@example.com",
            "phone": "555-4777",
            "raw_message": "Needs an HVAC tune-up",
            "cta_name": "demo_call_request",
            "landing_page": "https://www.gofieldwise.com/demo",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["ok"] is True
    assert body["lead_id"] > 0
    assert body["call_sid"].startswith("DEMO")
    assert body["call_started"] is False

    transcript = client.get(f"/api/demo-call/transcript/{body['call_sid']}")
    assert transcript.status_code == 200
    assert len(transcript.json()["transcript"]) >= 1

    twiml = client.get(f"/api/demo-call/twiml/{body['lead_id']}")
    assert twiml.status_code == 200
    assert "GoFieldwise AI receptionist demo" in twiml.text
    assert "<Dial" in twiml.text
    assert "+16029320967" in twiml.text


def test_demo_call_intake_starts_twilio_call_when_configured(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 201
        text = '{"sid":"CA123"}'

        def json(self):
            return {"sid": "CA123"}

    def fake_post(url, data, auth, timeout):
        calls.append({"url": url, "data": data, "auth": auth, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "AC123")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "secret")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "+16029320967")
    monkeypatch.setattr("app.services.twilio_gateway.httpx.post", fake_post)

    client = TestClient(app)
    intake_key = _get_org_intake_key()
    resp = client.post(
        f"/api/leads/intake/demo-call/by-key/{intake_key}",
        json={"name": "Demo Caller", "phone": "6025550123", "email": "demo@example.com"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["call_started"] is True
    assert body["call_sid"] == "CA123"
    assert calls[0]["url"] == "https://api.twilio.com/2010-04-01/Accounts/AC123/Calls.json"
    assert calls[0]["data"]["To"] == "+16025550123"
    assert calls[0]["data"]["From"] == "+16029320967"
    assert calls[0]["data"]["Url"].endswith(f"/api/demo-call/twiml/{body['lead_id']}")


def test_demo_call_sms_summary_endpoint_matches_frontend_contract():
    client = TestClient(app)

    resp = client.post("/api/demo-call/send-summary/1")

    assert resp.status_code == 200
    assert resp.json()["to"] == "(602) 932-0967"


def test_intent_and_support_chat_routes_do_not_404():
    client = TestClient(app)
    org_id = _get_org_id()

    intent = client.post(
        f"/api/leads/intake/intent/{org_id}",
        json={
            "cta_name": "see_pricing",
            "landing_page": "https://www.gofieldwise.com/demo",
            "raw_message": "Intent click captured for demo",
        },
    )
    assert intent.status_code == 201
    assert intent.json()["ok"] is True

    support = client.post(
        f"/api/leads/intake/support-chat/{org_id}",
        json={"message": "How does the demo call work?", "context_key": "demo", "trade": "hvac", "limit": 2},
    )
    assert support.status_code == 200
    assert support.json()["ok"] is True
    assert len(support.json()["messages"]) == 2


def test_public_demo_routes_allow_gofieldwise_cors_origin():
    client = TestClient(app)
    org_id = _get_org_id()

    resp = client.options(
        f"/api/leads/intake/demo-call/{org_id}",
        headers={
            "Origin": "https://www.gofieldwise.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "https://www.gofieldwise.com"
