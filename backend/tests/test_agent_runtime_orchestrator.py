from agent_runtime.orchestrator import run_orchestration
from agent_runtime.policies import choose_next_slice


def test_orchestration_happy_path_sets_done():
    def dispatch(role, objective, state, repo_context):
        if role == "planner":
            return {"status": "success", "summary": "planned"}
        if role == "architect":
            return {"status": "success", "summary": "designed"}
        if role == "backend_engineer":
            return {"status": "success", "summary": "implemented"}
        if role == "qa_engineer":
            return {"status": "success", "summary": "tests pass"}
        if role == "docs_engineer":
            return {"status": "success", "summary": "docs updated"}
        if role == "reviewer":
            return {"status": "success", "summary": "complete", "done": True}
        return {"status": "failed", "summary": "unknown role"}

    state = run_orchestration("Build vertical slice", {"repo": "x"}, dispatch)
    assert state.done is True
    assert state.blockers == []
    assert any(step.role == "reviewer" for step in state.completed_steps)


def test_orchestration_qa_failure_loops_back_to_backend():
    calls = {"backend": 0, "qa": 0}

    def dispatch(role, objective, state, repo_context):
        if role == "planner":
            return {"status": "success", "summary": "planned"}
        if role == "architect":
            return {"status": "success", "summary": "designed"}
        if role == "backend_engineer":
            calls["backend"] += 1
            return {"status": "success", "summary": f"backend pass {calls['backend']}"}
        if role == "qa_engineer":
            calls["qa"] += 1
            if calls["qa"] == 1:
                return {"status": "failed", "summary": "tests failed"}
            return {"status": "success", "summary": "tests fixed"}
        if role == "docs_engineer":
            return {"status": "success", "summary": "docs"}
        if role == "reviewer":
            return {"status": "success", "summary": "done", "done": True}
        return {"status": "failed", "summary": "unknown"}

    state = run_orchestration("Fix loop test", {}, dispatch)
    assert state.done is True
    assert calls["backend"] >= 2
    assert calls["qa"] >= 2


def test_orchestration_stall_response_is_redispatched():
    planner_calls = {"count": 0}

    def dispatch(role, objective, state, repo_context):
        if role == "planner":
            planner_calls["count"] += 1
            if planner_calls["count"] == 1:
                return {"status": "success", "summary": "Which would you like first?"}
            return {"status": "success", "summary": "planned after strict redispatch"}
        if role == "architect":
            return {"status": "success", "summary": "designed"}
        if role == "backend_engineer":
            return {"status": "success", "summary": "implemented"}
        if role == "qa_engineer":
            return {"status": "success", "summary": "qa pass"}
        if role == "docs_engineer":
            return {"status": "success", "summary": "docs pass"}
        if role == "reviewer":
            return {"status": "success", "summary": "done", "done": True}
        return {"status": "failed", "summary": "unknown"}

    state = run_orchestration("Stall guardrail test", {}, dispatch)
    assert state.done is True
    assert planner_calls["count"] == 2


def test_orchestration_stops_on_true_hard_blocker():
    def dispatch(role, objective, state, repo_context):
        if role == "planner":
            return {
                "status": "blocked",
                "summary": "blocked waiting for prod key",
                "blockers": ["MISSING_CREDENTIAL"],
            }
        return {"status": "failed", "summary": "should not run"}

    state = run_orchestration("Need prod integration", {}, dispatch)
    assert state.done is False
    assert "MISSING_CREDENTIAL" in state.blockers
    assert len(state.completed_steps) == 1


def test_choose_next_slice_priority_order():
    options = [
        "Polish dashboard shell",
        "Improve dispatch follow-up",
        "Build missed call recovery retries",
    ]
    picked = choose_next_slice(options)
    assert picked == "Build missed call recovery retries"
