from agent_runtime.preflight import _health_url, ensure_model_backend_available


def test_health_url_defaults_with_path(monkeypatch):
    monkeypatch.setenv("AGENT_MODEL_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setenv("AGENT_MODEL_HEALTH_PATH", "/models")
    assert _health_url() == "http://localhost:1234/v1/models"


def test_ensure_backend_skips_recovery_when_healthy(monkeypatch):
    def fake_probe(base_url=None, health_path=None, timeout_seconds=None):
        return {"ok": True, "url": "http://localhost:1234/v1/models", "status": 200}

    monkeypatch.setattr("agent_runtime.preflight.probe_model_backend", fake_probe)

    result = ensure_model_backend_available("http://localhost:1234/v1")
    assert result["ok"] is True
    assert result["recovery_attempted"] is False


def test_ensure_backend_raises_when_unhealthy_and_autorecover_off(monkeypatch):
    monkeypatch.setenv("AGENT_MODEL_AUTORECOVER", "0")

    def fake_probe(base_url=None, health_path=None, timeout_seconds=None):
        return {
            "ok": False,
            "url": "http://localhost:1234/v1/models",
            "status": None,
            "error": "connection refused",
            "body_excerpt": "",
        }

    monkeypatch.setattr("agent_runtime.preflight.probe_model_backend", fake_probe)

    try:
        ensure_model_backend_available("http://localhost:1234/v1")
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Model backend unavailable" in str(exc)


def test_ensure_backend_attempts_recovery(monkeypatch):
    calls = {"probe": 0, "recover": 0}

    def fake_probe(base_url=None, health_path=None, timeout_seconds=None):
        calls["probe"] += 1
        if calls["probe"] == 1:
            return {
                "ok": False,
                "url": "http://localhost:1234/v1/models",
                "status": None,
                "error": "connection refused",
                "body_excerpt": "",
            }
        return {"ok": True, "url": "http://localhost:1234/v1/models", "status": 200, "body_excerpt": "ok"}

    def fake_recovery_script():
        calls["recover"] += 1
        return {"ok": True, "returncode": 0, "stdout": "started", "stderr": ""}

    monkeypatch.setattr("agent_runtime.preflight.probe_model_backend", fake_probe)
    monkeypatch.setattr("agent_runtime.preflight._run_recovery_script", fake_recovery_script)

    result = ensure_model_backend_available("http://localhost:1234/v1", allow_recovery=True)
    assert result["ok"] is True
    assert result["recovery_attempted"] is True
    assert calls["recover"] == 1
