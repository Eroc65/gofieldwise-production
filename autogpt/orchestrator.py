"""Orchestrator — the cofounder chat interface.

This is the central coordination layer of the platform.  It:

* Maintains a running conversation history so context is never lost.
* Uses the OpenAI API to decide which agent(s) to invoke for each message.
* Calls the appropriate agent and returns a human-readable summary.
* Persists conversation history to Postgres (when ``DATABASE_URL`` is set)
  so sessions survive restarts and can be shared across processes.
* Exposes a ``chat(message)`` method for use from any interface (CLI, web, etc.).

Example usage::

    from autogpt.config import Config
    from autogpt.orchestrator import Orchestrator

    cfg = Config()
    orc = Orchestrator(cfg, session_id="my-session")
    print(orc.chat("Build me a Flask app and deploy it to Render."))
    print(orc.chat("Tweet about our launch."))
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import openai

from autogpt.config import Config
from autogpt.agents.engineering_agent import EngineeringAgent
from autogpt.agents.browser_agent import BrowserAgent
from autogpt.agents.twitter_agent import TwitterAgent
from autogpt.agents.meta_ads_agent import MetaAdsAgent
from autogpt.agents.slack_agent import SlackAgent
from autogpt.utils.logger import get_logger

_ROUTER_SYSTEM_PROMPT = """\
You are the AI cofounder and operator of a startup.  You coordinate a team of
specialized agents:

  - engineering  : builds & deploys web apps (GitHub + Render + Postgres)
  - browser      : automates browser tasks (scraping, form filling, etc.)
  - twitter      : manages the company Twitter/X account
  - meta_ads     : creates and manages Meta (Facebook/Instagram) ad campaigns
  - slack        : sends messages and notifications to a Slack workspace
  - none         : answer directly from your own knowledge (no agent needed)

When the user sends a message, reply with a JSON object:
{
  "agent": "<engineering|browser|twitter|meta_ads|slack|none>",
  "task": "<the exact sub-task to pass to the chosen agent, rephrased if needed>",
  "direct_reply": "<non-empty only when agent is 'none'; your direct answer>"
}

