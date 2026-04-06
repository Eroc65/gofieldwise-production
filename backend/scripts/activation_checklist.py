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


def _api_get_safe(base: str, token: str, path: str) -> tuple[Any | None, str | None]:
    try:
        return _api_get(base, token, path), None
    except Exception as exc:
        return None, str(exc)


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

    status, status_err = _api_get_safe(base, token, "/api/status")
    guide, guide_err = _api_get_safe(base, token, "/api/org/ai-guide")
    comm_profile, comm_err = _api_get_safe(base, token, "/api/org/comm-profile")
    packages, pkg_err = _api_get_safe(base, token, "/api/marketing/service-packages")

    reactivation_dry = None
    react_err = None
    try:
        reactivation_dry = _api_post(
            base,
            token,
            "/api/marketing/reactivation/run",
            {"lookback_days": 180, "limit": 20, "dry_run": True},
        )
    except Exception as exc:
        react_err = str(exc)

    readiness = {
        "status_endpoint_ok": bool(status and status.get("status") == "ok"),
        "ai_guide_endpoint_ok": bool(guide and "enabled" in guide and "stage" in guide),
        "comm_profile_active": bool(comm_profile and comm_profile.get("active", False)),
        "twilio_sid_present": bool(comm_profile and comm_profile.get("twilio_account_sid")),
        "retell_agent_present": bool(comm_profile and comm_profile.get("retell_agent_id")),
        "packages_present": isinstance(packages, list) and len(packages) > 0,
        "reactivation_dry_run_ok": bool(reactivation_dry and "candidate_count" in reactivation_dry),
    }

    blockers = []
    if status_err:
        blockers.append(status_err)
    if guide_err:
        blockers.append(guide_err)
    if comm_err:
        blockers.append(comm_err)
    if pkg_err:
        blockers.append(pkg_err)
    if react_err:
        blockers.append(react_err)
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
