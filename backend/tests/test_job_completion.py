from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "completion@example.com"
_PASSWORD = "completionpass"
_ORG = "Completion Org"
_OTHER_EMAIL = "completion_other@example.com"
_OTHER_PASSWORD = "completionother"
_OTHER_ORG = "Completion Other Org"


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


def _create_customer(client: TestClient, headers):
    resp = client.post(
        "/api/customers",
        json={"name": "Completion Customer", "phone": "555-8000"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_job(client: TestClient, headers, customer_id):
    resp = client.post(
        "/api/jobs",
        json={"title": "Completion Job", "customer_id": customer_id},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_technician(client: TestClient, headers):
    resp = client.post(
        "/api/technicians",
        json={
            "name": "Completion Tech",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _dispatch_job(client: TestClient, headers, job_id, tech_id, scheduled_time: str):
    resp = client.patch(
        f"/api/jobs/{job_id}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": scheduled_time},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


def test_complete_job_routes_require_auth():
    client = TestClient(app)
    assert client.patch("/api/jobs/1/complete", json={}).status_code == 401


def test_complete_dispatched_job():
    """Test basic job completion."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Dispatch job
    import datetime
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    dispatched = _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    assert dispatched["status"] == "dispatched"
    
    # Complete job
    completed = client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={"completion_notes": "Job completed successfully"},
        headers=headers,
    )
    assert completed.status_code == 200
    body = completed.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    assert body["completion_notes"] == "Job completed successfully"


def test_cannot_complete_non_dispatched_job():
    """Test that only dispatched jobs can be completed."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    
    # Try to complete job in 'pending' status
    result = client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={"completion_notes": "Test"},
        headers=headers,
    )
    assert result.status_code == 422
    assert "Cannot complete job" in result.json()["detail"]


def test_complete_job_creates_followup_reminder():
    """Test that completing a job creates a follow-up reminder."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Dispatch and complete
    import datetime
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    
    # Get reminders before completion
    reminders_before = client.get("/api/reminders", headers=headers)
    assert reminders_before.status_code == 200
    initial_count = len(reminders_before.json())
    
    # Complete job
    client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={},
        headers=headers,
    )
    
    # Verify reminders
    reminders_after = client.get("/api/reminders", headers=headers)
    assert reminders_after.status_code == 200
    # Should have same count or +1 (dismiss is not delete)
    assert len(reminders_after.json()) >= initial_count
    
    # Verify follow-up reminder was created
    all_reminders = reminders_after.json()
    followup_reminders = [r for r in all_reminders if "Follow up" in r["message"]]
    assert len(followup_reminders) > 0
    assert any(r["status"] == "pending" for r in followup_reminders)


def test_cannot_complete_completed_job():
    """Test that a completed job is terminal."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Dispatch and complete
    import datetime
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    
    completed = client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={},
        headers=headers,
    )
    assert completed.status_code == 200
    
    # Try to complete again
    result = client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={},
        headers=headers,
    )
    assert result.status_code == 422
    assert "Cannot complete job" in result.json()["detail"]


def test_complete_job_optional_notes():
    """Test completion with optional completion_notes."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Dispatch and complete without notes
    import datetime
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    
    completed = client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={},
        headers=headers,
    )
    assert completed.status_code == 200
    assert completed.json()["completion_notes"] is None


def test_dispatch_job_creates_completion_reminder():
    """Test that dispatching a job creates a completion reminder."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Get reminders before dispatch
    reminders_before = client.get("/api/reminders", headers=headers)
    assert reminders_before.status_code == 200
    initial_count = len(reminders_before.json())
    
    # Dispatch job
    import datetime
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    
    # Verify reminder was created
    reminders_after = client.get("/api/reminders", headers=headers)
    assert reminders_after.status_code == 200
    assert len(reminders_after.json()) == initial_count + 1
    
    # Verify the completion reminder
    completion_reminder = reminders_after.json()[-1]
    assert completion_reminder["status"] == "pending"
    assert completion_reminder["channel"] == "internal"
    assert "Mark" in completion_reminder["message"]
    assert "complete" in completion_reminder["message"]


def test_complete_job_dismisses_completion_reminder():
    """Test that completing a job dismisses the completion reminder."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Dispatch job (creates completion reminder)
    import datetime
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    
    # Get reminders for this job before completion
    reminders_before = client.get("/api/reminders", headers=headers)
    job_reminders_before = [r for r in reminders_before.json() if r.get("job_id") == job["id"]]
    completion_reminders_before = [r for r in job_reminders_before if "Mark" in r["message"] and r["status"] == "pending"]
    assert len(completion_reminders_before) > 0, "No pending completion reminder found"
    
    # Complete job
    client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={},
        headers=headers,
    )
    
    # Get reminders after completion
    reminders_after = client.get("/api/reminders", headers=headers)
    job_reminders_after = [r for r in reminders_after.json() if r.get("job_id") == job["id"]]
    completion_reminders_after = [r for r in job_reminders_after if "Mark" in r["message"]]
    
    # Verify all completion reminders for this job are now dismissed
    assert len(completion_reminders_after) > 0
    assert all(r["status"] == "dismissed" for r in completion_reminders_after)


def test_complete_job_creates_followup_reminder_after_dismissing_completion():
    """Test that completing dismisses completion reminder and creates follow-up."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Dispatch (creates completion reminder)
    import datetime
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    
    # Complete job (dismisses completion, creates follow-up)
    client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={},
        headers=headers,
    )
    
    # Get all reminders for this job
    reminders = client.get("/api/reminders", headers=headers).json()
    job_reminders = [r for r in reminders if r.get("job_id") == job["id"]]
    
    # Verify completion reminder is dismissed
    completion_reminders = [r for r in job_reminders if "Mark" in r["message"]]
    assert len(completion_reminders) > 0
    assert all(r["status"] == "dismissed" for r in completion_reminders)
    
    # Verify follow-up reminder is created
    followup_reminders = [r for r in job_reminders if "Follow up" in r["message"]]
    assert len(followup_reminders) > 0
    assert any(r["status"] == "pending" for r in followup_reminders)


def test_complete_job_with_approved_estimate_creates_invoice():
    """Test that completing a job with an approved estimate auto-creates an invoice."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Create and approve an estimate
    import datetime
    estimate = client.post(
        "/api/estimates",
        json={"amount": 500.0, "description": "Service work", "job_id": job["id"]},
        headers=headers,
    )
    assert estimate.status_code == 201
    estimate_id = estimate.json()["id"]
    
    approved = client.patch(
        f"/api/estimates/{estimate_id}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert approved.status_code == 200
    
    # Dispatch job
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    
    # Check invoices before completion
    invoices_before = client.get("/api/invoices", headers=headers)
    initial_count = len(invoices_before.json())
    
    # Complete job
    completed = client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={},
        headers=headers,
    )
    assert completed.status_code == 200
    
    # Verify invoice was created
    invoices_after = client.get("/api/invoices", headers=headers)
    assert len(invoices_after.json()) == initial_count + 1
    
    # Verify invoice details
    invoice = invoices_after.json()[-1]
    assert invoice["amount"] == 500.0
    assert invoice["status"] == "unpaid"
    assert invoice["job_id"] == job["id"]


def test_complete_job_without_estimate_no_invoice_created():
    """Test that completing a job without an estimate doesn't create an invoice."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Dispatch job (no estimate)
    import datetime
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    
    # Check invoices before completion
    invoices_before = client.get("/api/invoices", headers=headers)
    initial_count = len(invoices_before.json())
    
    # Complete job
    client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={},
        headers=headers,
    )
    
    # Verify no invoice was created
    invoices_after = client.get("/api/invoices", headers=headers)
    assert len(invoices_after.json()) == initial_count


def test_complete_job_with_unapproved_estimate_no_invoice():
    """Test that job completion with unapproved estimate doesn't auto-create invoice."""
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    
    customer = _create_customer(client, headers)
    job = _create_job(client, headers, customer["id"])
    tech = _create_technician(client, headers)
    
    # Create but don't approve an estimate
    import datetime
    estimate = client.post(
        "/api/estimates",
        json={"amount": 300.0, "description": "Unapproved work", "job_id": job["id"]},
        headers=headers,
    )
    assert estimate.status_code == 201
    
    # Dispatch job
    scheduled_time = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)).isoformat()
    _dispatch_job(client, headers, job["id"], tech["id"], scheduled_time)
    
    # Check invoices before completion
    invoices_before = client.get("/api/invoices", headers=headers)
    initial_count = len(invoices_before.json())
    
    # Complete job
    client.patch(
        f"/api/jobs/{job['id']}/complete",
        json={},
        headers=headers,
    )
    
    # Verify no invoice was created (estimate not approved)
    invoices_after = client.get("/api/invoices", headers=headers)
    assert len(invoices_after.json()) == initial_count

