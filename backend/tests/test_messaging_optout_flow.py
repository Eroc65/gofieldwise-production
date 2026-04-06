from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Customer, Organization, Reminder, User, _utcnow


_AUTH_EMAIL = "sms-owner@example.com"
_AUTH_PASSWORD = "smsownerpass"
_AUTH_ORG = "SMS Suppression Org"


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        org = Organization(name=_AUTH_ORG)
        db.add(org)
        db.flush()

        owner = User(
            email=_AUTH_EMAIL,
            hashed_password=hash_password(_AUTH_PASSWORD),
            role="owner",
            organization_id=org.id,
        )
        db.add(owner)
        db.flush()

        customer = Customer(
            name="SMS Customer",
            phone="+16025550199",
            email="sms-customer@example.com",
            organization_id=org.id,
        )
        db.add(customer)
        db.flush()

        reminder = Reminder(
            message="Reactivation: Reply to rebook this week",
            channel="sms",
            status="pending",
            due_at=_utcnow() - timedelta(minutes=5),
            customer_id=customer.id,
            organization_id=org.id,
        )
        db.add(reminder)
        db.commit()
    finally:
        db.close()


def _auth_headers() -> dict[str, str]:
    with TestClient(app) as client:
        resp = client.post(
            "/api/auth/login",
            data={"username": _AUTH_EMAIL, "password": _AUTH_PASSWORD},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_twilio_stop_opt_out_suppresses_sms_dispatch() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        me = client.get("/api/auth/me", headers=headers)
        assert me.status_code == 200
        org_id = me.json()["organization_id"]

        inbound = client.post(
            f"/api/integrations/twilio/inbound/{org_id}",
            json={"from_phone": "+16025550199", "body": "STOP", "message_sid": "SMSTOP1"},
        )
        assert inbound.status_code == 200
        assert inbound.json()["action"] == "opted_out"

        run_due = client.post(
            "/api/reminders/run-due",
            json={"limit": 50, "dry_run": False},
            headers=headers,
        )
        assert run_due.status_code == 200
        payload = run_due.json()
        assert payload["failed_count"] >= 1

        reminders = client.get("/api/reminders", headers=headers)
        assert reminders.status_code == 200
        sms_rows = [r for r in reminders.json() if r["channel"] == "sms"]
        assert len(sms_rows) >= 1
        assert any(r["status"] == "dismissed" for r in sms_rows)


def test_comm_profile_can_be_saved_and_loaded() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        save = client.patch(
            "/api/org/comm-profile",
            json={
                "active": True,
                "twilio_account_sid": "AC123",
                "twilio_auth_token": "token123",
                "twilio_messaging_service_sid": "MG123",
                "twilio_phone_number": "+16025550000",
                "retell_agent_id": "agent_abc",
                "retell_phone_number": "+16025550001",
            },
            headers=headers,
        )
        assert save.status_code == 200

        get_profile = client.get("/api/org/comm-profile", headers=headers)
        assert get_profile.status_code == 200
        body = get_profile.json()
        assert body["active"] is True
        assert body["twilio_account_sid"] == "AC123"
        assert body["retell_agent_id"] == "agent_abc"
