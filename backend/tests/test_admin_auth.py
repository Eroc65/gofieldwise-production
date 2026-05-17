from app.core.db import Base, engine


ADMIN_USERNAME = "owner-admin"
ENV_PASSWORD = "testpass123"
NEW_PASSWORD = "newpass123"


def _reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_admin_login_uses_env_credentials(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD", ENV_PASSWORD)

    response = client.post(
        "/api/admin/auth/login",
        json={"username": ADMIN_USERNAME, "password": ENV_PASSWORD},
    )

    assert response.status_code == 200, response.text
    assert response.json()["access_token"]
    assert response.json()["username"] == ADMIN_USERNAME


def test_admin_forgot_and_reset_password_override_env_password(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD", ENV_PASSWORD)
    monkeypatch.setenv("ADMIN_RESET_BASE_URL", "https://gofieldwise.com")

    forgot = client.post("/api/admin/auth/forgot-password", json={"username": ADMIN_USERNAME})
    assert forgot.status_code == 200, forgot.text
    reset_url = forgot.json()["reset_url"]
    token = reset_url.split("reset=", 1)[1]

    reset = client.post(
        "/api/admin/auth/reset-password",
        json={"token": token, "password": NEW_PASSWORD},
    )
    assert reset.status_code == 200, reset.text
    assert reset.json()["access_token"]

    old_login = client.post(
        "/api/admin/auth/login",
        json={"username": ADMIN_USERNAME, "password": ENV_PASSWORD},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/admin/auth/login",
        json={"username": ADMIN_USERNAME, "password": NEW_PASSWORD},
    )
    assert new_login.status_code == 200, new_login.text


def test_admin_reset_token_cannot_be_reused(client, monkeypatch):
    _reset_db()
    monkeypatch.setenv("ADMIN_USERNAME", ADMIN_USERNAME)
    monkeypatch.setenv("ADMIN_PASSWORD", ENV_PASSWORD)

    forgot = client.post("/api/admin/auth/forgot-password", json={"username": ADMIN_USERNAME})
    token = forgot.json()["reset_url"].split("reset=", 1)[1]

    first = client.post("/api/admin/auth/reset-password", json={"token": token, "password": NEW_PASSWORD})
    assert first.status_code == 200, first.text

    second = client.post("/api/admin/auth/reset-password", json={"token": token, "password": "another123"})
    assert second.status_code == 404
