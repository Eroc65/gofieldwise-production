from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_auth_signup_login_and_protected_routes() -> None:
	client = TestClient(app)

	email = f"testclientuser-{uuid4().hex[:8]}@example.com"
	password = "testpass123"
	org_name = "TestClientOrg"

	# Signup
	signup_resp = client.post(
		"/api/auth/signup",
		json={
			"email": email,
			"password": password,
			"organization_name": org_name,
		},
	)
	assert signup_resp.status_code == 200
	assert signup_resp.json()["email"] == email

	# Login
	login_resp = client.post(
		"/api/auth/login",
		data={"username": email, "password": password},
	)
	assert login_resp.status_code == 200
	access_token = login_resp.json()["access_token"]

	# Protected route rejects unauthenticated
	unauth_resp = client.get("/api/protected")
	assert unauth_resp.status_code == 401

	# Protected route succeeds with valid auth
	headers = {"Authorization": f"Bearer {access_token}"}
	auth_resp = client.get("/api/protected", headers=headers)
	assert auth_resp.status_code == 200

	# Current-organization endpoint returns expected org
	org_resp = client.get("/api/auth/org", headers=headers)
	assert org_resp.status_code == 200
	assert org_resp.json()["name"] == org_name
