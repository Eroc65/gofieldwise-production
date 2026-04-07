from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "payment@example.com"
_PASSWORD = "paymentpass"
_ORG = "Payment Escalation Org"


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


def _auth_headers(client: TestClient, email: str, password: str):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_customer(client: TestClient, headers):
    resp = client.post(
        "/api/customers",
        json={"name": "Payment Customer", "phone": "555-9000"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_job(client: TestClient, headers, customer_id):
    resp = client.post(
        "/api/jobs",
        json={"title": "Payment Test Job", "customer_id": customer_id},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def test_escalate_payments_requires_auth():
    client = TestClient(app)
    assert client.post("/api/invoices/escalate-payments").status_code == 401


def test_escalate_payments_returns_zero_on_no_invoices():
    """Test that escalation returns 0s when there are no unpaid invoices."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    result = client.post("/api/invoices/escalate-payments", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["initial_reminders_created"] == 0
    assert body["first_overdue_reminders_created"] == 0
    assert body["second_overdue_reminders_created"] == 0
    assert body["final_reminders_created"] == 0
    assert body["total_escalations"] == 0


def test_escalate_payments_initial_stage():
    """Test that invoices due today get initial payment reminders."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    
    # Create invoice due today
    import datetime
    today = datetime.datetime.now(datetime.UTC).isoformat()
    invoice = client.post(
        "/api/invoices",
        json={"amount": 500.0, "due_at": today, "job_id": job["id"]},
        headers=headers,
    )
    assert invoice.status_code == 201
    
    # Run escalation
    result = client.post("/api/invoices/escalate-payments", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["initial_reminders_created"] == 1
    assert body["total_escalations"] == 1


def test_escalate_payments_first_overdue_stage():
    """Test that invoices 3+ days overdue get first_overdue reminders."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    
    # Create invoice due 3 days ago
    import datetime
    three_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=3)).isoformat()
    invoice = client.post(
        "/api/invoices",
        json={"amount": 750.0, "due_at": three_days_ago, "job_id": job["id"]},
        headers=headers,
    )
    assert invoice.status_code == 201
    
    # Run escalation
    result = client.post("/api/invoices/escalate-payments", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["first_overdue_reminders_created"] == 1
    assert body["total_escalations"] == 1


def test_escalate_payments_second_overdue_stage():
    """Test that invoices 7+ days overdue get second_overdue reminders."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    
    # Create invoice due 7 days ago
    import datetime
    seven_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7)).isoformat()
    invoice = client.post(
        "/api/invoices",
        json={"amount": 1000.0, "due_at": seven_days_ago, "job_id": job["id"]},
        headers=headers,
    )
    assert invoice.status_code == 201
    
    # Run escalation
    result = client.post("/api/invoices/escalate-payments", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["second_overdue_reminders_created"] == 1
    assert body["total_escalations"] == 1


def test_escalate_payments_final_stage():
    """Test that invoices 14+ days overdue get final reminders."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    
    # Create invoice due 14 days ago
    import datetime
    fourteen_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=14)).isoformat()
    invoice = client.post(
        "/api/invoices",
        json={"amount": 1500.0, "due_at": fourteen_days_ago, "job_id": job["id"]},
        headers=headers,
    )
    assert invoice.status_code == 201
    
    # Run escalation
    result = client.post("/api/invoices/escalate-payments", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["final_reminders_created"] == 1
    assert body["total_escalations"] == 1


def test_escalate_payments_multiple_stages():
    """Test escalation with invoices at different stages."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    
    import datetime
    
    # Create multiple jobs and invoices at different stages
    for i in range(4):
        job = _create_job(client, headers, customer["id"])
        if i == 0:
            # Due today
            due_date = datetime.datetime.now(datetime.UTC).isoformat()
            amount = 100
        elif i == 1:
            # 3 days overdue
            due_date = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=3)).isoformat()
            amount = 200
        elif i == 2:
            # 7 days overdue
            due_date = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7)).isoformat()
            amount = 300
        else:
            # 14 days overdue
            due_date = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=14)).isoformat()
            amount = 400
        
        invoice = client.post(
            "/api/invoices",
            json={"amount": amount, "due_at": due_date, "job_id": job["id"]},
            headers=headers,
        )
        assert invoice.status_code == 201
    
    # Run escalation
    result = client.post("/api/invoices/escalate-payments", headers=headers)
    assert result.status_code == 200
    body = result.json()
    assert body["initial_reminders_created"] == 1
    assert body["first_overdue_reminders_created"] == 1
    assert body["second_overdue_reminders_created"] == 1
    assert body["final_reminders_created"] == 1
    assert body["total_escalations"] == 4


