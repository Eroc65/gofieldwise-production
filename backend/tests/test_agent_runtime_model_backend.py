from agent_runtime.model_backend import (
    _extract_first_json_object,
    _strip_code_fences,
    build_backend_config,
    invoke_openai_compatible_chat,
    parse_structured_result,
)


def test_strip_code_fences_json_block():
    text = "```json\n{\"status\":\"success\"}\n```"
    assert _strip_code_fences(text) == '{"status":"success"}'


def test_extract_json_with_prefix_and_suffix():
    text = "Result follows:\n{\"status\":\"success\",\"summary\":\"ok\"}\nThanks"
    extracted = _extract_first_json_object(text)
    assert extracted == '{"status":"success","summary":"ok"}'


def test_parse_structured_result_reads_object():
    text = '{"status":"success","summary":"ok"}'
    parsed = parse_structured_result(text)
    assert parsed["status"] == "success"
    assert parsed["summary"] == "ok"


def test_build_backend_config_from_env(monkeypatch):
    monkeypatch.setenv("AGENT_MODEL_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENT_MODEL_API_KEY", "lm-studio")
    monkeypatch.setenv("AGENT_MODEL_NAME", "gpt-4.1-mini")
    monkeypatch.setenv("AGENT_MODEL_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("AGENT_MODEL_TEMPERATURE", "0.2")
    monkeypatch.setenv("AGENT_MODEL_MAX_TOKENS", "2048")

    cfg = build_backend_config()
    assert cfg["base_url"] == "http://localhost:1234/v1"
    assert cfg["api_key"] == "lm-studio"
    assert cfg["model"] == "gpt-4.1-mini"
    assert cfg["timeout_seconds"] == 60.0
    assert cfg["temperature"] == 0.2
    assert cfg["max_tokens"] == 2048


def test_invoke_chat_calls_preflight(monkeypatch):
    monkeypatch.setenv("AGENT_MODEL_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENT_MODEL_API_KEY", "lm-studio")
    monkeypatch.setenv("AGENT_MODEL_NAME", "gpt-4.1-mini")

    called = {"preflight": 0}

    def fake_preflight(base_url, allow_recovery=True, force_recovery=False):
        called["preflight"] += 1
        assert base_url == "http://localhost:1234/v1"
        return {"ok": True}

    def fake_post_json(url, api_key, payload, timeout_seconds):
        assert url == "http://localhost:1234/v1/chat/completions"
        assert api_key == "lm-studio"
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr("agent_runtime.model_backend.ensure_model_backend_available", fake_preflight)
    monkeypatch.setattr("agent_runtime.model_backend._post_json", fake_post_json)

    output = invoke_openai_compatible_chat([{"role": "user", "content": "hi"}])
    assert output == "ok"
    assert called["preflight"] == 1


def test_invoke_chat_retries_once_on_connection_error(monkeypatch):
    monkeypatch.setenv("AGENT_MODEL_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENT_MODEL_API_KEY", "lm-studio")
    monkeypatch.setenv("AGENT_MODEL_NAME", "gpt-4.1-mini")

    called = {"preflight": 0, "post": 0}

    def fake_preflight(base_url, allow_recovery=True, force_recovery=False):
        called["preflight"] += 1
        return {"ok": True, "force": force_recovery}

    def fake_post_json(url, api_key, payload, timeout_seconds):
        called["post"] += 1
        if called["post"] == 1:
            raise RuntimeError("Model backend connection error: refused")
        return {"choices": [{"message": {"content": "recovered"}}]}

    monkeypatch.setattr("agent_runtime.model_backend.ensure_model_backend_available", fake_preflight)
    monkeypatch.setattr("agent_runtime.model_backend._post_json", fake_post_json)

    output = invoke_openai_compatible_chat([{"role": "user", "content": "hi"}])
    assert output == "recovered"
    assert called["preflight"] == 2
    assert called["post"] == 2
