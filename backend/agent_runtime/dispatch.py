import json
import os
import urllib.error
import urllib.request
from typing import Any, Callable

from .policies import looks_like_stall


DispatchResult = dict[str, Any]


DispatchFn = Callable[[str, str, dict[str, Any], dict[str, Any]], dict[str, Any]]


ROLE_SYSTEM_PROMPTS: dict[str, str] = {
    "planner": (
        "You are the planner. Define the smallest high-value end-to-end vertical slice. "
        "Do not ask the user to choose between valid options. Choose the best option."
    ),
    "architect": (
        "You are the architect. Inspect repo context, choose touched modules, schema, API, tests, "
        "and implementation path. Be concrete."
    ),
    "backend_engineer": (
        "You are the backend engineer. Implement the required code changes. "
        "Do not stop at planning; describe concrete file-level work."
    ),
    "frontend_engineer": (
        "You are the frontend engineer. Implement UI changes needed for the current slice. "
        "Prefer minimal functional UI over polish."
    ),
    "qa_engineer": (
        "You are the QA engineer. Run validation, identify failures, and return actionable results."
    ),
    "docs_engineer": (
        "You are the docs engineer. Update setup docs, workflow docs, and runbooks impacted by the changes."
    ),
    "reviewer": (
        "You are the reviewer. Verify completeness, identify missing pieces, and mark done only if the vertical slice is complete."
    ),
}


def build_dispatch_payload(
    *,
    role: str,
    objective: str,
    state: dict[str, Any],
    repo_context: dict[str, Any],
) -> dict[str, Any]:
    return {
        "role": role,
        "system_prompt": ROLE_SYSTEM_PROMPTS[role],
        "objective": objective,
        "state": state,
        "repo_context": repo_context,
        "response_contract": {
            "status": "success|failed|blocked",
            "summary": "short text",
            "artifacts": ["list", "of", "files"],
            "blockers": ["list", "of", "blocker_codes_or_messages"],
            "next_recommended_role": "optional role",
            "next_objective": "optional next objective",
            "done": False,
            "metadata": {},
        },
    }


def validate_dispatch_result(result: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(result or {})
    status = normalized.get("status")
    if status not in {"success", "failed", "blocked"}:
        normalized["status"] = "failed"
        normalized["summary"] = f"Invalid dispatch status: {status!r}"
        normalized.setdefault("artifacts", [])
        normalized.setdefault("blockers", ["INVALID_DISPATCH_STATUS"])

    normalized.setdefault("summary", "")
    normalized.setdefault("artifacts", [])
    normalized.setdefault("blockers", [])
    normalized.setdefault("next_recommended_role", None)
    normalized.setdefault("next_objective", None)
    normalized.setdefault("done", False)
    normalized.setdefault("metadata", {})

    normalized["summary"] = str(normalized["summary"])
    normalized["artifacts"] = list(normalized["artifacts"] or [])
    normalized["blockers"] = list(normalized["blockers"] or [])
    normalized["done"] = bool(normalized["done"])
    normalized["metadata"] = dict(normalized["metadata"] or {})

    if looks_like_stall(normalized["summary"]):
        normalized["status"] = "failed"
        normalized["blockers"] = ["NONCOMPLIANT_STALL_RESPONSE"]
        normalized["metadata"]["stall_detected"] = True

    return normalized


def model_invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Invoke a runtime adapter for orchestration dispatch.

    Modes are controlled by AGENT_RUNTIME_DISPATCH_MODE:
    - mock (default): deterministic local adapter for development/testing
    - http: POST payload to AGENT_RUNTIME_DISPATCH_ENDPOINT
    """
    mode = os.getenv("AGENT_RUNTIME_DISPATCH_MODE", "mock").strip().lower()
    if mode == "mock":
        return _mock_model_invoke(payload)
    if mode == "http":
        return _http_model_invoke(payload)
    return {
        "status": "blocked",
        "summary": f"Unsupported dispatch mode: {mode}",
        "artifacts": [],
        "blockers": ["UNSUPPORTED_DISPATCH_MODE"],
        "done": False,
        "metadata": {"dispatch_mode": mode},
    }


def _mock_model_invoke(payload: dict[str, Any]) -> dict[str, Any]:
    role = str(payload.get("role", ""))
    objective = str(payload.get("objective", ""))
    next_role_map = {
        "planner": "architect",
        "architect": "backend_engineer",
        "backend_engineer": "qa_engineer",
        "qa_engineer": "reviewer",
        "docs_engineer": "reviewer",
    }
    return {
        "status": "success",
        "summary": f"[{role}] mock execution complete: {objective[:120]}",
        "artifacts": [],
        "blockers": [],
        "next_recommended_role": next_role_map.get(role),
        "next_objective": None,
        "done": role == "reviewer",
        "metadata": {"dispatch_mode": "mock"},
    }


def _http_model_invoke(payload: dict[str, Any]) -> dict[str, Any]:
    endpoint = os.getenv("AGENT_RUNTIME_DISPATCH_ENDPOINT", "").strip()
    timeout_raw = os.getenv("AGENT_RUNTIME_DISPATCH_TIMEOUT_SECONDS", "30").strip()

    if not endpoint:
        return {
            "status": "blocked",
            "summary": "AGENT_RUNTIME_DISPATCH_ENDPOINT is required for http mode",
            "artifacts": [],
            "blockers": ["MISSING_DISPATCH_ENDPOINT"],
            "done": False,
            "metadata": {"dispatch_mode": "http"},
        }

    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = 30.0

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8")
        parsed = json.loads(response_body) if response_body else {}
    except urllib.error.HTTPError as exc:
        return {
            "status": "blocked",
            "summary": f"Dispatch endpoint HTTP error: {exc.code}",
            "artifacts": [],
            "blockers": ["DISPATCH_ENDPOINT_HTTP_ERROR"],
            "done": False,
            "metadata": {"dispatch_mode": "http", "http_status": exc.code},
        }
    except urllib.error.URLError:
        return {
            "status": "blocked",
            "summary": "Dispatch endpoint is unreachable",
            "artifacts": [],
            "blockers": ["DISPATCH_ENDPOINT_UNREACHABLE"],
            "done": False,
            "metadata": {"dispatch_mode": "http"},
        }
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "summary": "Dispatch endpoint returned invalid JSON",
            "artifacts": [],
            "blockers": ["INVALID_DISPATCH_RESPONSE_JSON"],
            "done": False,
            "metadata": {"dispatch_mode": "http"},
        }

    if not isinstance(parsed, dict):
        return {
            "status": "failed",
            "summary": "Dispatch endpoint response must be a JSON object",
            "artifacts": [],
            "blockers": ["INVALID_DISPATCH_RESPONSE_SHAPE"],
            "done": False,
            "metadata": {"dispatch_mode": "http"},
        }

    return parsed


def dispatch(
    *,
    role: str,
    objective: str,
    state: dict[str, Any],
    repo_context: dict[str, Any],
) -> dict[str, Any]:
    payload = build_dispatch_payload(
        role=role,
        objective=objective,
        state=state,
        repo_context=repo_context,
    )
    raw = model_invoke(payload)
    return validate_dispatch_result(raw)


def dispatch_via_fn(
    *,
    role: str,
    objective: str,
    state: dict[str, Any],
    repo_context: dict[str, Any],
    dispatch_fn: DispatchFn,
) -> dict[str, Any]:
    raw = dispatch_fn(role, objective, state, repo_context)
    return validate_dispatch_result(raw)
