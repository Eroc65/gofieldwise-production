from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base, SessionLocal, engine
from app.main import app
from app.models.core import Organization, User


_AUTH_EMAIL = "platform-owner@example.com"
_AUTH_PASSWORD = "platformpass"
_AUTH_ORG = "Platform Features Org"


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


def test_public_status_endpoint() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["features"]["ai_guide"] is True


def test_ai_guide_toggle_roundtrip() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        get_before = client.get("/api/org/ai-guide", headers=headers)
        assert get_before.status_code == 200

        update = client.patch(
            "/api/org/ai-guide",
            json={"enabled": True, "stage": "phase_1"},
            headers=headers,
        )
        assert update.status_code == 200
        assert update.json()["enabled"] is True
        assert update.json()["stage"] == "phase_1"

        get_after = client.get("/api/org/ai-guide", headers=headers)
        assert get_after.status_code == 200
        assert get_after.json()["enabled"] is True


def test_contextual_help_articles_create_and_filter() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        create = client.post(
            "/api/help/articles",
            json={
                "slug": "jobs-dispatch-basics",
                "title": "Dispatch Basics",
                "category": "scheduling",
                "context_key": "jobs_dispatch",
                "body": "Use dispatch to assign techs quickly and avoid overlaps.",
            },
            headers=headers,
        )
        assert create.status_code == 201

        listed = client.get("/api/help/articles?context_key=jobs_dispatch", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) >= 1


def test_tribal_coaching_snippets_create_and_list() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        create = client.post(
            "/api/coaching/snippets",
            json={
                "title": "No Heat Winter Triage",
                "trade": "hvac",
                "issue_pattern": "No heat call in winter",
                "senior_tip": "Verify thermostat mode, power, then ignition path before replacing parts.",
                "checklist": "Thermostat;Breaker;Ignition;Airflow",
            },
            headers=headers,
        )
        assert create.status_code == 201

        listed = client.get("/api/coaching/snippets?trade=hvac", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) >= 1


def test_marketing_service_packages_endpoint() -> None:
    headers = _auth_headers()
    with TestClient(app) as client:
        resp = client.get("/api/marketing/service-packages", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["monthly_price_usd"] in (500, 750)
