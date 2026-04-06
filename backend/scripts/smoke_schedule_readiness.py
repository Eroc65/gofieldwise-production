from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import requests

BASE = "http://localhost:8001"
EMAIL = f"smokeschedule-{uuid4().hex[:8]}@example.com"
PASSWORD = "smokeschedulepass123"
ORG = f"SmokeScheduleOrg-{uuid4().hex[:6]}"


def require_status(response: requests.Response, code: int) -> None:
    if response.status_code != code:
        print("FAILED", response.status_code, response.text)
        raise SystemExit(1)


def iso(hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


print("1) Signup")
r = requests.post(
    f"{BASE}/api/auth/signup",
    json={"email": EMAIL, "password": PASSWORD, "organization_name": ORG},
)
print("/api/auth/signup", r.status_code, r.json())
require_status(r, 200)

print("2) Login")
r = requests.post(
    f"{BASE}/api/auth/login",
    data={"username": EMAIL, "password": PASSWORD},
)
print("/api/auth/login", r.status_code, r.json())
require_status(r, 200)

token = r.json().get("access_token")
if not token:
    raise SystemExit("Missing access token")
headers = {"Authorization": f"Bearer {token}"}

print("3) Create customer")
r = requests.post(
    f"{BASE}/api/customers",
    json={"name": "Schedule Customer", "phone": "555-8080"},
    headers=headers,
)
print("/api/customers", r.status_code, r.json())
require_status(r, 201)
customer_id = r.json()["id"]

print("4) Create technician")
r = requests.post(
    f"{BASE}/api/technicians",
    json={
        "name": "Schedule Tech",
        "availability_start_hour_utc": 0,
        "availability_end_hour_utc": 24,
        "availability_weekdays": "0,1,2,3,4,5,6",
    },
    headers=headers,
)
print("/api/technicians", r.status_code, r.json())
require_status(r, 201)
technician_id = r.json()["id"]

print("5) Create two jobs")
r1 = requests.post(
    f"{BASE}/api/jobs",
    json={"title": "Job One", "customer_id": customer_id},
    headers=headers,
)
r2 = requests.post(
    f"{BASE}/api/jobs",
    json={"title": "Job Two", "customer_id": customer_id},
    headers=headers,
)
print("/api/jobs #1", r1.status_code, r1.json())
print("/api/jobs #2", r2.status_code, r2.json())
require_status(r1, 201)
require_status(r2, 201)
job1_id = r1.json()["id"]

slot = iso(3)

print("6) Dispatch first job")
r = requests.patch(
    f"{BASE}/api/jobs/{job1_id}/dispatch",
    json={"technician_id": technician_id, "scheduled_time": slot},
    headers=headers,
)
print("/api/jobs/{job1_id}/dispatch", r.status_code, r.json())
require_status(r, 200)

print("7) Check scheduling conflict")
r = requests.get(
    f"{BASE}/api/jobs/scheduling/conflict",
    params={"technician_id": technician_id, "scheduled_time": slot, "buffer_minutes": 15},
    headers=headers,
)
print("/api/jobs/scheduling/conflict", r.status_code, r.json())
require_status(r, 200)
if r.json().get("conflict") is not True:
    raise SystemExit("Expected conflict=true")

print("8) Find next available slot")
r = requests.get(
    f"{BASE}/api/jobs/scheduling/next-slot",
    params={
        "technician_id": technician_id,
        "requested_time": slot,
        "search_hours": 4,
        "step_minutes": 30,
        "buffer_minutes": 15,
    },
    headers=headers,
)
print("/api/jobs/scheduling/next-slot", r.status_code, r.json())
require_status(r, 200)
next_slot = r.json().get("next_available_time")
if not next_slot or next_slot == slot:
    raise SystemExit("Expected a non-conflicting next slot")

print("OK: schedule readiness smoke test passed")
