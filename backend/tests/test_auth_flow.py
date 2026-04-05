from uuid import uuid4

from app.core.db import Base, engine


def setup_module() -> None:
	Base.metadata.drop_all(bind=engine)
	Base.metadata.create_all(bind=engine)

def test_auth_signup_login_and_protected_routes(client) -> None:

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
	assert signup_resp.json()["role"] == "owner"

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
	assert org_resp.json().get("intake_key", "").startswith("org_")


def test_user_role_management_endpoints(client) -> None:
	org_name = f"RoleOrg-{uuid4().hex[:6]}"
	owner_email = f"owner-{uuid4().hex[:6]}@example.com"
	tech_email = f"tech-{uuid4().hex[:6]}@example.com"
	admin_email = f"admin-{uuid4().hex[:6]}@example.com"
	password = "testpass123"

	owner_signup = client.post(
		"/api/auth/signup",
		json={
			"email": owner_email,
			"password": password,
			"organization_name": org_name,
			"role": "owner",
		},
	)
	assert owner_signup.status_code == 200

	tech_signup = client.post(
		"/api/auth/signup",
		json={
			"email": tech_email,
			"password": password,
			"organization_name": org_name,
			"role": "technician",
		},
	)
	assert tech_signup.status_code == 200
	tech_id = tech_signup.json()["id"]

	admin_signup = client.post(
		"/api/auth/signup",
		json={
			"email": admin_email,
			"password": password,
			"organization_name": org_name,
			"role": "admin",
		},
	)
	assert admin_signup.status_code == 200

	owner_login = client.post("/api/auth/login", data={"username": owner_email, "password": password})
	tech_login = client.post("/api/auth/login", data={"username": tech_email, "password": password})
	admin_login = client.post("/api/auth/login", data={"username": admin_email, "password": password})
	assert owner_login.status_code == 200
	assert tech_login.status_code == 200
	assert admin_login.status_code == 200

	owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
	tech_headers = {"Authorization": f"Bearer {tech_login.json()['access_token']}"}
	admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

	list_as_owner = client.get("/api/auth/users", headers=owner_headers)
	assert list_as_owner.status_code == 200
	emails = [u["email"] for u in list_as_owner.json()]
	assert owner_email in emails
	assert tech_email in emails
	assert admin_email in emails

	list_as_tech = client.get("/api/auth/users", headers=tech_headers)
	assert list_as_tech.status_code == 403

	update_as_admin = client.patch(
		f"/api/auth/users/{tech_id}/role",
		json={"role": "dispatcher"},
		headers=admin_headers,
	)
	assert update_as_admin.status_code == 200
	assert update_as_admin.json()["role"] == "dispatcher"

	bad_role = client.patch(
		f"/api/auth/users/{tech_id}/role",
		json={"role": "superhero"},
		headers=owner_headers,
	)
	assert bad_role.status_code == 422


def test_cannot_demote_last_owner(client) -> None:
	org_name = f"LastOwnerOrg-{uuid4().hex[:6]}"
	owner_email = f"solo-owner-{uuid4().hex[:6]}@example.com"
	password = "testpass123"

	owner_signup = client.post(
		"/api/auth/signup",
		json={
			"email": owner_email,
			"password": password,
			"organization_name": org_name,
			"role": "owner",
		},
	)
	assert owner_signup.status_code == 200
	owner_id = owner_signup.json()["id"]

	owner_login = client.post("/api/auth/login", data={"username": owner_email, "password": password})
	assert owner_login.status_code == 200
	owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}

	resp = client.patch(
		f"/api/auth/users/{owner_id}/role",
		json={"role": "admin"},
		headers=owner_headers,
	)
	assert resp.status_code == 422
	assert "last owner" in resp.json()["detail"].lower()
