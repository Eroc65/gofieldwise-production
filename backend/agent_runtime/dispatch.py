from collections.abc import Mapping
from typing import Any, Callable

from .state import ExecutionState


DispatchResult = dict[str, Any]


DispatchFn = Callable[[str, str, ExecutionState, dict[str, Any]], dict[str, Any]]


def normalize_dispatch_result(raw: Mapping[str, Any] | None) -> DispatchResult:
    if raw is None:
        raw = {}

    status = raw.get("status", "failed")
    if status not in {"success", "failed", "blocked"}:
        status = "failed"

    return {
        "status": status,
        "summary": str(raw.get("summary", "")),
        "artifacts": list(raw.get("artifacts", []) or []),
        "blockers": list(raw.get("blockers", []) or []),
        "next_recommended_role": raw.get("next_recommended_role"),
        "next_objective": raw.get("next_objective"),
        "done": bool(raw.get("done", False)),
    }
