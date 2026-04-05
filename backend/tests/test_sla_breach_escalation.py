from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "sla@example.com"
_PASSWORD = "slapass"
_ORG = "SLA Org"

_OTHER_EMAIL = "sla_other@example.com"
_OTHER_PASSWORD = "slaother"
_OTHER_ORG = "SLA Other Org"


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


def _auth_headers(client: TestClient, email: str, password: str):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _future(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _past(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _create_customer(client: TestClient, headers, name: str = "SLA Customer"):
    resp = client.post(
        "/api/customers",
        json={"name": name, "phone": "555-4000"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_job(client: TestClient, headers, customer_id: int, title: str = "SLA Job"):
    resp = client.post(
        "/api/jobs",
        json={"title": title, "customer_id": customer_id},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_invoice(client: TestClient, headers, job_id: int, amount: float, due_at: str):
    resp = client.post(
        "/api/invoices",
        json={"amount": amount, "job_id": job_id, "due_at": due_at},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_sla_escalation_requires_auth():
    client = TestClient(app)
    assert client.post("/api/reports/sla-breaches/escalate").status_code == 401


def test_sla_escalation_no_breaches_returns_zeroes():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    result = client.post("/api/reports/sla-breaches/escalate", headers=headers)
    assert result.status_code == 200

    body = result.json()
    assert body["stale_dispatched_jobs"] == 0
    assert body["severe_overdue_invoices"] == 0
    assert body["job_sla_alerts_created"] == 0
    assert body["invoice_sla_alerts_created"] == 0
    assert body["total_alerts_created"] == 0


def test_sla_escalation_creates_alerts_and_is_idempotent():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    customer = _create_customer(client, headers)

    # Create stale dispatched job (scheduled 3 days ago, still dispatched).
    stale_job = _create_job(client, headers, customer["id"], "Stale Dispatch Job")
    update_job = client.put(
        f"/api/jobs/{stale_job['id']}",
        json={
            "status": "dispatched",
            "scheduled_time": _past(3),
        },
        headers=headers,
    )
    assert update_job.status_code == 200

    # Create severely overdue invoice (14+ days).
    overdue_job = _create_job(client, headers, customer["id"], "Severe Overdue Job")
    _create_invoice(client, headers, overdue_job["id"], 450.0, _past(16))

    first = client.post("/api/reports/sla-breaches/escalate", headers=headers)
    assert first.status_code == 200
    first_body = first.json()

    assert first_body["stale_dispatched_jobs"] == 1
    assert first_body["severe_overdue_invoices"] == 1
    assert first_body["job_sla_alerts_created"] == 1
    assert first_body["invoice_sla_alerts_created"] == 1
    assert first_body["total_alerts_created"] == 2

    # Second run should not duplicate pending SLA reminders.
    second = client.post("/api/reports/sla-breaches/escalate", headers=headers)
    assert second.status_code == 200
    second_body = second.json()

    assert second_body["stale_dispatched_jobs"] == 1
    assert second_body["severe_overdue_invoices"] == 1
    assert second_body["job_sla_alerts_created"] == 0
    assert second_body["invoice_sla_alerts_created"] == 0
    assert second_body["total_alerts_created"] == 0


def test_sla_escalation_respects_org_isolation():
    client = TestClient(app)
    org1_headers = _auth_headers(client, _EMAIL, _PASSWORD)
    org2_headers = _auth_headers(client, _OTHER_EMAIL, _OTHER_PASSWORD)

    other_customer = _create_customer(client, org2_headers, "Other SLA Customer")
    other_job = _create_job(client, org2_headers, other_customer["id"], "Other Stale Dispatch")
    update_job = client.put(
        f"/api/jobs/{other_job['id']}",
        json={
            "status": "dispatched",
            "scheduled_time": _past(5),
        },
        headers=org2_headers,
    )
    assert update_job.status_code == 200

    org1_result = client.post("/api/reports/sla-breaches/escalate", headers=org1_headers)
    org2_result = client.post("/api/reports/sla-breaches/escalate", headers=org2_headers)

    assert org1_result.status_code == 200
    assert org2_result.status_code == 200

    org1_body = org1_result.json()
    org2_body = org2_result.json()

    # Org 1's stale job from prior test remains visible to org 1 only.
    assert org1_body["stale_dispatched_jobs"] >= 1
    assert org2_body["stale_dispatched_jobs"] == 1
    # Org 2 has only one stale job and no overdue invoices.
    assert org2_body["severe_overdue_invoices"] == 0
