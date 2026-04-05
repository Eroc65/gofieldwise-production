from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _default_base_url() -> str:
    return os.getenv("AGENT_MODEL_BASE_URL", "http://localhost:1234/v1")


def _default_health_path() -> str:
    return os.getenv("AGENT_MODEL_HEALTH_PATH", "/models")


def _health_url(base_url: str | None = None, health_path: str | None = None) -> str:
    base = (base_url or _default_base_url()).rstrip("/")
    path = health_path or _default_health_path()
    return f"{base}{path}" if path.startswith("/") else f"{base}/{path}"


def probe_model_backend(
    base_url: str | None = None,
    health_path: str | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    timeout = timeout_seconds or float(os.getenv("AGENT_MODEL_PRECHECK_TIMEOUT_SECONDS", "4"))
    url = _health_url(base_url, health_path)

    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return {
                "ok": 200 <= getattr(resp, "status", 200) < 300,
                "url": url,
                "status": getattr(resp, "status", 200),
                "body_excerpt": body[:500],
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "ok": False,
            "url": url,
            "status": exc.code,
            "error": f"HTTP {exc.code}",
            "body_excerpt": body[:500],
        }
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "url": url,
            "status": None,
            "error": str(exc.reason),
            "body_excerpt": "",
        }


def _find_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_recovery_script() -> dict[str, Any]:
    repo_root = _find_repo_root()
    script_path = repo_root / "scripts" / "ensure_model_backend.ps1"

    if not script_path.exists():
        return {
            "ok": False,
            "error": f"Recovery script not found: {script_path}",
            "stdout": "",
            "stderr": "",
            "returncode": None,
        }

    if os.name == "nt":
        exe = "powershell"
    else:
        exe = shutil.which("pwsh") or shutil.which("powershell") or "powershell"

    try:
        completed = subprocess.run(
            [
                exe,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
            ],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=int(os.getenv("AGENT_MODEL_RECOVERY_SCRIPT_TIMEOUT_SECONDS", "60")),
            shell=False,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "stdout": "",
            "stderr": "",
            "returncode": None,
        }


def ensure_model_backend_available(
    base_url: str | None = None,
    *,
    allow_recovery: bool = True,
    force_recovery: bool = False,
) -> dict[str, Any]:
    """
    Ensure the model backend is reachable.

    If unavailable and recovery is allowed, try the PowerShell recovery script,
    then probe again.
    """
    probe = probe_model_backend(base_url=base_url)
    if probe["ok"] and not force_recovery:
        return {
            "ok": True,
            "probe": probe,
            "recovery_attempted": False,
            "recovery_result": None,
        }

    autorecover = os.getenv("AGENT_MODEL_AUTORECOVER", "1").strip() not in {"0", "false", "False"}
    if not allow_recovery or not autorecover:
        raise RuntimeError(
            f"Model backend unavailable at {probe['url']}: "
            f"{probe.get('error') or probe.get('body_excerpt') or 'unknown error'}"
        )

    recovery_result = _run_recovery_script()
    probe_after = probe_model_backend(base_url=base_url)

    if not probe_after["ok"]:
        raise RuntimeError(
            "Model backend unavailable after recovery attempt: "
            + json.dumps(
                {
                    "probe_before": probe,
                    "recovery_result": recovery_result,
                    "probe_after": probe_after,
                },
                indent=2,
            )
        )

    return {
        "ok": True,
        "probe": probe_after,
        "recovery_attempted": True,
        "recovery_result": recovery_result,
    }
