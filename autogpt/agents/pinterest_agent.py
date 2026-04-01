"""Pinterest Agent — creates pins and manages boards via the Pinterest API v5.

Responsibilities
----------------
* List boards for the authenticated account.
* Create new boards.
* Create pins on an existing board (with GPT-composed description).
* List pins on a board.
* Retrieve basic analytics for a pin.

Configuration
-------------
``PINTEREST_ACCESS_TOKEN`` — OAuth 2 access token from the Pinterest developer app.

No third-party SDK is required; the agent uses plain ``requests``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_PINTEREST_BASE = "https://api.pinterest.com/v5"

_PIN_DESC_PROMPT = """\
You are a Pinterest content creator for a startup. Given a brief, write an
engaging pin description (2–4 sentences) that is keyword-rich and encourages
saves and clicks. Include a call-to-action.
Output ONLY the pin description — no preamble, no quotes.
"""

_PIN_TITLE_PROMPT = """\
You are a Pinterest content creator. Given a brief, write a short, compelling
pin title (≤100 characters, no trailing punctuation).
Output ONLY the title text.
"""


class PinterestAgent:
    """Creates pins and manages Pinterest boards via the Pinterest API v5.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key

    # ------------------------------------------------------------------ #
    # Public interface — Boards
    # ------------------------------------------------------------------ #

    def list_boards(self, page_size: int = 25) -> list[dict[str, Any]]:
        """Return the authenticated user's boards.

        Args:
            page_size: Number of boards to return per page (1–250).

        Returns:
            List of board dicts with ``id``, ``name``, ``description``,
            ``privacy``, ``pin_count``.
        """
        self._require_token()
        resp = self._get("/boards", params={"page_size": max(1, min(page_size, 250))})
        items = resp.get("items", [])
        return [
            {
                "id": b.get("id", ""),
                "name": b.get("name", ""),
                "description": b.get("description", ""),
                "privacy": b.get("privacy", "PUBLIC"),
                "pin_count": b.get("pin_count", 0),
            }
            for b in items
        ]

    def create_board(
        self,
        name: str,
        description: str = "",
        privacy: str = "PUBLIC",
    ) -> dict[str, Any]:
        """Create a new Pinterest board.

        Args:
            name: Board name.
            description: Optional board description.
            privacy: ``"PUBLIC"`` or ``"SECRET"``.

        Returns:
            Created board dict.
        """
        self._require_token()
        payload = {"name": name, "description": description, "privacy": privacy}
        resp = self._post("/boards", payload)
        self._log.info("Created Pinterest board: %s (id=%s)", name, resp.get("id"))
        return resp

    # ------------------------------------------------------------------ #
    # Public interface — Pins
    # ------------------------------------------------------------------ #

    def create_pin(
        self,
        board_id: str,
        title: str,
        description: str,
        image_url: str,
        link: str = "",
    ) -> dict[str, Any]:
        """Create a new pin on a board.

        Args:
            board_id: The target board ID.
            title: Pin title (≤100 characters).
            description: Pin description.
            image_url: Publicly accessible image URL.
            link: Optional destination URL.

        Returns:
            Created pin dict.
        """
        self._require_token()
        payload: dict[str, Any] = {
            "board_id": board_id,
            "title": title,
            "description": description,
            "media_source": {"source_type": "image_url", "url": image_url},
        }
        if link:
            payload["link"] = link
        resp = self._post("/pins", payload)
        self._log.info("Created Pinterest pin: %s (id=%s)", title[:60], resp.get("id"))
        return resp

    def compose_and_pin(
        self,
        brief: str,
        board_id: str,
        image_url: str,
        link: str = "",
    ) -> dict[str, Any]:
        """GPT-compose pin title/description from a brief and create the pin.

        Args:
            brief: Plain-English description of what the pin is about.
            board_id: Target board ID.
            image_url: Image URL for the pin.
            link: Optional destination URL.

        Returns:
            Dict with ``title``, ``description``, and ``pin`` (API response).
        """
        title = self._compose_title(brief)
        description = self._compose_description(brief)
        self._log.info("Composing pin — title: %s", title[:60])
        pin = self.create_pin(
            board_id=board_id,
            title=title,
            description=description,
            image_url=image_url,
            link=link,
        )
        return {"title": title, "description": description, "pin": pin}

    def list_pins(self, board_id: str, page_size: int = 25) -> list[dict[str, Any]]:
        """Return pins on a board.

        Args:
            board_id: The board to query.
            page_size: Number of pins per page (1–250).

        Returns:
            List of pin summary dicts.
        """
        self._require_token()
        resp = self._get(
            f"/boards/{board_id}/pins",
            params={"page_size": max(1, min(page_size, 250))},
        )
        items = resp.get("items", [])
        return [
            {
                "id": p.get("id", ""),
                "title": p.get("title", ""),
                "description": p.get("description", ""),
                "link": p.get("link", ""),
                "created_at": p.get("created_at", ""),
            }
            for p in items
        ]

    def get_pin_analytics(self, pin_id: str) -> dict[str, Any]:
        """Retrieve analytics for a specific pin.

        Args:
            pin_id: The pin ID.

        Returns:
            Dict with save, impression, and click metrics (when available).
        """
        self._require_token()
        try:
            resp = self._get(
                f"/pins/{pin_id}/analytics",
                params={"start_date": "2020-01-01", "end_date": "2026-12-31",
                        "metric_types": "IMPRESSION,SAVE,PIN_CLICK"},
            )
            return resp
        except Exception as exc:
            self._log.warning("Could not fetch pin analytics: %s", exc)
            return {"pin_id": pin_id, "error": str(exc)}

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point.

        Recognises keywords:
        * ``"list boards"`` / ``"show boards"`` → :meth:`list_boards`
        * ``"create board"`` → :meth:`create_board`
        * ``"list pins"`` / ``"show pins"`` → :meth:`list_pins` (needs board_id)
        * ``"pin analytics"`` → :meth:`get_pin_analytics`
        * ``"create pin"`` / ``"add pin"`` / ``"pin"`` (default) → :meth:`compose_and_pin`

        Args:
            task: Natural-language task description.

        Returns:
            Result dict.
        """
        import re
        t = task.lower()

        if any(kw in t for kw in ("list boards", "show boards", "my boards")):
            boards = self.list_boards()
            return {"boards": boards, "count": len(boards)}

        if "create board" in t:
            # Parse: "create board <name>"
            match = re.search(r"(?:create|new|add)\s+board\s+(.+)", task, re.IGNORECASE)
            name = match.group(1).strip() if match else task
            return self.create_board(name)

        if any(kw in t for kw in ("list pins", "show pins", "pins on")):
            board_id_match = re.search(r"\b([A-Za-z0-9_-]{10,})\b", task)
            board_id = board_id_match.group(1) if board_id_match else ""
            if board_id:
                pins = self.list_pins(board_id)
                return {"pins": pins, "count": len(pins)}
            return {"error": "Please provide a board ID."}

        if "pin analytics" in t or "pin stats" in t:
            pin_id_match = re.search(r"\b([0-9]+)\b", task)
            pin_id = pin_id_match.group(1) if pin_id_match else ""
            if pin_id:
                return self.get_pin_analytics(pin_id)
            return {"error": "Please provide a pin ID."}

        # Default: compose and create a pin.  Require board_id in task or config.
        board_id_match = re.search(r"\bboard[_\s]+id[:\s]+([A-Za-z0-9_-]+)", task, re.IGNORECASE)
        board_id = board_id_match.group(1) if board_id_match else self._cfg.pinterest_default_board_id
        if not board_id:
            return {"error": "Please provide a board ID (e.g. 'board_id: ABC123') or set PINTEREST_DEFAULT_BOARD_ID."}

        image_url_match = re.search(r"https?://\S+", task)
        image_url = image_url_match.group(0) if image_url_match else ""
        if not image_url:
            return {"error": "Please provide an image URL for the pin."}

        return self.compose_and_pin(brief=task, board_id=board_id, image_url=image_url)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_token(self) -> None:
        if not self._cfg.pinterest_access_token:
            raise ValueError("PINTEREST_ACCESS_TOKEN is not configured.")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._cfg.pinterest_access_token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = requests.get(
            f"{_PINTEREST_BASE}{path}",
            headers=self._headers(),
            params=params or {},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(
            f"{_PINTEREST_BASE}{path}",
            headers=self._headers(),
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def _compose_title(self, brief: str) -> str:
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _PIN_TITLE_PROMPT},
                {"role": "user", "content": brief},
            ],
            temperature=0.7,
            max_tokens=50,
        )
        return (response.choices[0].message.content or "").strip()[:100]

    def _compose_description(self, brief: str) -> str:
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _PIN_DESC_PROMPT},
                {"role": "user", "content": brief},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return (response.choices[0].message.content or "").strip()
