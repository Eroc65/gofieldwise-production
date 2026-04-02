from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "digest@example.com"
_PASSWORD = "digestpass"
_ORG = "Digest Org"

_OTHER_EMAIL = "digest_other@example.com"
_OTHER_PASSWORD = "digestother"
_OTHER_ORG = "Digest Other Org"


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


def _create_customer(client: TestClient, headers, name: str = "Digest Customer"):
    resp = client.post(
        "/api/customers",
        json={"name": name, "phone": "555-5000"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_job(client: TestClient, headers, customer_id: int, title: str = "Digest Job"):
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


def test_daily_digest_requires_auth():
    client = TestClient(app)
    assert client.get("/api/reports/daily-digest").status_code == 401


def test_daily_digest_empty_org():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    result = client.get("/api/reports/daily-digest", headers=headers)
    assert result.status_code == 200

    body = result.json()
    assert body["summary"]["urgent_now"] == 0
    assert body["summary"]["today_actions"] == 0
    assert body["cash_risk"]["unpaid_invoices"] == 0
    assert body["cash_risk"]["outstanding_amount"] == 0.0
    assert body["sla"]["stale_dispatched_jobs"] == 0
    assert body["pipeline"]["new_leads"] == 0
    assert body["weekly_trends"]["new_leads_last_7d"] == 0
    assert body["weekly_trends"]["jobs_completed_last_7d"] == 0
    assert body["weekly_trends"]["payments_collected_last_7d_count"] == 0
    assert body["weekly_trends"]["payments_collected_last_7d_amount"] == 0.0
    assert len(body["recommended_actions"]) >= 1


def test_daily_digest_populated_snapshot():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    intake = client.post(
        "/api/leads/intake/1",
        json={"name": "Digest Lead", "phone": "555-5111", "source": "web_form"},
    )
    assert intake.status_code == 201

    customer = _create_customer(client, headers)
    stale_job = _create_job(client, headers, customer["id"], "Stale Job")

    stale_update = client.put(
        f"/api/jobs/{stale_job['id']}",
        json={"status": "dispatched", "scheduled_time": _past(3)},
        headers=headers,
    )
    assert stale_update.status_code == 200

    overdue_job = _create_job(client, headers, customer["id"], "Overdue Invoice Job")
    _create_invoice(client, headers, overdue_job["id"], 275.0, _past(15))

    paid_job = _create_job(client, headers, customer["id"], "Paid Invoice Job")
    paid_invoice = _create_invoice(client, headers, paid_job["id"], 125.0, _future(3))
    mark_paid = client.patch(
        f"/api/invoices/{paid_invoice['id']}/status",
        json={"status": "paid"},
        headers=headers,
    )
    assert mark_paid.status_code == 200

    client.post("/api/invoices/escalate-payments", headers=headers)
    client.post("/api/reports/sla-breaches/escalate", headers=headers)

    result = client.get("/api/reports/daily-digest", headers=headers)
    assert result.status_code == 200

    body = result.json()
    assert body["summary"]["urgent_now"] >= 1
    assert body["summary"]["today_actions"] >= 1
    assert body["cash_risk"]["unpaid_invoices"] == 1
    assert body["cash_risk"]["severe_overdue_invoices"] == 1
    assert body["cash_risk"]["outstanding_amount"] == 275.0
    assert body["sla"]["stale_dispatched_jobs"] == 1
    assert body["sla"]["pending_sla_alerts"] >= 1
    assert body["pipeline"]["new_leads"] == 1
    assert body["weekly_trends"]["new_leads_last_7d"] >= 1
    assert body["weekly_trends"]["jobs_completed_last_7d"] == 0
    assert body["weekly_trends"]["payments_collected_last_7d_count"] == 1
    assert body["weekly_trends"]["payments_collected_last_7d_amount"] == 125.0
    assert any("overdue" in msg.lower() or "stale" in msg.lower() for msg in body["recommended_actions"])


def test_daily_digest_org_isolation():
    client = TestClient(app)
    org1_headers = _auth_headers(client, _EMAIL, _PASSWORD)
    org2_headers = _auth_headers(client, _OTHER_EMAIL, _OTHER_PASSWORD)

    other_customer = _create_customer(client, org2_headers, "Other Digest Customer")
    other_job = _create_job(client, org2_headers, other_customer["id"], "Other Digest Job")
    _create_invoice(client, org2_headers, other_job["id"], 100.0, _future(2))

    org1 = client.get("/api/reports/daily-digest", headers=org1_headers)
    org2 = client.get("/api/reports/daily-digest", headers=org2_headers)

    assert org1.status_code == 200
    assert org2.status_code == 200

    body1 = org1.json()
    body2 = org2.json()

    assert body1["organization_id"] != body2["organization_id"]
    assert body2["cash_risk"]["unpaid_invoices"] == 1
    assert body1["cash_risk"]["unpaid_invoices"] >= 1
    assert body2["pipeline"]["new_leads"] == 0
