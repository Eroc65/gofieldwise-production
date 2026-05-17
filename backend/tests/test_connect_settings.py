from app.core.db import Base, SessionLocal, engine
from app.core.auth import hash_password
from app.core.jwt import create_access_token
from app.models.core import Organization, User


def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _owner_token():
    db = SessionLocal()
    org = Organization(name="Connect Settings Org", is_active=True)
    db.add(org)
    db.flush()
    user = User(
        email="connect-owner@example.com",
        hashed_password=hash_password("securepass123"),
        role="owner",
        organization_id=org.id,
    )
    db.add(user)
    db.commit()
    db.close()
    return create_access_token({"sub": "connect-owner@example.com"})


def test_connect_settings_round_trip(client):
    _reset_db()
    token = _owner_token()

    empty = client.get(
        "/api/connect/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert empty.status_code == 200, empty.text
    assert empty.json()["settings"] == {}
    assert empty.json()["completed"] is False

    payload = {
        "settings": {
            "business_name": "Reliable HVAC",
            "trade_type": "HVAC",
            "workflow_mode": "hybrid",
            "owner_notification_phone": "9185550100",
        },
        "completed": True,
    }
    saved = client.patch(
        "/api/connect/settings",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["settings"]["business_name"] == "Reliable HVAC"
    assert saved.json()["completed"] is True

    again = client.get(
        "/api/connect/settings",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert again.status_code == 200, again.text
    assert again.json()["settings"]["workflow_mode"] == "hybrid"
    assert again.json()["completed"] is True
