import requests
from uuid import uuid4

BASE = "http://localhost:8001"
EMAIL = f"smoketestuser-{uuid4().hex[:8]}@example.com"
PASSWORD = "smoketestpass123"
ORG = f"SmokeTestOrg-{uuid4().hex[:6]}"


def require_ok(response: requests.Response) -> None:
	if response.status_code != 200:
		raise SystemExit(1)

print("1. Signup...")
r = requests.post(f"{BASE}/api/auth/signup", json={"email": EMAIL, "password": PASSWORD, "organization_name": ORG})
print("/api/auth/signup", r.status_code, r.json())
require_ok(r)

print("2. Login...")
r = requests.post(f"{BASE}/api/auth/login", data={"username": EMAIL, "password": PASSWORD})
print("/api/auth/login", r.status_code, r.json())
require_ok(r)

token = r.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"} if token else {}

print("3. Protected endpoint...")
r = requests.get(f"{BASE}/api/protected", headers=headers)
print("/api/protected", r.status_code, r.json())
require_ok(r)

print("4. Current organization...")
r = requests.get(f"{BASE}/api/auth/org", headers=headers)
print("/api/auth/org", r.status_code, r.json())
require_ok(r)
