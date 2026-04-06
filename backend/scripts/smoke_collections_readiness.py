from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import requests

BASE = "http://localhost:8001"
EMAIL = f"smokecollect-{uuid4().hex[:8]}@example.com"
PASSWORD = "smokecollectpass123"
ORG = f"SmokeCollectionsOrg-{uuid4().hex[:6]}"


def require_status(response: requests.Response, code: int) -> None:
    if response.status_code != code:
        print("FAILED", response.status_code, response.text)
        raise SystemExit(1)


def iso(hours: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


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
    json={"name": "Collections Customer", "phone": "555-9191"},
    headers=headers,
)
print("/api/customers", r.status_code, r.json())
require_status(r, 201)
customer_id = r.json()["id"]

print("4) Create technician")
r = requests.post(
    f"{BASE}/api/technicians",
    json={
        "name": "Collections Tech",
        "availability_start_hour_utc": 0,
        "availability_end_hour_utc": 24,
        "availability_weekdays": "0,1,2,3,4,5,6",
    },
    headers=headers,
)
print("/api/technicians", r.status_code, r.json())
require_status(r, 201)
technician_id = r.json()["id"]

print("5) Create job + approved estimate")
r = requests.post(
    f"{BASE}/api/jobs",
    json={"title": "Collections Job Auto", "customer_id": customer_id},
    headers=headers,
)
print("/api/jobs", r.status_code, r.json())
require_status(r, 201)
job_id = r.json()["id"]

r = requests.post(
    f"{BASE}/api/estimates",
    json={"amount": 725.0, "job_id": job_id, "description": "Approved estimate for auto invoice"},
    headers=headers,
)
print("/api/estimates", r.status_code, r.json())
require_status(r, 201)
estimate_id = r.json()["id"]

r = requests.patch(
    f"{BASE}/api/estimates/{estimate_id}/status",
    json={"status": "approved"},
    headers=headers,
)
print("/api/estimates/{estimate_id}/status", r.status_code, r.json())
require_status(r, 200)

print("6) Dispatch + complete to auto-create invoice")
r = requests.patch(
    f"{BASE}/api/jobs/{job_id}/dispatch",
    json={"technician_id": technician_id, "scheduled_time": iso(2)},
    headers=headers,
)
print("/api/jobs/{job_id}/dispatch", r.status_code, r.json())
require_status(r, 200)

r = requests.patch(
    f"{BASE}/api/jobs/{job_id}/complete",
    json={"completion_notes": "Completed during collections smoke"},
    headers=headers,
)
print("/api/jobs/{job_id}/complete", r.status_code, r.json())
require_status(r, 200)

r = requests.get(f"{BASE}/api/invoices", headers=headers)
print("/api/invoices", r.status_code, r.json())
require_status(r, 200)
all_invoices = r.json()
auto_invoice = next((inv for inv in all_invoices if inv.get("job_id") == job_id), None)
if not auto_invoice:
    raise SystemExit("Expected auto invoice for completed approved estimate")

print("7) Create overdue invoice for escalation path")
r = requests.post(
    f"{BASE}/api/jobs",
    json={"title": "Collections Job Overdue", "customer_id": customer_id},
    headers=headers,
)
print("/api/jobs #2", r.status_code, r.json())
require_status(r, 201)
job2_id = r.json()["id"]

r = requests.post(
    f"{BASE}/api/invoices",
    json={"amount": 410.0, "job_id": job2_id, "due_at": iso_days_ago(14)},
    headers=headers,
)
print("/api/invoices #overdue", r.status_code, r.json())
require_status(r, 201)
overdue_invoice_id = r.json()["id"]

print("8) Escalate payments")
r = requests.post(f"{BASE}/api/invoices/escalate-payments", headers=headers)
print("/api/invoices/escalate-payments", r.status_code, r.json())
require_status(r, 200)
escalation = r.json()
if escalation.get("total_escalations", 0) < 1:
    raise SystemExit("Expected at least one escalation for overdue invoice")

print("9) Mark overdue invoice paid and verify base collection reminder suppression")
r = requests.patch(
    f"{BASE}/api/invoices/{overdue_invoice_id}/status",
    json={"status": "paid"},
    headers=headers,
)
print("/api/invoices/{id}/status", r.status_code, r.json())
require_status(r, 200)

r = requests.get(
    f"{BASE}/api/reminders",
    params={"job_id": job2_id},
    headers=headers,
)
print("/api/reminders?job_id", r.status_code, r.json())
require_status(r, 200)
reminders = r.json()
base_msg = f"Collect payment for invoice #{overdue_invoice_id}"
base_reminder = next((rm for rm in reminders if rm.get("message") == base_msg), None)
if base_reminder is None:
    raise SystemExit("Expected base collection reminder for overdue invoice")
if base_reminder.get("status") != "dismissed":
    raise SystemExit("Expected base collection reminder to be dismissed after payment")

print("OK: collections readiness smoke test passed")
