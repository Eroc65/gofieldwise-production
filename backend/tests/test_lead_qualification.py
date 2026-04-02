from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "qualify@example.com"
_PASSWORD = "qualifypass"
_ORG = "Qualify Org"
_OTHER_EMAIL = "qualify_other@example.com"
_OTHER_PASSWORD = "qualifyother"
_OTHER_ORG = "Qualify Other Org"


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
        db.add(User(email=_OTHER_EMAIL, hashed_password=hash_password(_OTHER_PASSWORD), organization_id=other_org.id))
        db.commit()
    finally:
        db.close()


def _org_id(name: str) -> int:
    db: Session = SessionLocal()
    try:
        return db.query(Organization).filter(Organization.name == name).first().id
    finally:
        db.close()


def _auth_headers(client: TestClient, email: str, password: str):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_qualify_endpoint_requires_auth():
    client = TestClient(app)
    resp = client.post("/api/leads/1/qualify", json={"emergency": True})
    assert resp.status_code == 401


def test_qualify_sets_status_score_and_booking_reminder():
    client = TestClient(app)
    org_id = _org_id(_ORG)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    created = client.post(
        f"/api/leads/intake/missed-call/{org_id}",
        json={"phone": "555-5100", "name": "Urgent Lead"},
    )
    assert created.status_code == 200
    lead_id = created.json()["lead"]["id"]

    qualified = client.post(
        f"/api/leads/{lead_id}/qualify",
        json={
            "emergency": True,
            "budget_confirmed": True,
            "requested_within_48h": True,
            "service_category": "plumbing",
        },
        headers=headers,
    )
    assert qualified.status_code == 200
    body = qualified.json()
    assert body["booking_reminder_created"] is True
    assert body["lead"]["status"] == "qualified"
    assert body["lead"]["priority_score"] >= 80
    assert body["lead"]["qualified_at"] is not None

    reminders = client.get(f"/api/reminders?lead_id={lead_id}", headers=headers)
    msgs = [r["message"] for r in reminders.json()]
    assert any("Book job with" in msg for msg in msgs)


def test_qualify_rejects_terminal_statuses():
    client = TestClient(app)
    org_id = _org_id(_ORG)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    created = client.post(
        f"/api/leads/intake/{org_id}",
        json={"name": "Dismiss Me", "phone": "555-5101", "source": "manual"},
    )
    lead_id = created.json()["id"]
    dismissed = client.patch(f"/api/leads/{lead_id}/status", json={"status": "dismissed"}, headers=headers)
    assert dismissed.status_code == 200

    qualified = client.post(
        f"/api/leads/{lead_id}/qualify",
        json={"emergency": True},
        headers=headers,
    )
    assert qualified.status_code == 422


def test_qualify_respects_org_scoping():
    client = TestClient(app)
    org_id = _org_id(_ORG)
    other_headers = _auth_headers(client, _OTHER_EMAIL, _OTHER_PASSWORD)

    created = client.post(
        f"/api/leads/intake/{org_id}",
        json={"name": "Scoped Lead", "phone": "555-5102", "source": "web_form"},
    )
    lead_id = created.json()["id"]

    resp = client.post(
        f"/api/leads/{lead_id}/qualify",
        json={"emergency": True},
        headers=other_headers,
    )
    assert resp.status_code == 404
