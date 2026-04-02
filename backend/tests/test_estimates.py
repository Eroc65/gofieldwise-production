from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "estimate@example.com"
_PASSWORD = "estimatepass"
_ORG = "Estimate Org"
_OTHER_EMAIL = "estimate_other@example.com"
_OTHER_PASSWORD = "estimateother"
_OTHER_ORG = "Estimate Other Org"


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


def _create_job(client: TestClient, headers):
    customer = client.post(
        "/api/customers",
        json={"name": "Estimate Customer", "phone": "555-7000"},
        headers=headers,
    )
    assert customer.status_code == 201
    job = client.post(
        "/api/jobs",
        json={"title": "Estimate Job", "customer_id": customer.json()["id"]},
        headers=headers,
    )
    assert job.status_code == 201
    return job.json()["id"]


def test_estimate_routes_require_auth():
    client = TestClient(app)
    assert client.get("/api/estimates").status_code == 401
    assert client.get("/api/estimates/1").status_code == 401
    assert client.post("/api/estimates", json={"amount": 100, "job_id": 1}).status_code == 401
    assert client.patch("/api/estimates/1/status", json={"status": "approved"}).status_code == 401


def test_create_and_list_estimate():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    job_id = _create_job(client, headers)

    created = client.post(
        "/api/estimates",
        json={"amount": 850.0, "description": "Replace water heater", "job_id": job_id},
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "sent"
    assert body["issued_at"] is not None

    lst = client.get("/api/estimates", headers=headers)
    assert lst.status_code == 200
    assert any(item["id"] == body["id"] for item in lst.json())


def test_approve_estimate_updates_job_status():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    job_id = _create_job(client, headers)

    created = client.post(
        "/api/estimates",
        json={"amount": 1200.0, "description": "Main line repair", "job_id": job_id},
        headers=headers,
    ).json()

    approved = client.patch(
        f"/api/estimates/{created['id']}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_at"] is not None

    job = client.get(f"/api/jobs/{job_id}", headers=headers)
    assert job.status_code == 200
    assert job.json()["status"] == "approved"


def test_reject_estimate_updates_job_status():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    job_id = _create_job(client, headers)

    created = client.post(
        "/api/estimates",
        json={"amount": 400.0, "description": "Drain cleaning", "job_id": job_id},
        headers=headers,
    ).json()

    rejected = client.patch(
        f"/api/estimates/{created['id']}/status",
        json={"status": "rejected"},
        headers=headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejected_at"] is not None

    job = client.get(f"/api/jobs/{job_id}", headers=headers)
    assert job.status_code == 200
    assert job.json()["status"] == "estimate_rejected"


def test_terminal_estimate_status_is_locked():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    job_id = _create_job(client, headers)

    created = client.post(
        "/api/estimates",
        json={"amount": 999.0, "description": "Panel upgrade", "job_id": job_id},
        headers=headers,
    ).json()

    approved = client.patch(
        f"/api/estimates/{created['id']}/status",
        json={"status": "approved"},
        headers=headers,
    )
    assert approved.status_code == 200

    reroute = client.patch(
        f"/api/estimates/{created['id']}/status",
        json={"status": "rejected"},
        headers=headers,
    )
    assert reroute.status_code == 422


def test_estimate_org_scoping():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)
    other_headers = _auth_headers(client, _OTHER_EMAIL, _OTHER_PASSWORD)
    other_job_id = _create_job(client, other_headers)

    foreign = client.post(
        "/api/estimates",
        json={"amount": 700.0, "description": "Foreign estimate", "job_id": other_job_id},
        headers=other_headers,
    ).json()

    resp = client.get(f"/api/estimates/{foreign['id']}", headers=headers)
    assert resp.status_code == 404
