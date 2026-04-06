from __future__ import annotations

import os
import sys
from urllib.parse import urlencode

import httpx


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _assert_ok(resp: httpx.Response, context: str) -> dict:
    if resp.status_code >= 400:
        raise RuntimeError(f"{context} failed: HTTP {resp.status_code} body={resp.text[:500]}")
    if "application/json" in (resp.headers.get("content-type", "")):
        return resp.json()
    return {"raw": resp.text}


def main() -> int:
    base_url = _require_env("SMOKE_API_BASE_URL").rstrip("/")
    email = _require_env("SMOKE_EMAIL")
    password = _require_env("SMOKE_PASSWORD")

    session = httpx.Client(timeout=20.0)

    login = session.post(
        f"{base_url}/api/auth/login",
        data={"username": email, "password": password},
    )
    token_payload = _assert_ok(login, "login")
    token = token_payload.get("access_token")
    if not token:
        raise RuntimeError("login did not return access_token")

    headers = {"Authorization": f"Bearer {token}"}

    me = session.get(f"{base_url}/api/auth/me", headers=headers)
    me_payload = _assert_ok(me, "get me")
    if me_payload.get("email") != email:
        raise RuntimeError("authenticated user mismatch in /api/auth/me")

    metrics = session.get(f"{base_url}/api/reports/lead-conversion?days=7", headers=headers)
    _assert_ok(metrics, "lead conversion metrics")

    audit = session.get(f"{base_url}/api/auth/users/role-audit?{urlencode({'limit': 5})}", headers=headers)
    audit_payload = _assert_ok(audit, "role audit list")
    if "events" not in audit_payload:
        raise RuntimeError("role audit list missing events field")

    export_resp = session.get(f"{base_url}/api/auth/users/role-audit/export.csv?{urlencode({'limit': 5})}", headers=headers)
    if export_resp.status_code >= 400:
        raise RuntimeError(f"role audit export failed: HTTP {export_resp.status_code}")
    if "text/csv" not in export_resp.headers.get("content-type", ""):
        raise RuntimeError("role audit export did not return text/csv")

    print("DEPLOY_SMOKE_OK")
    session.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover
        print(f"DEPLOY_SMOKE_FAILED: {exc}")
        raise
