from dataclasses import asdict
from typing import Any

from .dispatch import DispatchFn, dispatch, dispatch_via_fn
from .policies import build_noncompliance_fix_objective, is_hard_blocker
from .state import ExecutionState, StepResult


def initialize_state(user_goal: str, repo_context: dict[str, Any]) -> ExecutionState:
    state = ExecutionState(
        user_goal=user_goal,
        repo_context=repo_context,
    )
    state.add_pending(
        "planner",
        f"Plan the smallest high-value end-to-end vertical slice for: {user_goal}",
    )
    return state


def enqueue_followups(state: ExecutionState, result: dict[str, Any]) -> None:
    role = state.active_objective["role"] if state.active_objective else ""

    if result.get("metadata", {}).get("stall_detected"):
        state.prepend_pending(
            "planner",
            build_noncompliance_fix_objective(),
        )
        return

    if role == "planner":
        state.add_pending(
            "architect",
            "Inspect the repo, choose touched modules, and define the implementation path.",
        )
        return

    if role == "architect":
        state.add_pending(
            "backend_engineer",
            "Implement the backend, schema, routes, tests, and supporting code for the chosen slice.",
        )
        return

    if role == "backend_engineer":
        state.add_pending(
            "qa_engineer",
            "Run tests and validation for the changed slice. Report failures concretely.",
        )
        state.add_pending(
            "docs_engineer",
            "Update any docs, setup notes, or runbooks affected by the implementation.",
        )
        return

    if role == "frontend_engineer":
        state.add_pending(
            "qa_engineer",
            "Validate the UI slice and report any failures concretely.",
        )
        return

    if role == "qa_engineer":
        if result["status"] == "failed":
            state.prepend_pending(
                "backend_engineer",
                "Fix the reported validation/test failures and re-run the relevant checks.",
            )
        else:
            state.add_pending(
                "reviewer",
                "Review the completed slice for completeness, missing pieces, and release readiness.",
            )
        return

    if role == "docs_engineer":
        if not any(x["role"] == "reviewer" for x in state.pending_objectives):
            state.add_pending(
                "reviewer",
                "Review the completed slice for completeness, missing pieces, and release readiness.",
            )
        return

    if role == "reviewer":
        if result.get("done") is True or result["status"] == "success":
            if result.get("next_recommended_role") and result.get("next_objective"):
                state.add_pending(result["next_recommended_role"], result["next_objective"])
            else:
                state.done = True
        elif result["status"] == "failed":
            state.add_pending(
                "backend_engineer",
                "Resolve reviewer findings and complete the missing parts of the slice.",
            )


def should_stop_for_blockers(result: dict[str, Any]) -> bool:
    if result["status"] != "blocked":
        return False
    if not result["blockers"]:
        return True
    return any(is_hard_blocker(code) for code in result["blockers"])


def run_orchestration(
    user_goal: str,
    repo_context: dict[str, Any] | None = None,
    dispatch_fn: DispatchFn | None = None,
    max_loops: int = 20,
) -> ExecutionState:
    state = initialize_state(user_goal, repo_context or {})
    state.max_loops = max_loops

    while not state.done and state.loop_count < state.max_loops:
        state.loop_count += 1

        if not state.pending_objectives:
            state.done = True
            break

        state.active_objective = state.pending_objectives.pop(0)
        role = state.active_objective["role"]
        objective = state.active_objective["objective"]

        if dispatch_fn is not None:
            result = dispatch_via_fn(
                role=role,
                objective=objective,
                state=asdict(state),
                repo_context=state.repo_context,
                dispatch_fn=dispatch_fn,
            )
        else:
            result = dispatch(
                role=role,
                objective=objective,
                state=asdict(state),
                repo_context=state.repo_context,
            )

        step = StepResult(
            role=role,
            objective=objective,
            status=result["status"],
            summary=result["summary"],
            artifacts=result["artifacts"],
            blockers=result["blockers"],
            next_recommended_role=result.get("next_recommended_role"),
            next_objective=result.get("next_objective"),
            done=result.get("done", False),
            metadata=result.get("metadata", {}),
        )
        state.add_step(step)

        if should_stop_for_blockers(result):
            break

        if step.done:
            state.done = True
            break

        enqueue_followups(state, result)

    return state


def format_final_output(state: ExecutionState) -> dict[str, Any]:
    files_touched: list[str] = []
    for step in state.completed_steps:
        for path in step.artifacts:
            if path not in files_touched:
                files_touched.append(path)

    latest = state.latest_step
    return {
        "done": state.done,
        "loop_count": state.loop_count,
        "blockers": state.blockers,
        "latest_summary": latest.summary if latest else "",
        "files_touched": files_touched,
        "steps": [
            {
                "role": s.role,
                "objective": s.objective,
                "status": s.status,
                "summary": s.summary,
                "artifacts": s.artifacts,
            }
            for s in state.completed_steps
        ],
    }
