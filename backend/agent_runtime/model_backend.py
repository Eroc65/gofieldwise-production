from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from agent_runtime.preflight import ensure_model_backend_available


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def build_backend_config() -> dict[str, Any]:
    """
    Generic OpenAI-compatible config.

    Examples:
      AGENT_MODEL_BASE_URL=http://localhost:1234/v1
      AGENT_MODEL_API_KEY=sk-...
      AGENT_MODEL_NAME=gpt-4.1-mini
    """
    return {
        "base_url": _get_env("AGENT_MODEL_BASE_URL"),
        "api_key": _get_env("AGENT_MODEL_API_KEY"),
        "model": _get_env("AGENT_MODEL_NAME"),
        "timeout_seconds": float(os.getenv("AGENT_MODEL_TIMEOUT_SECONDS", "120")),
        "temperature": float(os.getenv("AGENT_MODEL_TEMPERATURE", "0.1")),
        "max_tokens": int(os.getenv("AGENT_MODEL_MAX_TOKENS", "4000")),
    }


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_first_json_object(text: str) -> str:
    """
    Try to recover a JSON object from model text.
    Handles:
    - raw JSON
    - fenced JSON
    - extra prose before/after JSON
    """
    cleaned = _strip_code_fences(text)

    # Fast path: already valid JSON object text
    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    # Find first balanced {...}
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response")

    depth = 0
    for i, ch in enumerate(cleaned[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return cleaned[start : i + 1]

    raise ValueError("Unbalanced JSON object in model response")


def _post_json(url: str, api_key: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        data=json.dumps(payload).encode("utf-8"),
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Model backend HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Model backend connection error: {exc}") from exc


def invoke_openai_compatible_chat(messages: list[dict[str, str]]) -> str:
    cfg = build_backend_config()
    url = cfg["base_url"].rstrip("/") + "/chat/completions"

    # Preflight + auto-recovery
    ensure_model_backend_available(cfg["base_url"], allow_recovery=True)

    payload = {
        "model": cfg["model"],
        "messages": messages,
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
    }

    try:
        data = _post_json(url, cfg["api_key"], payload, cfg["timeout_seconds"])
    except RuntimeError as exc:
        msg = str(exc).lower()
        if "connection error" in msg or "connection refused" in msg or "timed out" in msg:
            # One recovery retry
            ensure_model_backend_available(cfg["base_url"], allow_recovery=True, force_recovery=True)
            data = _post_json(url, cfg["api_key"], payload, cfg["timeout_seconds"])
        else:
            raise

    try:
        return data["choices"][0]["message"]["content"]
    except Exception as exc:
        raise RuntimeError(f"Unexpected backend response shape: {json.dumps(data)[:1000]}") from exc


def parse_structured_result(text: str) -> dict[str, Any]:
    obj_text = _extract_first_json_object(text)
    result = json.loads(obj_text)

    if not isinstance(result, dict):
        raise RuntimeError("Model response JSON must be an object")

    return result
