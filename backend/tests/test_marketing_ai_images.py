from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base
from app.core.db import SessionLocal
from app.core.db import engine
from app.main import app
from app.models.core import Organization
from app.models.core import User


_AUTH_EMAIL = "marketing-image-owner@example.com"
_AUTH_PASSWORD = "marketingimagepass"
_AUTH_ORG = "Marketing Image Test Org"


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


def test_generate_marketing_image_requires_auth() -> None:
    with TestClient(app) as client:
        resp = client.post(
            "/api/marketing/ai-images/generate",
            json={"prompt": "Generate a spring HVAC promotion image for homeowners."},
        )
        assert resp.status_code == 401


def test_generate_marketing_image_success(monkeypatch) -> None:
    def _fake_generate_marketing_image(*, prompt: str, size: str, quality: str):
        assert "HVAC" in prompt or "hvac" in prompt
        assert size == "1024x1024"
        assert quality == "high"

        class _Image:
            model = "gpt-image-1"
            mime_type = "image/png"
            image_base64 = "ZmFrZS1pbWFnZS1ieXRlcw=="
            revised_prompt = "A polished HVAC spring promo graphic"

        return _Image()

    monkeypatch.setattr("app.api.marketing.generate_marketing_image", _fake_generate_marketing_image)

    headers = _auth_headers()
    with TestClient(app) as client:
        resp = client.post(
            "/api/marketing/ai-images/generate",
            json={
                "prompt": "Generate an HVAC spring promotion image for local homeowners with clear CTA",
                "size": "1024x1024",
                "quality": "high",
            },
            headers=headers,
        )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["model"] == "gpt-image-1"
    assert payload["mime_type"] == "image/png"
    assert payload["image_base64"] == "ZmFrZS1pbWFnZS1ieXRlcw=="
    assert payload["revised_prompt"]
