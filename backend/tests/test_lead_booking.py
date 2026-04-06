from datetime import datetime, timedelta, timezone
from typing import cast

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "leadbook@example.com"
_PASSWORD = "leadbookpass"
_ORG = "LeadBook Org"

_OTHER_EMAIL = "leadbook_other@example.com"
_OTHER_PASSWORD = "leadbookother"
_OTHER_ORG = "LeadBook Other Org"
_TECH_EMAIL = "leadbook_tech@example.com"
_TECH_PASSWORD = "leadbooktech"


def setup_module():
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
        db.add(User(email=_TECH_EMAIL, hashed_password=hash_password(_TECH_PASSWORD), role="technician", organization_id=org.id))
        db.add(User(email=_OTHER_EMAIL, hashed_password=hash_password(_OTHER_PASSWORD), organization_id=other_org.id))
        db.commit()
    finally:
        db.close()


def _org_id(name: str) -> int:
    db: Session = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.name == name).first()
        assert org is not None
        return int(cast(int, org.id))
    finally:
        db.close()


def _auth_headers(client: TestClient, email: str, password: str):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _future(hours: int = 4) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def test_book_lead_requires_auth():
    client = TestClient(app)
    resp = client.post(
        "/api/leads/1/book",
        json={"scheduled_time": _future(), "technician_id": 1},
    )
    assert resp.status_code == 401


def test_book_qualified_lead_dispatches_and_clears_booking_reminders():
    client = TestClient(app)
    org_id = _org_id(_ORG)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    tech = client.post(
        "/api/technicians",
        json={
            "name": "Tech One",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=headers,
    )
    assert tech.status_code == 201
    technician_id = tech.json()["id"]

    intake = client.post(
        f"/api/leads/intake/{org_id}",
        json={"name": "Booking Lead", "phone": "555-7100", "source": "web_form"},
    )
    assert intake.status_code == 201
    lead_id = intake.json()["id"]

    qual = client.post(
        f"/api/leads/{lead_id}/qualify",
        json={
            "emergency": True,
            "budget_confirmed": True,
            "requested_within_48h": True,
            "service_category": "hvac",
        },
        headers=headers,
    )
    assert qual.status_code == 200

    book = client.post(
        f"/api/leads/{lead_id}/book",
        json={"scheduled_time": _future(6), "technician_id": technician_id},
        headers=headers,
    )
    assert book.status_code == 200
    body = book.json()

    assert body["lead_id"] == lead_id
    assert body["job_status"] == "dispatched"
    assert body["technician_id"] == technician_id
    assert body["booking_reminders_dismissed"] >= 1

    lead_detail = client.get(f"/api/leads/{lead_id}", headers=headers)
    assert lead_detail.status_code == 200
    assert lead_detail.json()["status"] == "converted"

    reminders = client.get(f"/api/reminders?lead_id={lead_id}", headers=headers)
    assert reminders.status_code == 200
    pending_booking = [
        r
        for r in reminders.json()
        if r["status"] == "pending" and "Book job with" in r["message"]
    ]
    assert pending_booking == []


def test_book_rejects_non_qualified_lead():
    client = TestClient(app)
    org_id = _org_id(_ORG)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    tech = client.post(
        "/api/technicians",
        json={
            "name": "Tech Two",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=headers,
    )
    technician_id = tech.json()["id"]

    intake = client.post(
        f"/api/leads/intake/{org_id}",
        json={"name": "New Lead", "phone": "555-7200", "source": "manual"},
    )
    lead_id = intake.json()["id"]

    book = client.post(
        f"/api/leads/{lead_id}/book",
        json={"scheduled_time": _future(8), "technician_id": technician_id},
        headers=headers,
    )
    assert book.status_code == 422


def test_book_respects_org_scope_and_technician_scope():
    client = TestClient(app)
    org_id = _org_id(_ORG)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    other_headers = _auth_headers(client, _OTHER_EMAIL, _OTHER_PASSWORD)

    other_tech = client.post(
        "/api/technicians",
        json={
            "name": "Other Tech",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=other_headers,
    )
    assert other_tech.status_code == 201
    other_tech_id = other_tech.json()["id"]

    intake = client.post(
        f"/api/leads/intake/{org_id}",
        json={"name": "Scoped Lead", "phone": "555-7300", "source": "web_form"},
    )
    lead_id = intake.json()["id"]

    qual = client.post(
        f"/api/leads/{lead_id}/qualify",
        json={"emergency": False},
        headers=headers,
    )
    assert qual.status_code == 200

    cross_org = client.post(
        f"/api/leads/{lead_id}/book",
        json={"scheduled_time": _future(5), "technician_id": other_tech_id},
        headers=other_headers,
    )
    assert cross_org.status_code == 404

    bad_tech = client.post(
        f"/api/leads/{lead_id}/book",
        json={"scheduled_time": _future(5), "technician_id": other_tech_id},
        headers=headers,
    )
    assert bad_tech.status_code == 422


def test_book_rejects_technician_role():
    client = TestClient(app)
    org_id = _org_id(_ORG)
    owner_headers = _auth_headers(client, _EMAIL, _PASSWORD)
    tech_headers = _auth_headers(client, _TECH_EMAIL, _TECH_PASSWORD)

    tech = client.post(
        "/api/technicians",
        json={
            "name": "Book Tech",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=owner_headers,
    )
    technician_id = tech.json()["id"]

    intake = client.post(
        f"/api/leads/intake/{org_id}",
        json={"name": "Book Restricted", "phone": "555-7400", "source": "web_form"},
    )
    lead_id = intake.json()["id"]

    qual = client.post(
        f"/api/leads/{lead_id}/qualify",
        json={"emergency": True},
        headers=owner_headers,
    )
    assert qual.status_code == 200

    denied = client.post(
        f"/api/leads/{lead_id}/book",
        json={"scheduled_time": _future(6), "technician_id": technician_id},
        headers=tech_headers,
    )
    assert denied.status_code == 403