def test_invoice_stage_persists_after_escalation():
    """Test that invoice payment_reminder_stage is updated and persists."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    
    # Create invoice due today
    import datetime
    today = datetime.datetime.now(datetime.UTC).isoformat()
    invoice_resp = client.post(
        "/api/invoices",
        json={"amount": 500.0, "due_at": today, "job_id": job["id"]},
        headers=headers,
    )
    assert invoice_resp.status_code == 201
    invoice_id = invoice_resp.json()["id"]
    
    # Before escalation
    invoice_before = client.get(f"/api/invoices/{invoice_id}", headers=headers)
    assert invoice_before.json()["payment_reminder_stage"] == "none"
    
    # Run escalation
    client.post("/api/invoices/escalate-payments", headers=headers)
    
    # After escalation
    invoice_after = client.get(f"/api/invoices/{invoice_id}", headers=headers)
    assert invoice_after.json()["payment_reminder_stage"] == "initial"


def test_paid_invoice_not_escalated():
    """Test that paid invoices are not escalated."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    
    # Create invoice and mark it paid
    import datetime
    seven_days_ago = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7)).isoformat()
    invoice = client.post(
        "/api/invoices",
        json={"amount": 500.0, "due_at": seven_days_ago, "job_id": job["id"]},
        headers=headers,
    )
    assert invoice.status_code == 201
    invoice_id = invoice.json()["id"]
    
    # Mark as paid
    client.patch(
        f"/api/invoices/{invoice_id}/status",
        json={"status": "paid"},
        headers=headers,
    )
    
    # Run escalation
    result = client.post("/api/invoices/escalate-payments", headers=headers)
    assert result.status_code == 200
    body = result.json()
    # Should not escalate paid invoices
    assert body["total_escalations"] == 0


def test_paid_invoice_dismisses_escalation_reminders_and_reopen_reactivates():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])

    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    invoice = client.post(
        "/api/invoices",
        json={"amount": 620.0, "due_at": seven_days_ago, "job_id": job["id"]},
        headers=headers,
    )
    assert invoice.status_code == 201
    invoice_id = invoice.json()["id"]

    # Create overdue escalation reminder for this invoice.
    escalate = client.post("/api/invoices/escalate-payments", headers=headers)
    assert escalate.status_code == 200
    assert escalate.json()["second_overdue_reminders_created"] == 1

    reminders_before_pay = client.get(f"/api/reminders?job_id={job['id']}", headers=headers)
    assert reminders_before_pay.status_code == 200
    invoice_related_before = [
        r for r in reminders_before_pay.json() if f"invoice #{invoice_id}" in r["message"].lower()
    ]
    assert invoice_related_before
    assert all(r["status"] == "pending" for r in invoice_related_before)

    mark_paid = client.patch(
        f"/api/invoices/{invoice_id}/status",
        json={"status": "paid"},
        headers=headers,
    )
    assert mark_paid.status_code == 200

    reminders_after_pay = client.get(f"/api/reminders?job_id={job['id']}", headers=headers)
    assert reminders_after_pay.status_code == 200
    invoice_related_after_pay = [
        r for r in reminders_after_pay.json() if f"invoice #{invoice_id}" in r["message"].lower()
    ]
    assert invoice_related_after_pay
    assert all(r["status"] == "dismissed" for r in invoice_related_after_pay)

    reopen = client.patch(
        f"/api/invoices/{invoice_id}/status",
        json={"status": "unpaid"},
        headers=headers,
    )
    assert reopen.status_code == 200

    reminders_after_reopen = client.get(f"/api/reminders?job_id={job['id']}", headers=headers)
    assert reminders_after_reopen.status_code == 200
    invoice_related_after_reopen = [
        r for r in reminders_after_reopen.json() if f"invoice #{invoice_id}" in r["message"].lower()
    ]
    assert invoice_related_after_reopen
    assert all(r["status"] == "pending" for r in invoice_related_after_reopen)
