from __future__ import annotations

from typing import Any


def _has_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(n in lowered for n in needles)


def choose_tool_mode(role: str, objective: str, repo_context: dict[str, Any] | None = None) -> str:
    """
    Choose the safest mode that still allows the role to complete its work.

    Modes:
    - readonly
    - test
    - dev
    - deploy
    - production_safe
    """
    repo_context = repo_context or {}
    _ = repo_context
    text = f"{role} {objective}".lower()

    if _has_any(text, ["deploy", "publish", "render", "ship build", "promote"]):
        return "deploy"

    if _has_any(
        text,
        [
            "production",
            "prod",
            "live system",
            "health check",
            "metrics",
            "reconcile",
            "broker",
            "ibkr",
            "observability",
            "alert",
            "n8n",
            "workflow sync",
            "smoke test against running service",
        ],
    ):
        return "production_safe"

    if role in {"planner", "architect", "reviewer"}:
        return "readonly"

    if role == "qa_engineer":
        if _has_any(text, ["run tests", "validate", "pytest", "smoke", "lint", "type check"]):
            return "test"
        return "readonly"

    if role in {"backend_engineer", "frontend_engineer", "docs_engineer"}:
        return "dev"

    if _has_any(text, ["implement", "build", "write", "refactor", "update docs", "add tests", "fix"]):
        return "dev"

    if _has_any(text, ["test", "validate", "lint", "smoke", "assert"]):
        return "test"

    return "readonly"