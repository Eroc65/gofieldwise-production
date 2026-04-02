from __future__ import annotations

import json
from typing import Any, Callable

from agent_runtime.model_backend import invoke_openai_compatible_chat, parse_structured_result
from agent_runtime.policies import looks_like_stall
from agent_runtime.tool_executor import ToolExecutionError, ToolExecutor


DispatchResult = dict[str, Any]
DispatchFn = Callable[[str, str, dict[str, Any], dict[str, Any]], dict[str, Any]]
MAX_TOOL_LOOPS = 12


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


def validate_dispatch_result(result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("status")
    if status not in {"success", "failed", "blocked"}:
        result["status"] = "failed"
        result["summary"] = f"Invalid dispatch status: {status!r}"
        result.setdefault("artifacts", [])
        result.setdefault("blockers", ["INVALID_DISPATCH_STATUS"])

    result.setdefault("summary", "")
    result.setdefault("artifacts", [])
    result.setdefault("blockers", [])
    result.setdefault("next_recommended_role", None)
    result.setdefault("next_objective", None)
    result.setdefault("done", False)
    result.setdefault("metadata", {})

    if looks_like_stall(result["summary"]):
        result["status"] = "failed"
        result["blockers"] = ["NONCOMPLIANT_STALL_RESPONSE"]
        result["metadata"]["stall_detected"] = True

    return result


def _compress_state_for_prompt(state: dict[str, Any]) -> dict[str, Any]:
    """
    Keep prompts bounded. We do not need the full repo dump every loop.
    """
    completed_steps = state.get("completed_steps", [])
    recent_steps = completed_steps[-5:] if isinstance(completed_steps, list) else []

    return {
        "user_goal": state.get("user_goal"),
        "loop_count": state.get("loop_count"),
        "done": state.get("done"),
        "active_objective": state.get("active_objective"),
        "pending_objectives": state.get("pending_objectives", [])[:5],
        "blockers": state.get("blockers", []),
        "recent_steps": recent_steps,
    }


def _build_initial_messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    system = (
        payload["system_prompt"]
        + "\n\n"
        + "You are part of an autonomous orchestration loop.\n"
        + "You may either request one tool call at a time or return the final JSON result.\n"
        + "Do not return markdown. Do not return code fences. Do not ask the user to choose.\n"
        + "If multiple valid next steps exist, choose the highest-leverage one and continue.\n"
        + "\n"
        + "Tool request format:\n"
        + json.dumps(
            {
                "action": "tool",
                "tool_name": "read_file|write_file|append_file|list_dir|search_text|run_command",
                "args": {},
                "reason": "why this tool call is needed",
            },
            indent=2,
        )
        + "\n\n"
        + "Final result format:\n"
        + json.dumps(
            {
                "status": "success",
                "summary": "short result",
                "artifacts": [],
                "blockers": [],
                "next_recommended_role": None,
                "next_objective": None,
                "done": False,
                "metadata": {},
            },
            indent=2,
        )
    )

    user = "Dispatch payload:\n" + json.dumps(
        {
            "role": payload["role"],
            "objective": payload["objective"],
            "repo_context": payload["repo_context"],
            "state": _compress_state_for_prompt(payload["state"]),
            "response_contract": payload["response_contract"],
        },
        indent=2,
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _is_tool_request(obj: dict[str, Any]) -> bool:
    return obj.get("action") == "tool" and "tool_name" in obj


def _tool_result_message(tool_result: dict[str, Any]) -> dict[str, str]:
    return {
        "role": "user",
        "content": "Tool result:\n" + json.dumps(tool_result, indent=2),
    }


def model_invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Tool-using model adapter.

    The model may:
    1. request a tool call
    2. inspect the tool result
    3. request another tool
    4. eventually return the final structured dispatch result
    """
    messages = _build_initial_messages(payload)
    executor = ToolExecutor(repo_root=payload.get("repo_context", {}).get("repo_root", "."))

    for _ in range(MAX_TOOL_LOOPS):
        raw_text = invoke_openai_compatible_chat(messages)
        obj = parse_structured_result(raw_text)

        if _is_tool_request(obj):
            try:
                tool_result = executor.execute(
                    {
                        "tool_name": obj["tool_name"],
                        "args": obj.get("args", {}),
                    }
                )
            except ToolExecutionError as exc:
                tool_result = {
                    "tool_name": obj.get("tool_name"),
                    "ok": False,
                    "error": str(exc),
                }

            messages.append({"role": "assistant", "content": json.dumps(obj)})
            messages.append(_tool_result_message(tool_result))
            continue

        return obj

    return {
        "status": "blocked",
        "summary": "Tool-use loop exceeded maximum iterations.",
        "artifacts": [],
        "blockers": ["TOOL_LOOP_EXCEEDED"],
        "next_recommended_role": None,
        "next_objective": None,
        "done": False,
        "metadata": {"max_tool_loops": MAX_TOOL_LOOPS},
    }


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
