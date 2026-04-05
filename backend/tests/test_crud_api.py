import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import Base, SessionLocal, engine
from app.core.auth import hash_password
from app.main import app
from app.models.core import Organization, User


_AUTH_EMAIL = "crudtest@example.com"
_AUTH_PASSWORD = "crudtestpass"
_AUTH_ORG = "CRUD Test Org"


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        org = Organization(name=_AUTH_ORG)
        db.add(org)
        db.flush()
        db.add(
            User(
                email=_AUTH_EMAIL,
                hashed_password=hash_password(_AUTH_PASSWORD),
                organization_id=org.id,
            )
        )
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="module")
def auth_headers():
    with TestClient(app) as c:
        resp = c.post("/api/auth/login", data={"username": _AUTH_EMAIL, "password": _AUTH_PASSWORD})
        assert resp.status_code == 200
        token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_customers_crud(client, auth_headers):
    resp = client.post("/api/customers", json={"name": "Test Customer", "email": "test@demo.com", "phone": "555-1234"}, headers=auth_headers)
    assert resp.status_code == 201
    cid = resp.json()["id"]
    assert client.get("/api/customers", headers=auth_headers).status_code == 200
    assert client.get(f"/api/customers/{cid}", headers=auth_headers).status_code == 200
    assert client.put(f"/api/customers/{cid}", json={"name": "Updated Customer"}, headers=auth_headers).status_code == 200


def test_crud_rejects_unauthenticated(client):
    assert client.get("/api/customers").status_code == 401
    assert client.get("/api/jobs").status_code == 401
    assert client.get("/api/technicians").status_code == 401


def test_jobs_crud(client, auth_headers):
    customer_resp = client.post(
        "/api/customers",
        json={"name": "Job Customer", "email": "job@demo.com", "phone": "555-5678"},
        headers=auth_headers,
    )
    assert customer_resp.status_code == 201
    customer_id = customer_resp.json()["id"]

    resp = client.post("/api/jobs", json={"title": "Test Job", "customer_id": customer_id}, headers=auth_headers)
    assert resp.status_code == 201
    jid = resp.json()["id"]
    assert client.get("/api/jobs", headers=auth_headers).status_code == 200
    assert client.get(f"/api/jobs/{jid}", headers=auth_headers).status_code == 200
    assert client.put(f"/api/jobs/{jid}", json={"title": "Updated Job"}, headers=auth_headers).status_code == 200


def test_technicians_crud(client, auth_headers):
    resp = client.post("/api/technicians", json={"name": "Test Tech"}, headers=auth_headers)
    assert resp.status_code == 201
    tid = resp.json()["id"]
    assert resp.json()["availability_start_hour_utc"] == 8
    assert resp.json()["availability_end_hour_utc"] == 19
    assert resp.json()["availability_weekdays"] == "0,1,2,3,4"
    assert client.get("/api/technicians", headers=auth_headers).status_code == 200
    assert client.get(f"/api/technicians/{tid}", headers=auth_headers).status_code == 200
    updated = client.put(
        f"/api/technicians/{tid}",
        json={
            "name": "Updated Tech",
            "availability_start_hour_utc": 7,
            "availability_end_hour_utc": 18,
            "availability_weekdays": "0,1,2,3,4,5",
        },
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["availability_start_hour_utc"] == 7
    assert updated.json()["availability_end_hour_utc"] == 18
    assert updated.json()["availability_weekdays"] == "0,1,2,3,4,5"


def test_technician_availability_validation_rejects_invalid_create_payloads(client, auth_headers):
    bad_start = client.post(
        "/api/technicians",
        json={"name": "Bad Start", "availability_start_hour_utc": -1},
        headers=auth_headers,
    )
    assert bad_start.status_code == 422

    bad_end = client.post(
        "/api/technicians",
        json={"name": "Bad End", "availability_end_hour_utc": 25},
        headers=auth_headers,
    )
    assert bad_end.status_code == 422

    bad_window = client.post(
        "/api/technicians",
        json={
            "name": "Bad Window",
            "availability_start_hour_utc": 19,
            "availability_end_hour_utc": 19,
        },
        headers=auth_headers,
    )
    assert bad_window.status_code == 422

    bad_weekdays_duplicate = client.post(
        "/api/technicians",
        json={"name": "Bad Days", "availability_weekdays": "0,0,1"},
        headers=auth_headers,
    )
    assert bad_weekdays_duplicate.status_code == 422

    bad_weekdays_range = client.post(
        "/api/technicians",
        json={"name": "Bad Range", "availability_weekdays": "0,7"},
        headers=auth_headers,
    )
    assert bad_weekdays_range.status_code == 422


def test_technician_availability_validation_rejects_invalid_update_payloads(client, auth_headers):
    create = client.post(
        "/api/technicians",
        json={"name": "Update Target"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    technician_id = create.json()["id"]

    bad_update = client.put(
        f"/api/technicians/{technician_id}",
        json={"name": "Update Target", "availability_start_hour_utc": 22, "availability_end_hour_utc": 10},
        headers=auth_headers,
    )
    assert bad_update.status_code == 422

