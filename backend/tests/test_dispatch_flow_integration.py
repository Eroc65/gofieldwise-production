from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "dispatchflow@example.com"
_PASSWORD = "dispatchflowpass"
_ORG = "Dispatch Flow Org"


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        org = Organization(name=_ORG)
        db.add(org)
        db.flush()

        db.add(
            User(
                email=_EMAIL,
                hashed_password=hash_password(_PASSWORD),
                organization_id=org.id,
            )
        )
        db.commit()
    finally:
        db.close()


def _iso(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _auth_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/auth/login",
        data={"username": _EMAIL, "password": _PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dispatch_flow_conflict_next_slot_then_dispatch() -> None:
    client = TestClient(app)
    headers = _auth_headers(client)

    customer = client.post(
        "/api/customers",
        json={"name": "Flow Customer", "phone": "555-2323"},
        headers=headers,
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    technician = client.post(
        "/api/technicians",
        json={
            "name": "Flow Tech",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=headers,
    )
    assert technician.status_code == 201
    technician_id = technician.json()["id"]

    job1 = client.post(
        "/api/jobs",
        json={"title": "Flow Job One", "customer_id": customer_id},
        headers=headers,
    )
    job2 = client.post(
        "/api/jobs",
        json={"title": "Flow Job Two", "customer_id": customer_id},
        headers=headers,
    )
    assert job1.status_code == 201
    assert job2.status_code == 201
    job1_id = job1.json()["id"]
    job2_id = job2.json()["id"]

    scheduled_time = _iso(3)

    first_dispatch = client.patch(
        f"/api/jobs/{job1_id}/dispatch",
        json={"technician_id": technician_id, "scheduled_time": scheduled_time},
        headers=headers,
    )
    assert first_dispatch.status_code == 200

    conflict = client.get(
        "/api/jobs/scheduling/conflict",
        params={
            "technician_id": technician_id,
            "scheduled_time": scheduled_time,
            "buffer_minutes": 15,
        },
        headers=headers,
    )
    assert conflict.status_code == 200
    assert conflict.json()["conflict"] is True
    assert conflict.json()["conflicting_job_id"] == job1_id

    next_slot = client.get(
        "/api/jobs/scheduling/next-slot",
        params={
            "technician_id": technician_id,
            "requested_time": scheduled_time,
            "search_hours": 4,
            "step_minutes": 30,
            "buffer_minutes": 15,
        },
        headers=headers,
    )
    assert next_slot.status_code == 200
    body = next_slot.json()
    assert body["next_available_time"] is not None
    assert body["next_available_time"] != scheduled_time
    assert job1_id in body["conflicting_job_ids"]

    second_dispatch = client.patch(
        f"/api/jobs/{job2_id}/dispatch?buffer_minutes=15",
        json={
            "technician_id": technician_id,
            "scheduled_time": body["next_available_time"],
        },
        headers=headers,
    )
    assert second_dispatch.status_code == 200
    dispatched = second_dispatch.json()
    assert dispatched["status"] == "dispatched"
    assert dispatched["technician_id"] == technician_id
