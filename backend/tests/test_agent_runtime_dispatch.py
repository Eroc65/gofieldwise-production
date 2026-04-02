from agent_runtime.dispatch import dispatch, model_invoke, validate_dispatch_result


def test_model_invoke_parses_structured_result(monkeypatch):
    def fake_invoke(messages):
        assert len(messages) == 2
        return '{"status":"success","summary":"ok","artifacts":[],"blockers":[],"done":false,"metadata":{}}'

    monkeypatch.setattr("agent_runtime.dispatch.invoke_openai_compatible_chat", fake_invoke)

    result = model_invoke(
        {
            "role": "planner",
            "system_prompt": "planner prompt",
            "objective": "Plan a slice",
            "state": {},
            "repo_context": {},
            "response_contract": {},
        }
    )

    assert result["status"] == "success"
    assert result["summary"] == "ok"


def test_dispatch_calls_model_and_normalizes(monkeypatch):
    def fake_model_invoke(payload):
        assert payload["role"] == "reviewer"
        return {
            "status": "success",
            "summary": "complete",
            "artifacts": ["backend/agent_runtime/dispatch.py"],
            "blockers": [],
            "done": True,
            "metadata": {},
        }

    monkeypatch.setattr("agent_runtime.dispatch.model_invoke", fake_model_invoke)

    result = dispatch(
        role="reviewer",
        objective="Review slice",
        state={},
        repo_context={},
    )

    assert result["status"] == "success"
    assert result["done"] is True
    assert result["artifacts"] == ["backend/agent_runtime/dispatch.py"]


def test_validate_dispatch_result_flags_stall():
    result = validate_dispatch_result(
        {
            "status": "success",
            "summary": "Which would you like me to do first?",
            "artifacts": [],
            "blockers": [],
            "metadata": {},
        }
    )

    assert result["status"] == "failed"
    assert result["blockers"] == ["NONCOMPLIANT_STALL_RESPONSE"]
    assert result["metadata"]["stall_detected"] is True
