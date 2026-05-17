from datetime import timedelta

from app.core.db import Base, engine, SessionLocal
from app.api.operator import _hash_key
from app.models.core import OperatorInvite, Organization, _utcnow


def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_operator_invite_provision_verify_and_redeem(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("BILLING_SYNC_SECRET", "test-secret-that-is-long-enough")

    db = SessionLocal()
    org = Organization(name="Paid Operator Org", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    org_id = org.id
    db.close()

    provision = client.post(
        "/api/operator/invite/provision",
        headers={"X-Billing-Sync-Secret": "test-secret-that-is-long-enough"},
        json={
            "org_id": org_id,
            "email": "owner@example.com",
            "owner_name": "Owner Example",
            "business_name": "Paid Operator Org",
            "phone": "918-555-0100",
            "stripe_customer_id": "cus_test",
            "stripe_subscription_id": "sub_test",
            "setup_base_url": "https://gofieldwise.com",
        },
    )
    assert provision.status_code == 200, provision.text
    provision_body = provision.json()
    assert provision_body["operator_key"].startswith("gfw_op_")
    assert provision_body["setup_url"].startswith("https://gofieldwise.com/operator/setup?key=gfw_op_")

    verify = client.post(
        "/api/operator/invite/verify",
        json={"key": provision_body["operator_key"]},
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["email"] == "owner@example.com"
    assert verify.json()["business_name"] == "Paid Operator Org"

    redeem = client.post(
        "/api/operator/invite/redeem",
        json={
            "key": provision_body["operator_key"],
            "email": "owner@example.com",
            "password": "super-secret",
            "confirm_password": "super-secret",
            "owner_name": "Owner Example",
            "business_name": "Paid Operator Org",
            "phone": "918-555-0100",
        },
    )
    assert redeem.status_code == 200, redeem.text
    redeemed = redeem.json()
    assert redeemed["ok"] is True
    assert redeemed["access_token"]
    assert redeemed["token_type"] == "bearer"
    assert redeemed["user"]["role"] == "owner"
    assert redeemed["user"]["organization_id"] == org_id
    assert redeemed["redirect_to"] == "/connect-center"

    second_redeem = client.post(
        "/api/operator/invite/redeem",
        json={
            "key": provision_body["operator_key"],
            "email": "other@example.com",
            "password": "super-secret",
            "owner_name": "Other Owner",
            "business_name": "Other Business",
        },
    )
    assert second_redeem.status_code == 409


def test_operator_invite_provision_requires_internal_secret(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("BILLING_SYNC_SECRET", "test-secret-that-is-long-enough")

    missing = client.post("/api/operator/invite/provision", json={"email": "owner@example.com"})
    assert missing.status_code == 401

    wrong = client.post(
        "/api/operator/invite/provision",
        headers={"X-Billing-Sync-Secret": "wrong"},
        json={"email": "owner@example.com"},
    )
    assert wrong.status_code == 403


def test_operator_invite_redeem_can_create_org_when_invite_has_no_org(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("BILLING_SYNC_SECRET", "test-secret-that-is-long-enough")

    provision = client.post(
        "/api/operator/invite/provision",
        headers={"X-Billing-Sync-Secret": "test-secret-that-is-long-enough"},
        json={
            "email": "new-owner@example.com",
            "business_name": "New Checkout Business",
            "setup_base_url": "https://gofieldwise.com",
        },
    )
    assert provision.status_code == 200, provision.text

    redeem = client.post(
        "/api/operator/invite/redeem",
        json={
            "key": provision.json()["operator_key"],
            "email": "new-owner@example.com",
            "password": "super-secret",
            "owner_name": "New Owner",
            "business_name": "New Checkout Business",
            "phone": "405-555-0100",
        },
    )
    assert redeem.status_code == 200, redeem.text
    assert redeem.json()["organization"]["name"] == "New Checkout Business"


def test_operator_invite_expired_key_is_rejected(client):
    _reset_db()

    db = SessionLocal()
    invite = OperatorInvite(
        key_hash=_hash_key("expired-key"),
        email="expired@example.com",
        business_name="Expired Business",
        status="pending",
        expires_at=_utcnow() - timedelta(days=1),
    )
    db.add(invite)
    db.commit()
    db.close()

    response = client.post("/api/operator/invite/verify", json={"key": "expired-key"})
    assert response.status_code == 410


def test_operator_invite_accepts_operator_key_contract(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("BILLING_SYNC_SECRET", "test-secret-that-is-long-enough")

    db = SessionLocal()
    org = Organization(name="Exact Contract Org", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    org_id = org.id
    db.close()

    provision = client.post(
        "/api/operator/invite/provision",
        headers={"X-Billing-Sync-Secret": "test-secret-that-is-long-enough"},
        json={
            "organization_id": org_id,
            "email": "contract@example.com",
            "source": "stripe_checkout",
            "stripe_customer_id": "cus_contract",
            "stripe_subscription_id": "sub_contract",
            "expires_hours": 72,
        },
    )
    assert provision.status_code == 200, provision.text
    provision_body = provision.json()
    assert provision_body["organization_id"] == org_id
    assert provision_body["organization_name"] == "Exact Contract Org"
    assert provision_body["operator_key"].startswith("gfw_op_")

    verify = client.post(
        "/api/operator/invite/verify",
        json={"operator_key": provision_body["operator_key"]},
    )
    assert verify.status_code == 200, verify.text
    assert verify.json()["organization_id"] == org_id
    assert verify.json()["organization_name"] == "Exact Contract Org"

    redeem = client.post(
        "/api/operator/invite/redeem",
        json={
            "operator_key": provision_body["operator_key"],
            "email": "contract-owner@example.com",
            "password": "securepass123",
            "confirm_password": "securepass123",
            "owner_name": "Contract Owner",
            "business_name": "Exact Contract Org",
            "phone": "4055550100",
        },
    )
    assert redeem.status_code == 200, redeem.text
    assert redeem.json()["ok"] is True
    assert redeem.json()["redirect_to"] == "/connect-center"


def test_operator_invite_provision_is_idempotent_for_subscription(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("BILLING_SYNC_SECRET", "test-secret-that-is-long-enough")

    db = SessionLocal()
    org = Organization(name="Idempotent Contract Org", is_active=True)
    db.add(org)
    db.commit()
    db.refresh(org)
    org_id = org.id
    db.close()

    payload = {
        "organization_id": org_id,
        "email": "retry@example.com",
        "source": "stripe_checkout",
        "stripe_customer_id": "cus_retry",
        "stripe_subscription_id": "sub_retry",
        "expires_hours": 72,
    }

    first = client.post(
        "/api/operator/invite/provision",
        headers={"X-Billing-Sync-Secret": "test-secret-that-is-long-enough"},
        json=payload,
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/api/operator/invite/provision",
        headers={"X-Billing-Sync-Secret": "test-secret-that-is-long-enough"},
        json=payload,
    )
    assert second.status_code == 200, second.text

    assert second.json()["reused"] is True
    assert second.json()["invite_id"] == first.json()["invite_id"]
    assert second.json()["operator_key"] == first.json()["operator_key"]


def test_operator_invite_rejects_password_confirmation_mismatch(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("BILLING_SYNC_SECRET", "test-secret-that-is-long-enough")

    provision = client.post(
        "/api/operator/invite/provision",
        headers={"X-Billing-Sync-Secret": "test-secret-that-is-long-enough"},
        json={"email": "mismatch@example.com", "business_name": "Mismatch Org"},
    )
    assert provision.status_code == 200, provision.text

    redeem = client.post(
        "/api/operator/invite/redeem",
        json={
            "operator_key": provision.json()["operator_key"],
            "email": "mismatch@example.com",
            "password": "securepass123",
            "confirm_password": "different123",
            "owner_name": "Mismatch Owner",
            "business_name": "Mismatch Org",
        },
    )
    assert redeem.status_code == 422
