"""Slack Agent — sends messages and notifications to a Slack workspace.

Responsibilities
----------------
* Post to a channel via Slack Incoming Webhook (zero-dependency, uses requests).
* Post to a specific channel via the Slack Web API (bot token required).
* Compose a message from a plain-English brief using the OpenAI API then send it.
* Notify a default channel when other agents complete tasks.

Configuration
-------------
Set one (or both) of these in ``.env``:

* ``SLACK_WEBHOOK_URL``      — Incoming Webhook URL from Slack App settings.
* ``SLACK_BOT_TOKEN``        — ``xoxb-…`` bot token for the Web API.
* ``SLACK_DEFAULT_CHANNEL``  — Channel name (without ``#``), default ``general``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_COMPOSE_PROMPT = """\
You are a concise workplace communicator. Given a brief, write a short, clear
Slack message (1-3 sentences). Include emoji where appropriate.
Output ONLY the message text — no explanation.
"""

_SLACK_API_BASE = "https://slack.com/api"


class SlackAgent:
    """Sends messages and notifications to a Slack workspace.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def send_notification(self, text: str) -> dict[str, Any]:
        """Post *text* via the configured Incoming Webhook URL.

        This is the simplest integration and requires no Slack bot token —
        only ``SLACK_WEBHOOK_URL`` in ``.env``.

        Args:
            text: The message body.

        Returns:
            ``{"ok": True}`` on success, or ``{"ok": False, "error": "…"}``
            on failure.

        Raises:
            RuntimeError: When ``SLACK_WEBHOOK_URL`` is not configured.
        """
        if not self._cfg.slack_webhook_url:
            raise RuntimeError(
                "SLACK_WEBHOOK_URL is not set. "
                "Add it to your .env file to enable Slack notifications."
            )
        resp = requests.post(
            self._cfg.slack_webhook_url,
            json={"text": text},
            timeout=15,
        )
        if resp.ok and resp.text == "ok":
            self._log.info("Slack notification sent via webhook.")
            return {"ok": True}
        self._log.warning("Slack webhook returned: %s %s", resp.status_code, resp.text)
        return {"ok": False, "error": resp.text}

    def post_message(self, text: str, channel: str | None = None) -> dict[str, Any]:
        """Post *text* to a Slack channel via the Web API.

        Requires ``SLACK_BOT_TOKEN``.  Falls back to the webhook when the
        bot token is absent and ``channel`` is not supplied.

        Args:
            text: The message body.
            channel: Target channel (without ``#``).  Defaults to
                ``SLACK_DEFAULT_CHANNEL``.

        Returns:
            Slack Web API response dict.

        Raises:
            RuntimeError: When neither a bot token nor a webhook URL is set.
        """
        target = channel or self._cfg.slack_default_channel

        if self._cfg.slack_bot_token:
            return self._post_via_api(text, target)

        # Fall back to webhook (channel param ignored)
        if self._cfg.slack_webhook_url:
            self._log.debug("No bot token; falling back to webhook for channel %s.", target)
            return self.send_notification(text)

        raise RuntimeError(
            "Neither SLACK_BOT_TOKEN nor SLACK_WEBHOOK_URL is configured."
        )

    def compose_and_send(self, brief: str, channel: str | None = None) -> dict[str, Any]:
        """Use GPT to write a Slack message from *brief*, then send it.

        Args:
            brief: Plain-English description of what to communicate.
            channel: Target channel (without ``#``).  Defaults to
                ``SLACK_DEFAULT_CHANNEL``.

        Returns:
            Slack API response dict.
        """
        text = self._compose(brief)
        self._log.info("Composed Slack message: %s", text[:80])
        return self.post_message(text, channel=channel)

    def notify_task_result(
        self, agent_name: str, task: str, result_summary: str
    ) -> dict[str, Any]:
        """Send a standardised task-completion notification.

        Called automatically by the :class:`~autogpt.orchestrator.Orchestrator`
        after every agent invocation when a webhook or bot token is configured.

        Args:
            agent_name: Name of the agent that ran (e.g. ``"engineering"``).
            task: The task description.
            result_summary: Human-readable result summary.

        Returns:
            Slack API response dict, or ``{"ok": False}`` if Slack is unconfigured.
        """
        if not self._cfg.slack_webhook_url and not self._cfg.slack_bot_token:
            return {"ok": False, "reason": "slack not configured"}

        text = (
            f"✅ *{agent_name.capitalize()} agent* completed a task\n"
            f"> {task[:120]}\n\n"
            f"{result_summary}"
        )
        try:
            return self.post_message(text)
        except Exception as exc:
            self._log.warning("Could not send Slack task notification: %s", exc)
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _post_via_api(self, text: str, channel: str) -> dict[str, Any]:
        """POST to Slack ``chat.postMessage`` using the bot token."""
        resp = requests.post(
            f"{_SLACK_API_BASE}/chat.postMessage",
            headers={
                "Authorization": f"Bearer {self._cfg.slack_bot_token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            data=json.dumps({"channel": channel, "text": text}),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("ok"):
            self._log.info("Slack message posted to #%s.", channel)
        else:
            self._log.warning("Slack API error: %s", data.get("error"))
        return data

    def _compose(self, brief: str) -> str:
        """Use GPT to write a Slack message from a content brief."""
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _COMPOSE_PROMPT},
                {"role": "user", "content": brief},
            ],
            temperature=0.6,
            max_tokens=150,
        )
        return (response.choices[0].message.content or "").strip()
