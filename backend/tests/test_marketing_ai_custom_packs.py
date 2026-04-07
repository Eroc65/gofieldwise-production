from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.auth import hash_password
from app.core.db import Base
from app.core.db import SessionLocal
from app.core.db import engine
from app.main import app
from app.models.core import Organization
from app.models.core import User


_OWNER_EMAIL = "marketing-packs-owner@example.com"
_OWNER_PASSWORD = "marketingpackspass"
_OWNER_ORG = "Marketing Packs Org"
_OTHER_EMAIL = "marketing-packs-other@example.com"
_OTHER_PASSWORD = "marketingpacksother"
_OTHER_ORG = "Marketing Packs Other Org"


def setup_module() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        org1 = Organization(name=_OWNER_ORG)
        org2 = Organization(name=_OTHER_ORG)
        db.add(org1)
        db.add(org2)
        db.flush()

        db.add(
            User(
                email=_OWNER_EMAIL,
                hashed_password=hash_password(_OWNER_PASSWORD),
                role="owner",
                organization_id=org1.id,
            )
        )
        db.add(
            User(
                email=_OTHER_EMAIL,
                hashed_password=hash_password(_OTHER_PASSWORD),
                role="owner",
                organization_id=org2.id,
            )
        )
        db.commit()
    finally:
        db.close()


def _auth_headers(email: str, password: str) -> dict[str, str]:
    with TestClient(app) as client:
        resp = client.post(
            "/api/auth/login",
            data={"username": email, "password": password},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_custom_campaign_pack_create_list_delete_scoped_by_org() -> None:
    owner_headers = _auth_headers(_OWNER_EMAIL, _OWNER_PASSWORD)
    other_headers = _auth_headers(_OTHER_EMAIL, _OTHER_PASSWORD)

    payload = {
        "name": "My HVAC Local Pack",
        "description": "Org-specific preset",
        "template_code": "seasonal_offer",
        "channel_code": "facebook_landscape",
        "trade_code": "hvac",
        "service_type": "HVAC",
        "offer_text": "Spring Tune-Up 20% Off",
        "cta_text": "Book Tune-Up",
        "primary_color": "#0f172a",
        "prompt": "Use a modern home HVAC visual with bold headline and conversion-focused CTA.",
    }

    with TestClient(app) as client:
        create_resp = client.post("/api/marketing/ai-images/custom-packs", json=payload, headers=owner_headers)
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["name"] == payload["name"]
        assert created["code"].startswith("custom_")

        owner_list = client.get("/api/marketing/ai-images/custom-packs", headers=owner_headers)
        assert owner_list.status_code == 200
        owner_items = owner_list.json()
        assert any(item["id"] == created["id"] for item in owner_items)

        other_list = client.get("/api/marketing/ai-images/custom-packs", headers=other_headers)
        assert other_list.status_code == 200
        other_items = other_list.json()
        assert all(item["id"] != created["id"] for item in other_items)

        update_payload = {
            **payload,
            "name": "My HVAC Local Pack Updated",
            "offer_text": "Spring Tune-Up 25% Off",
            "cta_text": "Book This Week",
        }
        update_denied = client.patch(
            f"/api/marketing/ai-images/custom-packs/{created['id']}",
            json=update_payload,
            headers=other_headers,
        )
        assert update_denied.status_code == 404

        update_ok = client.patch(
            f"/api/marketing/ai-images/custom-packs/{created['id']}",
            json=update_payload,
            headers=owner_headers,
        )
        assert update_ok.status_code == 200
        updated = update_ok.json()
        assert updated["name"] == "My HVAC Local Pack Updated"
        assert updated["offer_text"] == "Spring Tune-Up 25% Off"
        assert updated["cta_text"] == "Book This Week"

        delete_denied = client.delete(f"/api/marketing/ai-images/custom-packs/{created['id']}", headers=other_headers)
        assert delete_denied.status_code == 404

        delete_ok = client.delete(f"/api/marketing/ai-images/custom-packs/{created['id']}", headers=owner_headers)
        assert delete_ok.status_code == 204

        owner_list_after = client.get("/api/marketing/ai-images/custom-packs", headers=owner_headers)
        assert owner_list_after.status_code == 200
        owner_items_after = owner_list_after.json()
        assert all(item["id"] != created["id"] for item in owner_items_after)
