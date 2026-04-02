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


def test_model_invoke_tool_request_then_final(monkeypatch):
    replies = [
        '{"action":"tool","tool_name":"list_dir","args":{"path":"agent_runtime"},"reason":"inspect"}',
        '{"status":"success","summary":"implemented","artifacts":["agent_runtime/dispatch.py"],"blockers":[],"done":false,"metadata":{}}',
    ]

    def fake_invoke(_messages):
        return replies.pop(0)

    class FakeExecutor:
        def __init__(self, repo_root):
            self.repo_root = repo_root

        def execute(self, request):
            assert request["tool_name"] == "list_dir"
            return {"tool_name": "list_dir", "ok": True, "entries": ["agent_runtime/"]}

    monkeypatch.setattr("agent_runtime.dispatch.invoke_openai_compatible_chat", fake_invoke)
    monkeypatch.setattr("agent_runtime.dispatch.ToolExecutor", FakeExecutor)

    result = model_invoke(
        {
            "role": "backend_engineer",
            "system_prompt": "backend prompt",
            "objective": "Build feature",
            "state": {},
            "repo_context": {"repo_root": "."},
            "response_contract": {},
        }
    )

    assert result["status"] == "success"
    assert result["summary"] == "implemented"


def test_model_invoke_returns_blocked_when_tool_loop_exceeded(monkeypatch):
    def fake_invoke(_messages):
        return '{"action":"tool","tool_name":"list_dir","args":{"path":"."}}'

    class FakeExecutor:
        def __init__(self, repo_root):
            self.repo_root = repo_root

        def execute(self, request):
            return {"tool_name": request["tool_name"], "ok": True}

    monkeypatch.setattr("agent_runtime.dispatch.invoke_openai_compatible_chat", fake_invoke)
    monkeypatch.setattr("agent_runtime.dispatch.ToolExecutor", FakeExecutor)

    result = model_invoke(
        {
            "role": "backend_engineer",
            "system_prompt": "backend prompt",
            "objective": "Build feature",
            "state": {},
            "repo_context": {"repo_root": "."},
            "response_contract": {},
        }
    )

    assert result["status"] == "blocked"
    assert result["blockers"] == ["TOOL_LOOP_EXCEEDED"]
