from datetime import datetime, timedelta, timezone
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "runner@example.com"
_PASSWORD = "runnerpass"
_ORG = "Reminder Runner Org"


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


def _org_id() -> int:
    db: Session = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.name == _ORG).first()
        assert org is not None
        return int(cast(int, org.id))
    finally:
        db.close()


def _auth_headers(client: TestClient):
    resp = client.post("/api/auth/login", data={"username": _EMAIL, "password": _PASSWORD})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _past_iso(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def test_run_due_requires_auth():
    client = TestClient(app)
    resp = client.post("/api/reminders/run-due", json={"limit": 10})
    assert resp.status_code == 401


def test_run_due_dry_run_does_not_send():
    client = TestClient(app)
    headers = _auth_headers(client)

    create = client.post(
        "/api/reminders",
        json={"message": "Dry run candidate", "channel": "internal", "due_at": _past_iso()},
        headers=headers,
    )
    assert create.status_code == 201
    rid = create.json()["id"]

    run = client.post("/api/reminders/run-due", json={"limit": 50, "dry_run": True}, headers=headers)
    assert run.status_code == 200
    body = run.json()
    assert body["dry_run"] is True
    assert body["candidate_count"] >= 1
    assert body["sent_count"] == 0

    reminder = client.get(f"/api/reminders/{rid}", headers=headers).json()
    assert reminder["status"] == "pending"
    assert reminder["dispatch_attempts"] == 0


def test_run_due_sends_internal_and_fails_sms_without_contact():
    client = TestClient(app)
    headers = _auth_headers(client)
    org_id = _org_id()

    # Lead with no phone; SMS reminder should fail due to missing destination.
    lead = client.post(
        f"/api/leads/intake/{org_id}",
        json={"name": "No Phone Lead", "source": "web_form"},
    )
    assert lead.status_code == 201
    lead_id = lead.json()["id"]

    sms = client.post(
        "/api/reminders",
        json={"message": "Try sms", "channel": "sms", "due_at": _past_iso(), "lead_id": lead_id},
        headers=headers,
    )
    assert sms.status_code == 201
    sms_id = sms.json()["id"]

    internal = client.post(
        "/api/reminders",
        json={"message": "Internal due", "channel": "internal", "due_at": _past_iso()},
        headers=headers,
    )
    assert internal.status_code == 201
    internal_id = internal.json()["id"]

    run = client.post("/api/reminders/run-due", json={"limit": 50}, headers=headers)
    assert run.status_code == 200
    out = run.json()
    assert out["candidate_count"] >= 2
    assert out["sent_count"] >= 1
    assert out["failed_count"] >= 1

    sent_detail = client.get(f"/api/reminders/{internal_id}", headers=headers).json()
    assert sent_detail["status"] == "sent"
    assert sent_detail["dispatch_attempts"] >= 1
    assert sent_detail["sent_at"] is not None

    failed_detail = client.get(f"/api/reminders/{sms_id}", headers=headers).json()
    assert failed_detail["status"] == "pending"
    assert failed_detail["dispatch_attempts"] >= 1
    assert "Missing destination contact" in (failed_detail["last_dispatch_error"] or "")
