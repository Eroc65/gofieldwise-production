"""Tests for the Follow-Up / Reminder Engine.

Covers:
- CRUD: create, list, filter, get, status update
- Auth enforcement on all routes
- Overdue queue (only pending, only past due_at)
- Invalid channel and status rejected
- Org scoping
- Auto-trigger: lead intake auto-creates a pending follow-up reminder
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import Base, SessionLocal, engine
from app.core.auth import hash_password
from app.main import app
from app.models.core import Organization, User
from typing import cast

_EMAIL = "remtest@example.com"
_PASSWORD = "remtestpass"
_ORG = "Reminder Test Org"

_OTHER_EMAIL = "remtest_other@example.com"
_OTHER_PASSWORD = "remtestother"
_OTHER_ORG = "Reminder Other Org"


def _future(hours: int = 2) -> str:
    dt = datetime.now(timezone.utc) + timedelta(hours=hours)
    return dt.isoformat()


def _past(hours: int = 2) -> str:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt.isoformat()


@pytest.fixture(scope="module", autouse=True)
def _setup():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        org = Organization(name=_ORG)
        other_org = Organization(name=_OTHER_ORG)
        db.add(org)
        db.add(other_org)
        db.flush()
        db.add(User(email=_EMAIL, hashed_password=hash_password(_PASSWORD), organization_id=org.id))
        db.add(User(email=_OTHER_EMAIL, hashed_password=hash_password(_OTHER_PASSWORD), organization_id=other_org.id))
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def org_id():
    db: Session = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.name == _ORG).first()
        assert org is not None
        return int(cast(int, org.id))
    finally:
        db.close()


@pytest.fixture(scope="module")
def other_org_id():
    db: Session = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.name == _OTHER_ORG).first()
        assert org is not None
        return int(cast(int, org.id))
    finally:
        db.close()


@pytest.fixture(scope="module")
def auth_headers(client):
    resp = client.post("/api/auth/login", data={"username": _EMAIL, "password": _PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="module")
def other_auth_headers(client):
    resp = client.post("/api/auth/login", data={"username": _OTHER_EMAIL, "password": _OTHER_PASSWORD})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------

def test_create_requires_auth(client):
    assert client.post("/api/reminders", json={"message": "x", "due_at": _future()}).status_code == 401


def test_list_requires_auth(client):
    assert client.get("/api/reminders").status_code == 401


def test_overdue_requires_auth(client):
    assert client.get("/api/reminders/overdue").status_code == 401


def test_get_requires_auth(client):
    assert client.get("/api/reminders/1").status_code == 401


def test_patch_status_requires_auth(client):
    assert client.patch("/api/reminders/1/status", json={"status": "sent"}).status_code == 401


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def test_create_reminder(client, auth_headers):
    resp = client.post(
        "/api/reminders",
        json={"message": "Call back the customer", "channel": "call", "due_at": _future()},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["channel"] == "call"
    assert body["message"] == "Call back the customer"


def test_create_reminder_invalid_channel(client, auth_headers):
    resp = client.post(
        "/api/reminders",
        json={"message": "Bad channel", "channel": "carrier_pigeon", "due_at": _future()},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_create_reminder_linked_to_lead(client, auth_headers, org_id):
    # Create a lead first via public intake
    lead_resp = client.post(
        f"/api/leads/intake/{org_id}",
        json={"name": "Reminder Lead", "phone": "555-7777", "source": "web_form"},
    )
    assert lead_resp.status_code == 201
    lead_id = lead_resp.json()["id"]

    resp = client.post(
        "/api/reminders",
        json={"message": "Follow up with lead", "due_at": _future(), "lead_id": lead_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["lead_id"] == lead_id


# ---------------------------------------------------------------------------
# List + filter
# ---------------------------------------------------------------------------

def test_list_reminders_returns_list(client, auth_headers):
    resp = client.get("/api/reminders", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert len(resp.json()) >= 1


def test_list_filter_by_status(client, auth_headers):
    resp = client.get("/api/reminders?status=pending", headers=auth_headers)
    assert resp.status_code == 200
    for r in resp.json():
        assert r["status"] == "pending"


# ---------------------------------------------------------------------------
# Get detail
# ---------------------------------------------------------------------------

def test_get_reminder_detail(client, auth_headers):
    created = client.post(
        "/api/reminders",
        json={"message": "Detail test", "due_at": _future()},
        headers=auth_headers,
    ).json()
    rid = created["id"]

    resp = client.get(f"/api/reminders/{rid}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == rid


def test_get_reminder_not_found(client, auth_headers):
    assert client.get("/api/reminders/99999", headers=auth_headers).status_code == 404


# ---------------------------------------------------------------------------
# Status update
# ---------------------------------------------------------------------------

def test_mark_reminder_sent(client, auth_headers):
    created = client.post(
        "/api/reminders",
        json={"message": "Send this one", "due_at": _future()},
        headers=auth_headers,
    ).json()
    rid = created["id"]

    resp = client.patch(f"/api/reminders/{rid}/status", json={"status": "sent"}, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "sent"
    assert body["sent_at"] is not None


def test_mark_reminder_dismissed(client, auth_headers):
    created = client.post(
        "/api/reminders",
        json={"message": "Dismiss this one", "due_at": _future()},
        headers=auth_headers,
    ).json()
    rid = created["id"]

    resp = client.patch(f"/api/reminders/{rid}/status", json={"status": "dismissed"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"


def test_invalid_status_returns_422(client, auth_headers):
    created = client.post(
        "/api/reminders",
        json={"message": "Invalid status test", "due_at": _future()},
        headers=auth_headers,
    ).json()
    rid = created["id"]

    resp = client.patch(f"/api/reminders/{rid}/status", json={"status": "exploded"}, headers=auth_headers)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Overdue queue
# ---------------------------------------------------------------------------

def test_overdue_queue_includes_past_pending(client, auth_headers):
    # Create a reminder that is already past due
    client.post(
        "/api/reminders",
        json={"message": "Already overdue", "due_at": _past(hours=3)},
        headers=auth_headers,
    )

    resp = client.get("/api/reminders/overdue", headers=auth_headers)
    assert resp.status_code == 200
    overdue = resp.json()
    assert len(overdue) >= 1
    for r in overdue:
        assert r["status"] == "pending"


def test_overdue_queue_excludes_future(client, auth_headers):
    """A reminder due in the future must not appear in the overdue queue."""
    future_rem = client.post(
        "/api/reminders",
        json={"message": "Future reminder", "due_at": _future(hours=48)},
        headers=auth_headers,
    ).json()

    resp = client.get("/api/reminders/overdue", headers=auth_headers)
    ids = [r["id"] for r in resp.json()]
    assert future_rem["id"] not in ids


def test_overdue_queue_excludes_sent(client, auth_headers):
    """A sent reminder must not reappear in the overdue queue."""
    created = client.post(
        "/api/reminders",
        json={"message": "Sent overdue", "due_at": _past(hours=1)},
        headers=auth_headers,
    ).json()
    rid = created["id"]
    client.patch(f"/api/reminders/{rid}/status", json={"status": "sent"}, headers=auth_headers)

    resp = client.get("/api/reminders/overdue", headers=auth_headers)
    ids = [r["id"] for r in resp.json()]
    assert rid not in ids


# ---------------------------------------------------------------------------
# Auto-trigger on lead intake
# ---------------------------------------------------------------------------

def test_lead_intake_auto_creates_reminder(client, auth_headers, org_id):
    """When a lead arrives via intake, a follow-up reminder is auto-created."""
    phone = f"555-{uuid.uuid4().hex[:4]}"
    lead_resp = client.post(
        f"/api/leads/intake/{org_id}",
        json={"name": "Auto Remind Me", "phone": phone, "source": "missed_call"},
    )
    assert lead_resp.status_code == 201
    lead_id = lead_resp.json()["id"]

    reminders = client.get(f"/api/reminders?lead_id={lead_id}", headers=auth_headers).json()
    assert len(reminders) >= 1
    assert reminders[0]["status"] == "pending"
    assert reminders[0]["lead_id"] == lead_id
    assert "Auto Remind Me" in reminders[0]["message"]


# ---------------------------------------------------------------------------
# Org scoping
# ---------------------------------------------------------------------------

def test_org_scoping_cannot_see_other_org_reminder(client, auth_headers, other_auth_headers):
    """A reminder created by org B is not visible to org A."""
    # org B creates a reminder
    other_rem = client.post(
        "/api/reminders",
        json={"message": "Other org secret", "due_at": _future()},
        headers=other_auth_headers,
    ).json()
    rid = other_rem["id"]

    # org A tries to fetch it — must get 404
    resp = client.get(f"/api/reminders/{rid}", headers=auth_headers)
    assert resp.status_code == 404