Output ONLY the JSON object — no prose, no markdown fences.
"""

_CREATE_SESSIONS_TABLE = """\
CREATE TABLE IF NOT EXISTS autogpt_sessions (
    session_id  TEXT        PRIMARY KEY,
    history     JSONB       NOT NULL DEFAULT '[]',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


class Orchestrator:
    """Routes user messages to the right agent and maintains conversation state.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
        session_id: Optional identifier for this conversation session.  When
            *database_url* is configured, history is loaded from and persisted
            to Postgres using this key.  A random UUID is generated when omitted.
    """

    def __init__(self, config: Config, session_id: str | None = None) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key

        self.session_id: str = session_id or str(uuid.uuid4())

        # Lazy-initialise agents to avoid import errors when optional
        # dependencies (playwright, tweepy, etc.) are not installed.
        self._engineering: EngineeringAgent | None = None
        self._browser: BrowserAgent | None = None
        self._twitter: TwitterAgent | None = None
        self._meta: MetaAdsAgent | None = None
        self._slack: SlackAgent | None = None

        # Conversation history sent with every OpenAI call for context.
        # Loaded from Postgres if a DATABASE_URL is configured.
        self._history: list[dict[str, str]] = [
            {"role": "system", "content": _ROUTER_SYSTEM_PROMPT}
        ]
        if config.database_url:
            self._init_sessions_table()
            self._load_history()

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def chat(self, message: str) -> str:
        """Process a user message and return a response string.

        Args:
            message: Free-form message from the user / operator.

        Returns:
            A human-readable reply summarising what was done or answering
            the question directly.
        """
        self._log.info("User: %s", message)
        self._history.append({"role": "user", "content": message})

        # Ask GPT to route the request
        routing = self._route(message)
        agent_name = routing.get("agent", "none")
        task = routing.get("task", message)
        direct_reply = routing.get("direct_reply", "")

        self._log.info("Routing to agent: %s", agent_name)

        if agent_name == "none" or not task:
            reply = direct_reply or "I'm not sure how to help with that."
        else:
            result = self._dispatch(agent_name, task)
            reply = self._summarise(agent_name, task, result)
            # Optional Slack notification when a real agent completes a task.
            if agent_name != "slack":
                self._get_slack().notify_task_result(agent_name, task, reply)

        self._history.append({"role": "assistant", "content": reply})
        self._log.info("Assistant: %s", reply[:120])
        self._save_history()
        return reply

    def reset(self) -> None:
        """Clear conversation history (keeps the system prompt)."""
        self._history = [self._history[0]]
        self._save_history()

    # ------------------------------------------------------------------ #
    # Internal routing helpers
    # ------------------------------------------------------------------ #

    def _route(self, message: str) -> dict[str, Any]:
        """Ask GPT to classify and route the message."""
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=self._history,
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            self._log.warning("Could not parse routing JSON; falling back to direct reply.")
            return {"agent": "none", "task": "", "direct_reply": raw}

    def _dispatch(self, agent_name: str, task: str) -> dict[str, Any]:
        """Invoke the named agent with *task* and return its result dict."""
        try:
            if agent_name == "engineering":
                return self._get_engineering().run(task)
            if agent_name == "browser":
                return self._get_browser().run(task)
            if agent_name == "twitter":
                # Decide between compose_and_post and search
                if any(kw in task.lower() for kw in ("search", "find", "look")):
                    return {"tweets": self._get_twitter().search(task)}
                if any(kw in task.lower() for kw in ("timeline", "feed")):
                    return {"tweets": self._get_twitter().get_timeline()}
                if any(kw in task.lower() for kw in ("like",)):
                    return self._get_twitter().like(task.split()[-1])
                if any(kw in task.lower() for kw in ("retweet",)):
                    return self._get_twitter().retweet(task.split()[-1])
                return self._get_twitter().compose_and_post(task)
            if agent_name == "meta_ads":
                copy = self._get_meta().generate_ad_copy(task)
                return {"ad_copy": copy, "status": "copy_generated"}
            if agent_name == "slack":
                return self._get_slack().compose_and_send(task)
        except Exception as exc:
            self._log.error("Agent '%s' raised an error: %s", agent_name, exc)
            return {"error": str(exc)}
        return {}

    def _summarise(self, agent_name: str, task: str, result: dict[str, Any]) -> str:
        """Convert an agent result dict into a human-readable string using GPT."""
        if "error" in result:
            return f"⚠️  The {agent_name} agent encountered an error: {result['error']}"

        summary_prompt = (
            f"The user asked: {task}\n\n"
            f"The {agent_name} agent returned this result:\n"
            f"{json.dumps(result, indent=2, default=str)}\n\n"
            "Write a short, friendly summary (2-4 sentences) of what was accomplished."
        )
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.4,
            max_tokens=200,
        )
        return (response.choices[0].message.content or "Done.").strip()

    # ------------------------------------------------------------------ #
    # Session persistence helpers
    # ------------------------------------------------------------------ #

    def _get_db(self) -> "DatabaseTools | None":
        """Return a *DatabaseTools* instance, or *None* when DB is not configured."""
        if not self._cfg.database_url:
            return None
        from autogpt.tools.database_tools import DatabaseTools
        return DatabaseTools(self._cfg.database_url, self._cfg.verbose)

    def _init_sessions_table(self) -> None:
        """Create the sessions table if it does not yet exist."""
        db = self._get_db()
        if db is None:
            return
        try:
            db.execute_sql(_CREATE_SESSIONS_TABLE)
            self._log.debug("Sessions table ready.")
        except Exception as exc:
            self._log.warning("Could not initialise sessions table: %s", exc)

    def _load_history(self) -> None:
        """Load conversation history from Postgres (no-op if DB not configured)."""
        db = self._get_db()
        if db is None:
            return
        try:
            rows = db.query(
                "SELECT history FROM autogpt_sessions WHERE session_id = %s",
                (self.session_id,),
            )
            if rows:
                stored: list[dict[str, str]] = rows[0]["history"]
                if stored:
                    # Preserve the in-memory system prompt; restore user/assistant turns.
                    self._history = [self._history[0]] + [
                        m for m in stored if m.get("role") != "system"
                    ]
                    self._log.info(
                        "Loaded %d history messages for session %s.",
                        len(self._history) - 1,
                        self.session_id,
                    )
        except Exception as exc:
            self._log.warning("Could not load session history: %s", exc)

    def _save_history(self) -> None:
        """Persist current conversation history to Postgres (no-op if DB not configured)."""
        db = self._get_db()
        if db is None:
            return
        try:
            # Upsert: insert or update on conflict.
            db.execute_sql(
                """
                INSERT INTO autogpt_sessions (session_id, history, updated_at)
                VALUES (%s, %s::jsonb, NOW())
                ON CONFLICT (session_id)
                DO UPDATE SET history = EXCLUDED.history, updated_at = NOW()
                """,
                (self.session_id, json.dumps(self._history)),
            )
            self._log.debug("Session %s saved (%d messages).", self.session_id, len(self._history))
        except Exception as exc:
            self._log.warning("Could not save session history: %s", exc)

    # ------------------------------------------------------------------ #
    # Lazy agent accessors
    # ------------------------------------------------------------------ #

    def _get_engineering(self) -> EngineeringAgent:
        if self._engineering is None:
            self._engineering = EngineeringAgent(self._cfg)
        return self._engineering

    def _get_browser(self) -> BrowserAgent:
        if self._browser is None:
            self._browser = BrowserAgent(self._cfg)
        return self._browser

    def _get_twitter(self) -> TwitterAgent:
        if self._twitter is None:
            self._twitter = TwitterAgent(self._cfg)
        return self._twitter

    def _get_meta(self) -> MetaAdsAgent:
        if self._meta is None:
            self._meta = MetaAdsAgent(self._cfg)
        return self._meta

    def _get_slack(self) -> SlackAgent:
        if self._slack is None:
            self._slack = SlackAgent(self._cfg)
        return self._slack

