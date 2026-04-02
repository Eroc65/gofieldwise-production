from typing import Any

from .dispatch import DispatchFn, normalize_dispatch_result
from .policies import extract_hard_blockers, has_stall_language
from .state import ExecutionState, StepResult


def _append_step(state: ExecutionState, role: str, objective: str, result: dict[str, Any]) -> None:
    step = StepResult(
        role=role,
        objective=objective,
        status=result["status"],
        summary=result.get("summary", ""),
        artifacts=result.get("artifacts", []),
        blockers=result.get("blockers", []),
        next_recommended_role=result.get("next_recommended_role"),
        next_objective=result.get("next_objective"),
    )
    state.completed_steps.append(step)


def _enqueue_followups(state: ExecutionState, result: dict[str, Any]) -> None:
    role = (state.active_objective or {}).get("role", "")

    # Respect explicit next recommendation if provided.
    nxt_role = result.get("next_recommended_role")
    nxt_obj = result.get("next_objective")
    if nxt_role and nxt_obj:
        state.pending_objectives.insert(0, {"role": nxt_role, "objective": nxt_obj})
        return

    if role == "planner":
        state.pending_objectives.append(
            {
                "role": "architect",
                "objective": "Inspect repo context and define touched modules for smallest complete vertical slice.",
            }
        )
        return

    if role == "architect":
        state.pending_objectives.append(
            {
                "role": "backend_engineer",
                "objective": "Implement backend and schema changes for the selected vertical slice.",
            }
        )
        return

    if role in {"backend_engineer", "frontend_engineer", "data_engineer", "devops_engineer", "reliability_engineer"}:
        state.pending_objectives.append(
            {
                "role": "qa_engineer",
                "objective": "Run deterministic validation (tests/checks) and report concrete failures.",
            }
        )
        state.pending_objectives.append(
            {
                "role": "docs_engineer",
                "objective": "Update docs/runbooks for changed behavior and operational notes.",
            }
        )
        return

    if role == "qa_engineer":
        if result["status"] == "failed":
            state.pending_objectives.insert(
                0,
                {
                    "role": "backend_engineer",
                    "objective": "Fix reported validation failures and rerun impacted checks.",
                },
            )
        else:
            state.pending_objectives.append(
                {
                    "role": "reviewer",
                    "objective": "Review completeness, residual risks, and remaining blockers.",
                }
            )
        return

    if role == "docs_engineer":
        if not any(x["role"] == "reviewer" for x in state.pending_objectives):
            state.pending_objectives.append(
                {
                    "role": "reviewer",
                    "objective": "Review completeness, residual risks, and remaining blockers.",
                }
            )
        return

    if role == "reviewer":
        if result.get("done"):
            state.done = True
        elif result["status"] == "failed":
            state.pending_objectives.append(
                {
                    "role": "backend_engineer",
                    "objective": "Resolve reviewer findings and close remaining gaps.",
                }
            )
        else:
            state.done = True


def run_orchestration(
    user_goal: str,
    repo_context: dict[str, Any],
    dispatch_fn: DispatchFn,
    *,
    max_loops: int = 20,
) -> ExecutionState:
    state = ExecutionState(
        user_goal=user_goal,
        repo_context=repo_context,
        max_loops=max_loops,
        pending_objectives=[
            {
                "role": "planner",
                "objective": f"Plan the smallest end-to-end vertical slice for: {user_goal}",
            }
        ],
    )

    while not state.done and state.loop_count < state.max_loops:
        state.loop_count += 1

        if not state.pending_objectives:
            state.done = True
            break

        state.active_objective = state.pending_objectives.pop(0)
        role = state.active_objective["role"]
        objective = state.active_objective["objective"]

        raw_result = dispatch_fn(role, objective, state, repo_context)
        result = normalize_dispatch_result(raw_result)

        # Anti-stall guardrail: re-dispatch immediately with stricter objective.
        if has_stall_language(result.get("summary", "")) and result["status"] != "blocked":
            stricter = (
                "Non-compliant response: choose the next highest-leverage step and execute it. "
                "Do not ask the user for preference. "
                + objective
            )
            raw_result = dispatch_fn(role, stricter, state, repo_context)
            result = normalize_dispatch_result(raw_result)

        _append_step(state, role, objective, result)

        if result["status"] == "blocked":
            hard = extract_hard_blockers(result.get("blockers", []))
            if hard:
                state.blockers.extend(hard)
                break
            # Non-hard blockers should not stop execution.

        if result.get("done") is True:
            state.done = True
            break

        _enqueue_followups(state, result)

    return state
