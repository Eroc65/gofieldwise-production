import os

from agent_runtime.dispatch import dispatch, model_invoke


def test_model_invoke_mock_mode(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_DISPATCH_MODE", "mock")

    result = model_invoke(
        {
            "role": "planner",
            "objective": "Plan a slice",
            "state": {},
            "repo_context": {},
        }
    )

    assert result["status"] == "success"
    assert result["metadata"]["dispatch_mode"] == "mock"


def test_model_invoke_http_mode_requires_endpoint(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_DISPATCH_MODE", "http")
    monkeypatch.delenv("AGENT_RUNTIME_DISPATCH_ENDPOINT", raising=False)

    result = model_invoke(
        {
            "role": "planner",
            "objective": "Plan a slice",
            "state": {},
            "repo_context": {},
        }
    )

    assert result["status"] == "blocked"
    assert "MISSING_DISPATCH_ENDPOINT" in result["blockers"]


def test_dispatch_normalizes_unsupported_mode(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_DISPATCH_MODE", "unsupported_mode")

    result = dispatch(
        role="planner",
        objective="Plan something",
        state={},
        repo_context={},
    )

    assert result["status"] == "blocked"
    assert result["blockers"] == ["UNSUPPORTED_DISPATCH_MODE"]


def test_dispatch_mock_reaches_done_for_reviewer(monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_DISPATCH_MODE", "mock")

    result = dispatch(
        role="reviewer",
        objective="Review slice",
        state={},
        repo_context={},
    )

    assert result["status"] == "success"
    assert result["done"] is True
    assert result["metadata"]["dispatch_mode"] == "mock"


def teardown_module():
    os.environ.pop("AGENT_RUNTIME_DISPATCH_MODE", None)
    os.environ.pop("AGENT_RUNTIME_DISPATCH_ENDPOINT", None)
    os.environ.pop("AGENT_RUNTIME_DISPATCH_TIMEOUT_SECONDS", None)
