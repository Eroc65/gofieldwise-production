from datetime import datetime, timedelta, timezone

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

    tech = client.post("/api/technicians", json={"name": "Dispatch Tech"}, headers=headers)
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
    tech = client.post("/api/technicians", json={"name": "Conflict Tech"}, headers=auth_headers)
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
        json={"name": "Other Org Tech"},
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
