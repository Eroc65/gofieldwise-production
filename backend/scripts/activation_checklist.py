from __future__ import annotations

import os
import sys
from typing import Any

import httpx


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _login(base: str, email: str, password: str) -> str:
    resp = httpx.post(
        f"{base}/api/auth/login",
        data={"username": email, "password": password},
        timeout=20.0,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"Login failed: {resp.status_code} {resp.text[:300]}")
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("Login did not return access_token")
    return str(token)


def _api_get(base: str, token: str, path: str) -> Any:
    resp = httpx.get(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20.0,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"GET {path} failed: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def _api_post(base: str, token: str, path: str, payload: dict) -> Any:
    resp = httpx.post(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=20.0,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"POST {path} failed: {resp.status_code} {resp.text[:300]}")
    return resp.json()


def main() -> int:
    base = _require("ACTIVATION_API_BASE_URL").rstrip("/")
    email = _require("ACTIVATION_EMAIL")
    password = _require("ACTIVATION_PASSWORD")

    token = _login(base, email, password)

    status = _api_get(base, token, "/api/status")
    guide = _api_get(base, token, "/api/org/ai-guide")
    comm_profile = _api_get(base, token, "/api/org/comm-profile")
    packages = _api_get(base, token, "/api/marketing/service-packages")
    reactivation_dry = _api_post(
        base,
        token,
        "/api/marketing/reactivation/run",
        {"lookback_days": 180, "limit": 20, "dry_run": True},
    )

    readiness = {
        "status_endpoint_ok": bool(status.get("status") == "ok"),
        "ai_guide_endpoint_ok": bool("enabled" in guide and "stage" in guide),
        "comm_profile_active": bool(comm_profile.get("active", False)),
        "twilio_sid_present": bool(comm_profile.get("twilio_account_sid")),
        "retell_agent_present": bool(comm_profile.get("retell_agent_id")),
        "packages_present": isinstance(packages, list) and len(packages) > 0,
        "reactivation_dry_run_ok": "candidate_count" in reactivation_dry,
    }

    blockers = []
    if not readiness["comm_profile_active"]:
        blockers.append("Communication profile is inactive")
    if not readiness["twilio_sid_present"]:
        blockers.append("Twilio account SID missing in tenant profile")
    if not readiness["retell_agent_present"]:
        blockers.append("Retell agent ID missing in tenant profile")

    print("ACTIVATION_READINESS", readiness)
    print("ACTIVATION_BLOCKERS", blockers if blockers else "none")
    if blockers:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
