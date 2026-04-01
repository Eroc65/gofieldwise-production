"""Browser Automation Agent — controls a real browser with Playwright.

Responsibilities
----------------
* Navigate to URLs, click elements, fill forms, take screenshots.
* Execute multi-step browser workflows described in plain English.
* Return structured results (page title, extracted text, screenshot path).

Playwright must be installed separately:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import openai

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_SYSTEM_PROMPT = """\
You are a browser automation agent.  You translate plain-English browser tasks
into a JSON list of steps.  Each step is an object with a "action" key and
additional parameters.

Supported actions:
  {"action": "navigate", "url": "<url>"}
  {"action": "click", "selector": "<css-or-text-selector>"}
  {"action": "fill", "selector": "<selector>", "value": "<text>"}
  {"action": "screenshot", "path": "<relative-file-path.png>"}
  {"action": "extract_text", "selector": "<selector>"}
  {"action": "wait", "seconds": <number>}

Respond with ONLY the JSON array of steps — no prose, no markdown fences.
"""


class BrowserAgent:
    """Automates browser interactions using Playwright.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
        headless: Run the browser in headless mode (default: ``True``).
        screenshots_dir: Directory where screenshots are saved.
    """

    def __init__(
        self,
        config: Config,
        headless: bool = True,
        screenshots_dir: str = "./screenshots",
    ) -> None:
        self._cfg = config
        self._headless = headless
        self._screenshots_dir = Path(screenshots_dir)
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def run(self, task: str) -> dict[str, Any]:
        """Execute a browser automation task described in plain English.

        Args:
            task: e.g. ``"Go to https://example.com and take a screenshot."``

        Returns:
            Dict with ``status``, ``steps_executed``, ``extracted_texts``,
            and ``screenshots`` keys.
        """
        self._log.info("BrowserAgent received task: %s", task)

        steps = self._plan(task)
        self._log.info("Planned %d browser steps.", len(steps))

        try:
            from playwright.sync_api import sync_playwright  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. "
                "Run `pip install playwright && playwright install chromium`."
            ) from exc

        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        extracted_texts: list[str] = []
        screenshots: list[str] = []
        steps_executed = 0

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self._headless)
            page = browser.new_page()

            for step in steps:
                action = step.get("action", "")
                try:
                    if action == "navigate":
                        page.goto(step["url"], wait_until="domcontentloaded", timeout=30_000)
                    elif action == "click":
                        page.click(step["selector"], timeout=10_000)
                    elif action == "fill":
                        page.fill(step["selector"], step.get("value", ""), timeout=10_000)
                    elif action == "screenshot":
                        path = self._screenshots_dir / step.get("path", "screenshot.png")
                        page.screenshot(path=str(path))
                        screenshots.append(str(path))
                    elif action == "extract_text":
                        text = page.inner_text(step["selector"])
                        extracted_texts.append(text)
                    elif action == "wait":
                        page.wait_for_timeout(int(step.get("seconds", 1)) * 1_000)
                    else:
                        self._log.warning("Unknown browser action: %s", action)
                        continue
                    steps_executed += 1
                except Exception as exc:
                    self._log.error("Step %s failed: %s", action, exc)

            browser.close()

        return {
            "status": "completed",
            "steps_executed": steps_executed,
            "extracted_texts": extracted_texts,
            "screenshots": screenshots,
        }

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _plan(self, task: str) -> list[dict[str, Any]]:
        """Ask GPT to translate the task into a list of browser steps."""
        import json

        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": task},
            ],
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "[]"
        try:
            result = json.loads(raw)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            self._log.warning("Could not parse GPT steps as JSON; returning empty plan.")
            return []
