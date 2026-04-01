"""Telegram Agent — sends and broadcasts messages via the Telegram Bot API.

Responsibilities
----------------
* Send messages to a specific chat or user by chat ID.
* Broadcast a message to a configured default channel/group.
* Retrieve the latest updates (incoming messages) for the bot.
* GPT-compose message text from a plain-English brief.

Configuration
-------------
``TELEGRAM_BOT_TOKEN`` — Bot API token from @BotFather.
``TELEGRAM_DEFAULT_CHAT_ID`` — Default chat / channel ID for broadcasts (optional).

No third-party SDK is required; the agent uses plain ``requests``.
"""

from __future__ import annotations

import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_COMPOSE_PROMPT = """\
You are a professional community manager writing a Telegram message for a startup.
Given a brief, write a clear and friendly message suitable for a Telegram channel.
Keep it concise (1–3 short paragraphs). Include relevant emojis where appropriate.
Output ONLY the message text — no preamble, no quotes.
"""

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


class TelegramAgent:
    """Manages a Telegram bot — sends messages and reads updates.

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

    def send_message(
        self,
        text: str,
        chat_id: str | int | None = None,
        parse_mode: str = "HTML",
    ) -> dict[str, Any]:
        """Send a text message to a chat.

        Args:
            text: The message body.
            chat_id: Telegram chat / channel ID.  Falls back to
                ``TELEGRAM_DEFAULT_CHAT_ID`` when omitted.
            parse_mode: Telegram parse mode — ``"HTML"`` or ``"Markdown"``.

        Returns:
            Telegram API response dict.

        Raises:
            ValueError: If no chat ID is available.
            RuntimeError: If the API call fails.
        """
        effective_chat_id = chat_id or self._cfg.telegram_default_chat_id
        if not effective_chat_id:
            raise ValueError(
                "No chat_id provided and TELEGRAM_DEFAULT_CHAT_ID is not set."
            )
        self._log.info("Sending Telegram message to %s: %s", effective_chat_id, text[:60])
        resp = self._call("sendMessage", {
            "chat_id": effective_chat_id,
            "text": text,
            "parse_mode": parse_mode,
        })
        self._log.info("Telegram message sent, message_id=%s", resp.get("result", {}).get("message_id"))
        return resp

    def broadcast(self, text: str) -> dict[str, Any]:
        """Broadcast a message to the configured default channel/group.

        Args:
            text: The message text.

        Returns:
            Telegram API response dict.
        """
        return self.send_message(text)

    def compose_and_send(
        self,
        brief: str,
        chat_id: str | int | None = None,
    ) -> dict[str, Any]:
        """GPT-compose a message from a brief and send it.

        Args:
            brief: Plain-English description of what to communicate.
            chat_id: Target chat/channel ID.  Falls back to the default.

        Returns:
            Dict with ``message`` (composed text) and the Telegram API response.
        """
        message = self._compose(brief)
        self._log.info("Composed Telegram message: %s", message[:80])
        result = self.send_message(message, chat_id=chat_id)
        return {"message": message, "api_response": result}

    def get_updates(self, limit: int = 10, offset: int | None = None) -> list[dict[str, Any]]:
        """Fetch the latest incoming updates (messages) for the bot.

        Args:
            limit: Maximum number of updates to retrieve (1–100).
            offset: Update offset to acknowledge older updates.

        Returns:
            List of Telegram update dicts.
        """
        params: dict[str, Any] = {"limit": max(1, min(limit, 100))}
        if offset is not None:
            params["offset"] = offset
        resp = self._call("getUpdates", params)
        return resp.get("result", [])

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point — route the task to the right method.

        Recognises keywords:
        * ``"get updates"`` / ``"check messages"`` → :meth:`get_updates`
        * ``"broadcast"`` / ``"announce"`` → :meth:`compose_and_send` (default chat)
        * Everything else → :meth:`compose_and_send`

        Args:
            task: Natural-language task description.

        Returns:
            Result dict.
        """
        t = task.lower()
        if any(kw in t for kw in ("get updates", "check messages", "read messages", "inbox")):
            updates = self.get_updates()
            return {"updates": updates, "count": len(updates)}
        return self.compose_and_send(task)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _call(self, method: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a Telegram Bot API call.

        Args:
            method: Bot API method name (e.g. ``"sendMessage"``).
            data: JSON payload.

        Returns:
            Parsed response dict.

        Raises:
            ValueError: If ``TELEGRAM_BOT_TOKEN`` is not set.
            RuntimeError: If the request fails.
        """
        if not self._cfg.telegram_bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")
        url = _TELEGRAM_API.format(token=self._cfg.telegram_bot_token, method=method)
        resp = requests.post(url, json=data, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def _compose(self, brief: str) -> str:
        """Use GPT to compose a Telegram message from a brief."""
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _COMPOSE_PROMPT},
                {"role": "user", "content": brief},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return (response.choices[0].message.content or "").strip()
