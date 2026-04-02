from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "invoice@example.com"
_PASSWORD = "invoicepass"
_ORG = "Invoice Org"

_OTHER_EMAIL = "invoice_other@example.com"
_OTHER_PASSWORD = "invoiceother"
_OTHER_ORG = "Invoice Other Org"


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
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
def auth_headers(client):
    resp = client.post("/api/auth/login", data={"username": _EMAIL, "password": _PASSWORD})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="module")
def other_auth_headers(client):
    resp = client.post("/api/auth/login", data={"username": _OTHER_EMAIL, "password": _OTHER_PASSWORD})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _future(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past(days: int = 2) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _create_customer_and_job(client, headers):
    customer = client.post(
        "/api/customers",
        json={"name": "Invoice Customer", "phone": "555-1111"},
        headers=headers,
    )
    assert customer.status_code == 201

    job = client.post(
        "/api/jobs",
        json={"title": "Invoice Job", "customer_id": customer.json()["id"]},
        headers=headers,
    )
    assert job.status_code == 201
    return customer.json()["id"], job.json()["id"]


def test_invoice_routes_require_auth(client):
    assert client.get("/api/invoices").status_code == 401
    assert client.get("/api/invoices/overdue").status_code == 401
    assert client.get("/api/invoices/1").status_code == 401
    assert client.post("/api/invoices", json={"amount": 100, "job_id": 1}).status_code == 401
    assert client.patch("/api/invoices/1/status", json={"status": "paid"}).status_code == 401


def test_create_invoice_and_collection_reminder(client, auth_headers):
    _, job_id = _create_customer_and_job(client, auth_headers)

    resp = client.post(
        "/api/invoices",
        json={"amount": 275.5, "job_id": job_id, "due_at": _future(5)},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "unpaid"
    assert body["job_id"] == job_id
    assert body["due_at"] is not None

    # Invoice creation should auto-create a collection reminder for same job.
    reminders = client.get(f"/api/reminders?job_id={job_id}", headers=auth_headers)
    assert reminders.status_code == 200
    msgs = [r["message"] for r in reminders.json()]
    assert any("Collect payment for invoice" in m for m in msgs)


def test_create_invoice_rejects_foreign_org_job(client, auth_headers, other_auth_headers):
    _, other_job_id = _create_customer_and_job(client, other_auth_headers)
    resp = client.post(
        "/api/invoices",
        json={"amount": 99.0, "job_id": other_job_id, "due_at": _future(3)},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "Job not found" in resp.json()["detail"]


def test_list_and_get_invoices(client, auth_headers):
    _, job_id = _create_customer_and_job(client, auth_headers)
    created = client.post(
        "/api/invoices",
        json={"amount": 310.0, "job_id": job_id, "due_at": _future(10)},
        headers=auth_headers,
    ).json()

    lst = client.get("/api/invoices", headers=auth_headers)
    assert lst.status_code == 200
    assert any(i["id"] == created["id"] for i in lst.json())

    detail = client.get(f"/api/invoices/{created['id']}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == created["id"]


def test_mark_invoice_paid_sets_paid_at(client, auth_headers):
    _, job_id = _create_customer_and_job(client, auth_headers)
    created = client.post(
        "/api/invoices",
        json={"amount": 420.0, "job_id": job_id, "due_at": _future(1)},
        headers=auth_headers,
    ).json()

    paid = client.patch(
        f"/api/invoices/{created['id']}/status",
        json={"status": "paid"},
        headers=auth_headers,
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"
    assert paid.json()["paid_at"] is not None


def test_mark_invoice_paid_dismisses_collection_reminders(client, auth_headers):
    _, job_id = _create_customer_and_job(client, auth_headers)
    created = client.post(
        "/api/invoices",
        json={"amount": 510.0, "job_id": job_id, "due_at": _future(2)},
        headers=auth_headers,
    ).json()

    reminders_before = client.get(f"/api/reminders?job_id={job_id}", headers=auth_headers).json()
    target_before = [
        r for r in reminders_before if r["message"] == f"Collect payment for invoice #{created['id']}"
    ]
    assert target_before
    assert all(r["status"] == "pending" for r in target_before)

    paid = client.patch(
        f"/api/invoices/{created['id']}/status",
        json={"status": "paid"},
        headers=auth_headers,
    )
    assert paid.status_code == 200

    reminders_after = client.get(f"/api/reminders?job_id={job_id}", headers=auth_headers).json()
    target_after = [
        r for r in reminders_after if r["message"] == f"Collect payment for invoice #{created['id']}"
    ]
    assert target_after
    assert all(r["status"] == "dismissed" for r in target_after)


def test_reopen_invoice_reactivates_collection_reminders(client, auth_headers):
    _, job_id = _create_customer_and_job(client, auth_headers)
    created = client.post(
        "/api/invoices",
        json={"amount": 515.0, "job_id": job_id, "due_at": _future(3)},
        headers=auth_headers,
    ).json()

    paid = client.patch(
        f"/api/invoices/{created['id']}/status",
        json={"status": "paid"},
        headers=auth_headers,
    )
    assert paid.status_code == 200

    reopened = client.patch(
        f"/api/invoices/{created['id']}/status",
        json={"status": "unpaid"},
        headers=auth_headers,
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "unpaid"

    reminders = client.get(f"/api/reminders?job_id={job_id}", headers=auth_headers).json()
    target = [r for r in reminders if r["message"] == f"Collect payment for invoice #{created['id']}"]
    assert target
    assert all(r["status"] == "pending" for r in target)


def test_invalid_invoice_status_rejected(client, auth_headers):
    _, job_id = _create_customer_and_job(client, auth_headers)
    created = client.post(
        "/api/invoices",
        json={"amount": 120.0, "job_id": job_id, "due_at": _future(1)},
        headers=auth_headers,
    ).json()

    resp = client.patch(
        f"/api/invoices/{created['id']}/status",
        json={"status": "mystery"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_overdue_invoices_lists_unpaid_past_due(client, auth_headers):
    _, job_id = _create_customer_and_job(client, auth_headers)
    overdue = client.post(
        "/api/invoices",
        json={"amount": 180.0, "job_id": job_id, "due_at": _past(3)},
        headers=auth_headers,
    ).json()

    # Make a paid past-due invoice that must not appear
    paid = client.post(
        "/api/invoices",
        json={"amount": 181.0, "job_id": job_id, "due_at": _past(2)},
        headers=auth_headers,
    ).json()
    client.patch(f"/api/invoices/{paid['id']}/status", json={"status": "paid"}, headers=auth_headers)

    resp = client.get("/api/invoices/overdue", headers=auth_headers)
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()]
    assert overdue["id"] in ids
    assert paid["id"] not in ids


def test_invoice_org_scoping(client, auth_headers, other_auth_headers):
    _, other_job_id = _create_customer_and_job(client, other_auth_headers)
    foreign = client.post(
        "/api/invoices",
        json={"amount": 333.0, "job_id": other_job_id, "due_at": _future(7)},
        headers=other_auth_headers,
    ).json()

    resp = client.get(f"/api/invoices/{foreign['id']}", headers=auth_headers)
    assert resp.status_code == 404
