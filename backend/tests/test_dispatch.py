from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "dispatch@example.com"
_PASSWORD = "dispatchpass"
_ORG = "Dispatch Org"

_OTHER_EMAIL = "dispatch_other@example.com"
_OTHER_PASSWORD = "dispatchother"
_OTHER_ORG = "Dispatch Other Org"
_CENTRAL = ZoneInfo("America/Chicago")


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

        db.add(
            User(
                email=_EMAIL,
                hashed_password=hash_password(_PASSWORD),
                organization_id=org.id,
            )
        )
        db.add(
            User(
                email=_OTHER_EMAIL,
                hashed_password=hash_password(_OTHER_PASSWORD),
                organization_id=other_org.id,
            )
        )
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


def _iso(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _setup_job_and_tech(client, headers):
    customer = client.post(
        "/api/customers",
        json={"name": "Dispatch Customer", "phone": "555-4321"},
        headers=headers,
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    tech = client.post(
        "/api/technicians",
        json={
            "name": "Dispatch Tech",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=headers,
    )
    assert tech.status_code == 201
    tech_id = tech.json()["id"]

    job = client.post(
        "/api/jobs",
        json={"title": "Dispatch Job", "customer_id": customer_id},
        headers=headers,
    )
    assert job.status_code == 201
    job_id = job.json()["id"]
    return job_id, tech_id


def test_dispatch_requires_auth(client):
    resp = client.patch(
        "/api/jobs/1/dispatch",
        json={"technician_id": 1, "scheduled_time": _iso()},
    )
    assert resp.status_code == 401


def test_dispatch_success_sets_fields(client, auth_headers):
    job_id, tech_id = _setup_job_and_tech(client, auth_headers)

    when = _iso(2)
    resp = client.patch(
        f"/api/jobs/{job_id}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": when},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["technician_id"] == tech_id
    assert body["status"] == "dispatched"
    assert body["scheduled_time"] is not None


def test_dispatch_rejects_technician_conflict(client, auth_headers):
    # Shared tech
    tech = client.post(
        "/api/technicians",
        json={
            "name": "Conflict Tech",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=auth_headers,
    )
    tech_id = tech.json()["id"]

    customer = client.post(
        "/api/customers",
        json={"name": "Conflict Customer", "phone": "555-8765"},
        headers=auth_headers,
    )
    customer_id = customer.json()["id"]

    job1 = client.post("/api/jobs", json={"title": "J1", "customer_id": customer_id}, headers=auth_headers).json()
    job2 = client.post("/api/jobs", json={"title": "J2", "customer_id": customer_id}, headers=auth_headers).json()

    when = _iso(3)
    ok = client.patch(
        f"/api/jobs/{job1['id']}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": when},
        headers=auth_headers,
    )
    assert ok.status_code == 200

    conflict = client.patch(
        f"/api/jobs/{job2['id']}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": when},
        headers=auth_headers,
    )
    assert conflict.status_code == 422
    assert "already has a job" in conflict.json()["detail"]


def test_dispatch_rejects_cross_org_technician(client, auth_headers, other_auth_headers):
    # Create technician in other org
    other_tech = client.post(
        "/api/technicians",
        json={
            "name": "Other Org Tech",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=other_auth_headers,
    )
    assert other_tech.status_code == 201
    other_tech_id = other_tech.json()["id"]

    # Create job in primary org
    customer = client.post(
        "/api/customers",
        json={"name": "Cross Org Customer", "phone": "555-1357"},
        headers=auth_headers,
    )
    job = client.post(
        "/api/jobs",
        json={"title": "Cross Org Job", "customer_id": customer.json()["id"]},
        headers=auth_headers,
    )
    job_id = job.json()["id"]

    resp = client.patch(
        f"/api/jobs/{job_id}/dispatch",
        json={"technician_id": other_tech_id, "scheduled_time": _iso(4)},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "Technician not found" in resp.json()["detail"]


def test_scheduling_conflict_requires_auth(client):
    resp = client.get(
        "/api/jobs/scheduling/conflict",
        params={"technician_id": 1, "scheduled_time": _iso(2)},
    )
    assert resp.status_code == 401


def test_scheduling_conflict_endpoint_reports_conflict(client, auth_headers):
    job_id, tech_id = _setup_job_and_tech(client, auth_headers)
    when = _iso(5)
    ok = client.patch(
        f"/api/jobs/{job_id}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": when},
        headers=auth_headers,
    )
    assert ok.status_code == 200

    check = client.get(
        "/api/jobs/scheduling/conflict",
        params={"technician_id": tech_id, "scheduled_time": when},
        headers=auth_headers,
    )
    assert check.status_code == 200
    body = check.json()
    assert body["conflict"] is True
    assert body["conflicting_job_id"] == job_id


def test_next_slot_requires_auth(client):
    resp = client.get(
        "/api/jobs/scheduling/next-slot",
        params={"technician_id": 1, "requested_time": _iso(2)},
    )
    assert resp.status_code == 401


def test_next_slot_returns_first_available_after_conflict(client, auth_headers):
    job_id, tech_id = _setup_job_and_tech(client, auth_headers)
    when = _iso(6)
    ok = client.patch(
        f"/api/jobs/{job_id}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": when},
        headers=auth_headers,
    )
    assert ok.status_code == 200

    slot = client.get(
        "/api/jobs/scheduling/next-slot",
        params={
            "technician_id": tech_id,
            "requested_time": when,
            "search_hours": 2,
            "step_minutes": 30,
        },
        headers=auth_headers,
    )
    assert slot.status_code == 200
    body = slot.json()
    assert body["technician_id"] == tech_id
    assert body["next_available_time"] is not None
    assert body["next_available_time"] != when
    assert job_id in body["conflicting_job_ids"]


def test_next_slot_respects_org_scope(client, auth_headers, other_auth_headers):
    other_setup = _setup_job_and_tech(client, other_auth_headers)
    other_job_id, other_tech_id = other_setup
    other_when = _iso(7)
    dispatched = client.patch(
        f"/api/jobs/{other_job_id}/dispatch",
        json={"technician_id": other_tech_id, "scheduled_time": other_when},
        headers=other_auth_headers,
    )
    assert dispatched.status_code == 200

    # Primary org should not see other org scheduling conflicts.
    check = client.get(
        "/api/jobs/scheduling/conflict",
        params={"technician_id": other_tech_id, "scheduled_time": other_when},
        headers=auth_headers,
    )
    assert check.status_code == 200
    assert check.json()["conflict"] is False


def test_dispatch_rejects_outside_technician_availability(client, auth_headers):
    customer = client.post(
        "/api/customers",
        json={"name": "Availability Customer", "phone": "555-0001"},
        headers=auth_headers,
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    tech = client.post(
        "/api/technicians",
        json={
            "name": "Day Shift Tech",
            "availability_start_hour_utc": 9,
            "availability_end_hour_utc": 17,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=auth_headers,
    )
    assert tech.status_code == 201
    tech_id = tech.json()["id"]

    job = client.post(
        "/api/jobs",
        json={"title": "Out of Hours Job", "customer_id": customer_id},
        headers=auth_headers,
    )
    assert job.status_code == 201

    outside_hours = (
        datetime.now(_CENTRAL)
        .replace(hour=20, minute=0, second=0, microsecond=0)
        .astimezone(timezone.utc)
        .isoformat()
    )
    resp = client.patch(
        f"/api/jobs/{job.json()['id']}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": outside_hours},
        headers=auth_headers,
    )
    assert resp.status_code == 422
    assert "outside configured availability" in resp.json()["detail"]


def test_next_slot_snaps_to_availability_window(client, auth_headers):
    tech = client.post(
        "/api/technicians",
        json={
            "name": "Morning Tech",
            "availability_start_hour_utc": 9,
            "availability_end_hour_utc": 17,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=auth_headers,
    )
    assert tech.status_code == 201
    tech_id = tech.json()["id"]

    requested = (
        datetime.now(_CENTRAL)
        .replace(hour=20, minute=0, second=0, microsecond=0)
        .astimezone(timezone.utc)
        .isoformat()
    )
    slot = client.get(
        "/api/jobs/scheduling/next-slot",
        params={
            "technician_id": tech_id,
            "requested_time": requested,
            "search_hours": 24,
            "step_minutes": 60,
        },
        headers=auth_headers,
    )
    assert slot.status_code == 200
    body = slot.json()
    assert body["next_available_time"] is not None
    parsed = datetime.fromisoformat(body["next_available_time"].replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(_CENTRAL)
    assert parsed.hour == 9


def test_scheduling_conflict_buffer_detects_nearby_job(client, auth_headers):
    job_id, tech_id = _setup_job_and_tech(client, auth_headers)
    when = _iso(10)
    ok = client.patch(
        f"/api/jobs/{job_id}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": when},
        headers=auth_headers,
    )
    assert ok.status_code == 200

    nearby = datetime.fromisoformat(when.replace("Z", "+00:00")) + timedelta(minutes=20)
    check = client.get(
        "/api/jobs/scheduling/conflict",
        params={
            "technician_id": tech_id,
            "scheduled_time": nearby.isoformat(),
            "buffer_minutes": 30,
        },
        headers=auth_headers,
    )
    assert check.status_code == 200
    assert check.json()["conflict"] is True


def test_next_slot_with_buffer_skips_nearby_time(client, auth_headers):
    job_id, tech_id = _setup_job_and_tech(client, auth_headers)
    when = _iso(12)
    ok = client.patch(
        f"/api/jobs/{job_id}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": when},
        headers=auth_headers,
    )
    assert ok.status_code == 200

    requested = (datetime.fromisoformat(when.replace("Z", "+00:00")) + timedelta(minutes=15)).isoformat()
    slot = client.get(
        "/api/jobs/scheduling/next-slot",
        params={
            "technician_id": tech_id,
            "requested_time": requested,
            "search_hours": 3,
            "step_minutes": 15,
            "buffer_minutes": 30,
        },
        headers=auth_headers,
    )
    assert slot.status_code == 200
    body = slot.json()
    assert body["next_available_time"] is not None
    assert body["next_available_time"] != requested


def test_dispatch_respects_buffer_minutes_conflict(client, auth_headers):
    tech = client.post(
        "/api/technicians",
        json={
            "name": "Buffer Dispatch Tech",
            "availability_start_hour_utc": 0,
            "availability_end_hour_utc": 24,
            "availability_weekdays": "0,1,2,3,4,5,6",
        },
        headers=auth_headers,
    )
    assert tech.status_code == 201
    tech_id = tech.json()["id"]

    customer = client.post(
        "/api/customers",
        json={"name": "Buffer Dispatch Customer", "phone": "555-6789"},
        headers=auth_headers,
    )
    assert customer.status_code == 201
    customer_id = customer.json()["id"]

    job1 = client.post("/api/jobs", json={"title": "B1", "customer_id": customer_id}, headers=auth_headers).json()
    job2 = client.post("/api/jobs", json={"title": "B2", "customer_id": customer_id}, headers=auth_headers).json()

    base_time = _iso(14)
    first = client.patch(
        f"/api/jobs/{job1['id']}/dispatch",
        json={"technician_id": tech_id, "scheduled_time": base_time},
        headers=auth_headers,
    )
    assert first.status_code == 200

    nearby = (datetime.fromisoformat(base_time.replace("Z", "+00:00")) + timedelta(minutes=20)).isoformat()
    second = client.patch(
        f"/api/jobs/{job2['id']}/dispatch?buffer_minutes=30",
        json={"technician_id": tech_id, "scheduled_time": nearby},
        headers=auth_headers,
    )
    assert second.status_code == 422
    assert "already has a job" in second.json()["detail"]
