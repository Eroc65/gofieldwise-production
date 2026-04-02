from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User

_EMAIL = "queue@example.com"
_PASSWORD = "queuepass"
_ORG = "Queue Org"

_OTHER_EMAIL = "queue_other@example.com"
_OTHER_PASSWORD = "queueother"
_OTHER_ORG = "Queue Other Org"


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


def _create_customer(client: TestClient, headers, name: str = "Queue Customer"):
    resp = client.post(
        "/api/customers",
        json={"name": name, "phone": "555-6000"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _create_job(client: TestClient, headers, customer_id: int, title: str = "Queue Job"):
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


def test_operator_queue_requires_auth():
    client = TestClient(app)
    assert client.get("/api/reports/operator-queue").status_code == 401


def test_operator_queue_empty_org():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    result = client.get("/api/reports/operator-queue", headers=headers)
    assert result.status_code == 200

    body = result.json()
    assert body["limit"] == 10
    assert body["total_candidates"] == 0
    assert body["items"] == []


def test_operator_queue_ranking_and_limit():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    # New lead candidate
    intake = client.post(
        "/api/leads/intake/1",
        json={"name": "Queue Lead", "phone": "555-6111", "source": "web_form"},
    )
    assert intake.status_code == 201

    customer = _create_customer(client, headers)

    # Stale dispatched job candidate
    stale_job = _create_job(client, headers, customer["id"], "Stale Queue Job")
    stale_update = client.put(
        f"/api/jobs/{stale_job['id']}",
        json={"status": "dispatched", "scheduled_time": _past(3)},
        headers=headers,
    )
    assert stale_update.status_code == 200

    # Severe overdue invoice candidate (highest expected)
    invoice_job = _create_job(client, headers, customer["id"], "Overdue Queue Invoice")
    _create_invoice(client, headers, invoice_job["id"], 900.0, _past(20))

    # Overdue custom reminder candidate
    reminder = client.post(
        "/api/reminders",
        json={
            "message": "Call customer back",
            "channel": "internal",
            "due_at": _past(1),
            "customer_id": customer["id"],
        },
        headers=headers,
    )
    assert reminder.status_code == 201

    result = client.get("/api/reports/operator-queue?limit=3", headers=headers)
    assert result.status_code == 200

    body = result.json()
    assert body["limit"] == 3
    assert body["total_candidates"] >= 4
    assert len(body["items"]) == 3

    scores = [item["priority_score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)
    assert body["items"][0]["item_type"] == "invoice_collection"


def test_operator_queue_org_isolation():
    client = TestClient(app)
    org1_headers = _auth_headers(client, _EMAIL, _PASSWORD)
    org2_headers = _auth_headers(client, _OTHER_EMAIL, _OTHER_PASSWORD)

    # Seed org 2 with one candidate item.
    intake = client.post(
        "/api/leads/intake/2",
        json={"name": "Other Queue Lead", "phone": "555-6222", "source": "web_form"},
    )
    assert intake.status_code == 201

    org1_queue = client.get("/api/reports/operator-queue", headers=org1_headers)
    org2_queue = client.get("/api/reports/operator-queue", headers=org2_headers)

    assert org1_queue.status_code == 200
    assert org2_queue.status_code == 200

    body1 = org1_queue.json()
    body2 = org2_queue.json()

    assert body1["organization_id"] != body2["organization_id"]
    assert body1["total_candidates"] > body2["total_candidates"]
    assert body2["total_candidates"] == 1


def test_operator_queue_ack_requires_auth():
    client = TestClient(app)
    resp = client.post(
        "/api/reports/operator-queue/ack",
        json={"item_type": "lead_followup", "entity_id": 1},
    )
    assert resp.status_code == 401


def test_operator_queue_ack_invalid_type():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    resp = client.post(
        "/api/reports/operator-queue/ack",
        json={"item_type": "not_real", "entity_id": 1},
        headers=headers,
    )
    assert resp.status_code == 422
    assert "Invalid item_type" in resp.json()["detail"]


def test_operator_queue_ack_removes_item_and_is_idempotent():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    intake = client.post(
        "/api/leads/intake/1",
        json={"name": "Ack Lead", "phone": "555-6333", "source": "web_form"},
    )
    assert intake.status_code == 201
    lead_id = intake.json()["id"]

    queue_before = client.get("/api/reports/operator-queue", headers=headers)
    assert queue_before.status_code == 200
    assert any(
        item["item_type"] == "lead_followup" and item["entity_id"] == lead_id
        for item in queue_before.json()["items"]
    )

    ack = client.post(
        "/api/reports/operator-queue/ack",
        json={"item_type": "lead_followup", "entity_id": lead_id},
        headers=headers,
    )
    assert ack.status_code == 200
    ack_body = ack.json()
    assert ack_body["acknowledged"] is True
    assert ack_body["already_acknowledged"] is False

    queue_after = client.get("/api/reports/operator-queue?limit=50", headers=headers)
    assert queue_after.status_code == 200
    assert not any(
        item["item_type"] == "lead_followup" and item["entity_id"] == lead_id
        for item in queue_after.json()["items"]
    )

    ack_again = client.post(
        "/api/reports/operator-queue/ack",
        json={"item_type": "lead_followup", "entity_id": lead_id},
        headers=headers,
    )
    assert ack_again.status_code == 200
    assert ack_again.json()["already_acknowledged"] is True


def test_operator_queue_unack_requires_auth():
    client = TestClient(app)
    resp = client.post(
        "/api/reports/operator-queue/unack",
        json={"item_type": "lead_followup", "entity_id": 1},
    )
    assert resp.status_code == 401


def test_operator_queue_unack_invalid_type():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    resp = client.post(
        "/api/reports/operator-queue/unack",
        json={"item_type": "not_real", "entity_id": 1},
        headers=headers,
    )
    assert resp.status_code == 422
    assert "Invalid item_type" in resp.json()["detail"]


def test_operator_queue_unack_restores_item_and_is_idempotent():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    intake = client.post(
        "/api/leads/intake/1",
        json={"name": "Unack Lead", "phone": "555-6444", "source": "web_form"},
    )
    assert intake.status_code == 201
    lead_id = intake.json()["id"]

    ack = client.post(
        "/api/reports/operator-queue/ack",
        json={"item_type": "lead_followup", "entity_id": lead_id},
        headers=headers,
    )
    assert ack.status_code == 200

    queue_hidden = client.get("/api/reports/operator-queue?limit=50", headers=headers)
    assert queue_hidden.status_code == 200
    assert not any(
        item["item_type"] == "lead_followup" and item["entity_id"] == lead_id
        for item in queue_hidden.json()["items"]
    )

    unack = client.post(
        "/api/reports/operator-queue/unack",
        json={"item_type": "lead_followup", "entity_id": lead_id},
        headers=headers,
    )
    assert unack.status_code == 200
    assert unack.json()["unacknowledged"] is True
    assert unack.json()["already_unacknowledged"] is False

    queue_restored = client.get("/api/reports/operator-queue?limit=50", headers=headers)
    assert queue_restored.status_code == 200
    assert any(
        item["item_type"] == "lead_followup" and item["entity_id"] == lead_id
        for item in queue_restored.json()["items"]
    )

    unack_again = client.post(
        "/api/reports/operator-queue/unack",
        json={"item_type": "lead_followup", "entity_id": lead_id},
        headers=headers,
    )
    assert unack_again.status_code == 200
    assert unack_again.json()["already_unacknowledged"] is True


def test_operator_queue_history_requires_auth():
    client = TestClient(app)
    resp = client.get("/api/reports/operator-queue/history")
    assert resp.status_code == 401


def test_operator_queue_history_includes_ack_and_unack_events():
    client = TestClient(app)
    headers = _auth_headers(client, _EMAIL, _PASSWORD)

    intake = client.post(
        "/api/leads/intake/1",
        json={"name": "History Lead", "phone": "555-6555", "source": "web_form"},
    )
    assert intake.status_code == 201
    lead_id = intake.json()["id"]

    ack = client.post(
        "/api/reports/operator-queue/ack",
        json={"item_type": "lead_followup", "entity_id": lead_id},
        headers=headers,
    )
    assert ack.status_code == 200

    unack = client.post(
        "/api/reports/operator-queue/unack",
        json={"item_type": "lead_followup", "entity_id": lead_id},
        headers=headers,
    )
    assert unack.status_code == 200

    history = client.get("/api/reports/operator-queue/history?limit=20", headers=headers)
    assert history.status_code == 200
    body = history.json()

    events_for_lead = [
        evt for evt in body["events"]
        if evt["item_type"] == "lead_followup" and evt["entity_id"] == lead_id
    ]
    assert len(events_for_lead) >= 2
    assert events_for_lead[0]["action"] == "unack"
    assert any(evt["action"] == "ack" for evt in events_for_lead)
