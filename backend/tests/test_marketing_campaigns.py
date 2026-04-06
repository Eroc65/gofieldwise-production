from datetime import timedelta
from datetime import datetime
from datetime import timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base
from app.core.db import SessionLocal
from app.core.db import engine
from app.main import app
from app.models.core import Customer
from app.models.core import Job
from app.models.core import Organization
from app.models.core import User
from app.models.core import _utcnow


_AUTH_EMAIL = "marketing-owner@example.com"
_AUTH_PASSWORD = "marketingpass"
_AUTH_ORG = "Marketing Test Org"


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        org = Organization(name=_AUTH_ORG)
        db.add(org)
        db.flush()

        owner = User(
            email=_AUTH_EMAIL,
            hashed_password=hash_password(_AUTH_PASSWORD),
            role="owner",
            organization_id=org.id,
        )
        db.add(owner)
        db.flush()

        customer_active = Customer(
            name="Active Customer",
            email="active@example.com",
            phone="555-0101",
            organization_id=org.id,
        )
        customer_stale = Customer(
            name="Stale Customer",
            email="stale@example.com",
            phone="555-0102",
            organization_id=org.id,
        )
        db.add(customer_active)
        db.add(customer_stale)
        db.flush()

        db.add(
            Job(
                title="Completed Service",
                status="completed",
                customer_id=customer_active.id,
                organization_id=org.id,
                completed_at=_utcnow(),
            )
        )

        db.add(
            Job(
                title="Old Completed Service",
                status="completed",
                customer_id=customer_stale.id,
                organization_id=org.id,
                completed_at=_utcnow() - timedelta(days=400),
            )
        )

        db.commit()
    finally:
        db.close()


def _auth_headers() -> dict[str, str]:
    with TestClient(app) as client:
        resp = client.post(
            "/api/auth/login",
            data={"username": _AUTH_EMAIL, "password": _AUTH_PASSWORD},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_review_harvester_campaign_launch_creates_recipients_and_reminders() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        create = client.post(
            "/api/marketing/campaigns",
            json={
                "name": "April Reviews",
                "kind": "review_harvester",
                "channel": "sms",
            },
            headers=headers,
        )
        assert create.status_code == 201
        campaign_id = create.json()["id"]

        launch = client.post(f"/api/marketing/campaigns/{campaign_id}/launch", headers=headers)
        assert launch.status_code == 200
        assert launch.json()["status"] == "launched"
        assert launch.json()["generated_recipients"] >= 1

        reminders = client.get("/api/reminders", headers=headers)
        assert reminders.status_code == 200
        review_messages = [r for r in reminders.json() if "review" in r["message"].lower()]
        assert len(review_messages) >= 1


def test_reactivation_campaign_launch_targets_stale_customers() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        create = client.post(
            "/api/marketing/campaigns",
            json={
                "name": "Winback June",
                "kind": "reactivation",
                "channel": "email",
                "lookback_days": 30,
            },
            headers=headers,
        )
        assert create.status_code == 201
        campaign_id = create.json()["id"]

        launch = client.post(f"/api/marketing/campaigns/{campaign_id}/launch", headers=headers)
        assert launch.status_code == 200
        assert launch.json()["generated_recipients"] >= 1

        list_resp = client.get("/api/marketing/campaigns", headers=headers)
        assert list_resp.status_code == 200
        assert any(c["id"] == campaign_id and c["status"] == "launched" for c in list_resp.json())

        reminders = client.get("/api/reminders", headers=headers)
        assert reminders.status_code == 200
        reactivation_msgs = [r for r in reminders.json() if "priority scheduling" in r["message"].lower()]
        assert len(reactivation_msgs) >= 1


def test_campaign_launch_is_not_relaunchable() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        create = client.post(
            "/api/marketing/campaigns",
            json={
                "name": "One-Time Launch",
                "kind": "review_harvester",
            },
            headers=headers,
        )
        assert create.status_code == 201
        campaign_id = create.json()["id"]

        first = client.post(f"/api/marketing/campaigns/{campaign_id}/launch", headers=headers)
        assert first.status_code == 200

        second = client.post(f"/api/marketing/campaigns/{campaign_id}/launch", headers=headers)
        assert second.status_code == 409


def test_review_harvester_auto_creates_sms_reminder_on_job_complete() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        create_customer = client.post(
            "/api/customers",
            json={"name": "Review Auto Customer", "email": "review-auto@example.com", "phone": "555-0190"},
            headers=headers,
        )
        assert create_customer.status_code == 201
        customer_id = create_customer.json()["id"]

        create_job = client.post(
            "/api/jobs",
            json={"title": "Review Auto Job", "customer_id": customer_id},
            headers=headers,
        )
        assert create_job.status_code == 201
        job_id = create_job.json()["id"]

        create_tech = client.post(
            "/api/technicians",
            json={"name": "Review Auto Tech"},
            headers=headers,
        )
        assert create_tech.status_code == 201
        technician_id = create_tech.json()["id"]

        dispatch_job = client.patch(
            f"/api/jobs/{job_id}/dispatch",
            json={
                "technician_id": technician_id,
                "scheduled_time": datetime.now(timezone.utc).isoformat(),
            },
            headers=headers,
        )
        assert dispatch_job.status_code == 200

        complete_job = client.patch(
            f"/api/jobs/{job_id}/complete",
            json={"completion_notes": "done"},
            headers=headers,
        )
        assert complete_job.status_code == 200

        reminders = client.get(f"/api/reminders?job_id={job_id}", headers=headers)
        assert reminders.status_code == 200
        sms_review = [
            r
            for r in reminders.json()
            if r["channel"] == "sms" and "review request" in r["message"].lower()
        ]
        assert len(sms_review) >= 1


def test_reactivation_engine_run_endpoint_queues_sms_for_stale_customers() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        run = client.post(
            "/api/marketing/reactivation/run",
            json={"lookback_days": 180, "limit": 100, "dry_run": False},
            headers=headers,
        )
        assert run.status_code == 200
        payload = run.json()
        assert payload["lookback_days"] == 180
        assert payload["queued_count"] >= 1

        reminders = client.get("/api/reminders", headers=headers)
        assert reminders.status_code == 200
        reactivation_msgs = [
            r for r in reminders.json() if r["channel"] == "sms" and r["message"].startswith("Reactivation:")
        ]
        assert len(reactivation_msgs) >= 1
