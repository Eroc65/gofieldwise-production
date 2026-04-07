from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "dashboard@example.com"
_PASSWORD = "dashboardpass"
_ORG = "Dashboard Org"

_OTHER_EMAIL = "dashboard_other@example.com"
_OTHER_PASSWORD = "dashboardother"
_OTHER_ORG = "Dashboard Other Org"


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


def _create_customer(client: TestClient, headers, name: str = "Dashboard Customer"):
    resp = client.post(
        "/api/customers",
        json={"name": name, "phone": "555-3000"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_job(client: TestClient, headers, customer_id: int, title: str = "Dashboard Job"):
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


def test_operational_dashboard_requires_auth():
    client = TestClient(app)
    assert client.get("/api/reports/operational-dashboard").status_code == 401


def test_operational_dashboard_empty_org_returns_zeroes():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    response = client.get("/api/reports/operational-dashboard", headers=headers)
    assert response.status_code == 200

    body = response.json()
    assert body["organization_id"] > 0
    assert body["lead_pipeline"]["total"] == 0
    assert body["job_status"]["total"] == 0
    assert body["invoice_summary"]["total"] == 0
    assert body["invoice_summary"]["unpaid_total_amount"] == 0.0
    assert body["invoice_summary"]["overdue_count"] == 0
    assert body["overdue_invoices"]["aging_buckets"]["current_not_due"]["count"] == 0
    assert body["sla_breaches"]["stale_dispatched_jobs"] == 0
    assert body["sla_breaches"]["severe_overdue_invoices"] == 0
    assert body["sla_breaches"]["pending_total_alerts"] == 0
    assert body["reminders"]["pending_total"] == 0
    assert body["revenue_metrics"]["total_invoiced"] == 0.0
    assert body["action_priorities"]["urgent_now"] == 0
    assert body["action_priorities"]["today"] == 0
    assert body["action_priorities"]["this_week"] == 0
    assert body["action_priorities"]["total_open_actions"] == 0


def test_operational_dashboard_metrics_and_escalation_breakdown():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    intake = client.post(
        "/api/leads/intake/1",
        json={"name": "Lead One", "phone": "555-3111", "source": "web_form"},
    )
    assert intake.status_code == 201

    customer = _create_customer(client, headers)

    paid_job = _create_job(client, headers, customer["id"], "Paid Job")
    paid_invoice = _create_invoice(client, headers, paid_job["id"], 300.0, _future(5))
    mark_paid = client.patch(
        f"/api/invoices/{paid_invoice['id']}/status",
        json={"status": "paid"},
        headers=headers,
    )
    assert mark_paid.status_code == 200

    overdue_job = _create_job(client, headers, customer["id"], "Overdue Job")
    _create_invoice(client, headers, overdue_job["id"], 200.0, _past(14))

    stale_job = _create_job(client, headers, customer["id"], "Stale Dispatch Job")
    stale_update = client.put(
        f"/api/jobs/{stale_job['id']}",
        json={
            "status": "dispatched",
            "scheduled_time": _past(3),
        },
        headers=headers,
    )
    assert stale_update.status_code == 200

    escalate = client.post("/api/invoices/escalate-payments", headers=headers)
    assert escalate.status_code == 200
    assert escalate.json()["final_reminders_created"] >= 1
    sla_escalate = client.post("/api/reports/sla-breaches/escalate", headers=headers)
    assert sla_escalate.status_code == 200

    dashboard = client.get("/api/reports/operational-dashboard", headers=headers)
    assert dashboard.status_code == 200

    body = dashboard.json()
    assert body["lead_pipeline"]["new"] == 1
    assert body["job_status"]["pending"] == 2
    assert body["invoice_summary"]["paid"] == 1
    assert body["invoice_summary"]["unpaid"] == 1
    assert body["invoice_summary"]["unpaid_total_amount"] == 200.0
    assert body["invoice_summary"]["overdue_count"] == 1
    assert body["overdue_invoices"]["14_plus_days_overdue"] >= 1
    assert body["overdue_invoices"]["total_overdue"] >= 1
    assert body["overdue_invoices"]["aging_buckets"]["days_8_14"]["count"] == 1
    assert body["overdue_invoices"]["aging_buckets"]["days_8_14"]["amount"] == 200.0
    assert body["sla_breaches"]["stale_dispatched_jobs"] == 1
    assert body["sla_breaches"]["severe_overdue_invoices"] == 1
    assert body["sla_breaches"]["pending_total_alerts"] >= 2
    assert body["revenue_metrics"]["total_invoiced"] == 500.0
    assert body["revenue_metrics"]["total_paid"] == 300.0
    assert body["revenue_metrics"]["outstanding"] == 200.0
    assert body["revenue_metrics"]["collection_rate_percent"] == 60.0
    assert body["action_priorities"]["urgent_now"] >= 1
    assert body["action_priorities"]["this_week"] >= 1
    assert body["action_priorities"]["total_open_actions"] >= 1


def test_operational_dashboard_org_isolation():
    client = TestClient(app)
    org1_headers = _auth_headers(client, _EMAIL, _PASSWORD)
    org2_headers = _auth_headers(client, _OTHER_EMAIL, _OTHER_PASSWORD)

    # Seed org 2 with one lead and one invoice.
    intake = client.post(
        "/api/leads/intake/2",
        json={"name": "Other Lead", "phone": "555-3222", "source": "web_form"},
    )
    assert intake.status_code == 201

    other_customer = _create_customer(client, org2_headers, "Other Customer")
    other_job = _create_job(client, org2_headers, other_customer["id"], "Other Job")
    _create_invoice(client, org2_headers, other_job["id"], 100.0, _future(2))

    org1_dashboard = client.get("/api/reports/operational-dashboard", headers=org1_headers)
    org2_dashboard = client.get("/api/reports/operational-dashboard", headers=org2_headers)

    assert org1_dashboard.status_code == 200
    assert org2_dashboard.status_code == 200

    org1_body = org1_dashboard.json()
    org2_body = org2_dashboard.json()

    assert org1_body["organization_id"] != org2_body["organization_id"]
    assert org2_body["lead_pipeline"]["total"] == 1
    assert org2_body["invoice_summary"]["total"] == 1
    assert org2_body["invoice_summary"]["unpaid_total_amount"] == 100.0
    assert org2_body["invoice_summary"]["overdue_count"] == 0
    assert org2_body["overdue_invoices"]["aging_buckets"]["current_not_due"]["count"] == 1
    assert org2_body["revenue_metrics"]["total_invoiced"] == 100.0
    assert org2_body["sla_breaches"]["pending_total_alerts"] == 0
    assert "action_priorities" in org2_body
    assert org1_body["invoice_summary"]["total"] > org2_body["invoice_summary"]["total"]
