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
from autogpt.agents.email_agent import EmailAgent
from autogpt.agents.analytics_agent import AnalyticsAgent
from autogpt.agents.customer_support_agent import CustomerSupportAgent
from autogpt.agents.content_agent import ContentAgent
from autogpt.agents.telegram_agent import TelegramAgent
from autogpt.agents.youtube_agent import YouTubeAgent
from autogpt.agents.google_agent import GoogleAgent
from autogpt.agents.yelp_agent import YelpAgent
from autogpt.agents.pinterest_agent import PinterestAgent
from autogpt.agents.linkedin_agent import LinkedInAgent
from autogpt.agents.stripe_agent import StripeAgent
from autogpt.agents.hubspot_agent import HubSpotAgent
from autogpt.agents.shopify_agent import ShopifyAgent
from autogpt.utils.logger import get_logger

_ROUTER_SYSTEM_PROMPT = """\
You are the autonomous AI cofounder and operator of a startup.  You have full
authority to act on behalf of the company.  Your default mode is ACTION — you
execute tasks end-to-end without asking for confirmation unless the user's intent
is genuinely ambiguous.  Never say "Would you like me to…" or "I can help you
with that" — just do it.

You coordinate a team of specialized agents:

  - engineering       : builds & deploys web apps (GitHub + Render + Postgres)
  - browser           : automates browser tasks (scraping, form filling, etc.)
  - twitter           : manages the company Twitter/X account
  - meta_ads          : creates and manages Meta (Facebook/Instagram) ad campaigns
  - slack             : sends messages and notifications to a Slack workspace
  - email             : sends transactional and marketing emails
  - analytics         : collects metrics and generates weekly operations reports
  - customer_support  : answers customer questions using a knowledge base, logs tickets
  - content           : writes blog posts, landing pages, social content, email campaigns
  - telegram          : sends/broadcasts messages via a Telegram bot
  - youtube           : searches YouTube videos and retrieves channel/video statistics
  - google            : runs Google web searches and summarises results
  - yelp              : searches local businesses and reads Yelp reviews
  - pinterest         : creates pins and manages Pinterest boards
  - linkedin          : posts updates, searches people/companies, retrieves company page stats
  - stripe            : retrieves revenue metrics (MRR, charges), lists customers/subscriptions, creates payment links
  - hubspot           : manages CRM contacts and deals, logs notes, summarises sales pipeline
  - shopify           : lists products, checks inventory, retrieves orders and revenue, creates discount codes
  - none              : answer directly from your own knowledge (no agent needed)

When the user sends a message, reply with a JSON object:
{
  "agent": "<engineering|browser|twitter|meta_ads|slack|email|analytics|customer_support|content|telegram|youtube|google|yelp|pinterest|linkedin|stripe|hubspot|shopify|none>",
  "task": "<the exact sub-task to pass to the chosen agent, written as a direct imperative command>",
  "direct_reply": "<non-empty only when agent is 'none'; your direct answer>"
}

Routing rules:
- Choose the most capable agent for the job and give it a precise, complete task.
- When a goal requires multiple agents, pick the FIRST one now.  After each step
  you will be called again with the step result in context — continue routing to
  the next agent until the full goal is accomplished, then return agent=none.
- Use "none" only for pure knowledge questions that require no external action,
  OR to signal that all required steps have been completed.

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
        self._email: EmailAgent | None = None
        self._analytics: AnalyticsAgent | None = None
        self._customer_support: CustomerSupportAgent | None = None
        self._content: ContentAgent | None = None
        self._telegram: TelegramAgent | None = None
        self._youtube: YouTubeAgent | None = None
        self._google: GoogleAgent | None = None
        self._yelp: YelpAgent | None = None
        self._pinterest: PinterestAgent | None = None
        self._linkedin: LinkedInAgent | None = None
        self._stripe: StripeAgent | None = None
        self._hubspot: HubSpotAgent | None = None
        self._shopify: ShopifyAgent | None = None

        # Name of the last agent invoked — exposed for callers (e.g. web UI).
        self.last_agent: str = "none"

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

        The orchestrator loops internally, chaining agents one after another
        until GPT signals the goal is complete (``agent == "none"``) or
        ``Config.max_iterations`` is reached — without returning to the caller
        between steps.

        Args:
            message: Free-form message from the user / operator.

        Returns:
            A human-readable reply summarising what was done or answering
            the question directly.
        """
        self._log.info("User: %s", message)
        self._history.append({"role": "user", "content": message})

        # Accumulate (agent_name, task, result) tuples for each step executed.
        steps: list[tuple[str, str, dict[str, Any]]] = []
        # Extra messages injected during the chain (not persisted to _history).
        chain_context: list[dict[str, str]] = []

        reply = "I'm not sure how to help with that."

        for _iteration in range(self._cfg.max_iterations):
            routing = self._route(chain_context)
            agent_name = routing.get("agent", "none")
            task = routing.get("task", message)
            direct_reply = routing.get("direct_reply", "")

            self._log.info("Routing to agent: %s (step %d)", agent_name, _iteration + 1)

            if agent_name == "none" or not task:
                if steps:
                    # All steps done — produce a consolidated summary.
                    reply = self._summarise_chain(steps)
                else:
                    self.last_agent = "none"
                    reply = direct_reply or "I'm not sure how to help with that."
                break

            self.last_agent = agent_name
            result = self._dispatch(agent_name, task)
            steps.append((agent_name, task, result))

            if "error" in result:
                reply = self._summarise_chain(steps)
                break

            # Feed the step result back as context so the router can decide
            # whether another agent is needed or the goal is complete.
            step_content = (
                f"[Step {len(steps)}] Agent '{agent_name}' completed task: {task}\n"
                f"Result: {json.dumps(result, default=str)}"
            )
            chain_context.append({"role": "assistant", "content": step_content})
            chain_context.append({
                "role": "user",
                "content": (
                    "Step complete. What is the next step to finish the original goal? "
                    "Return agent=none when the goal is fully accomplished."
                ),
            })
        else:
            # Reached max_iterations without a "none" routing signal.
            reply = self._summarise_chain(steps) if steps else "Reached the maximum number of steps."

        # Optional Slack notification for the completed chain.
        if steps and steps[-1][0] != "slack":
            last_agent, last_task, _ = steps[-1]
            self._get_slack().notify_task_result(last_agent, last_task, reply)

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

    def _route(self, extra_messages: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """Ask GPT to classify and route the message.

        Args:
            extra_messages: Optional list of additional messages (chain context)
                to append after ``self._history`` for this call only.  These are
                NOT persisted to the conversation history.
        """
        messages = self._history + (extra_messages or [])
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=messages,
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
            if agent_name == "email":
                return self._get_email().compose_and_send(task)
            if agent_name == "analytics":
                return self._get_analytics().run(task)
            if agent_name == "customer_support":
                return self._get_customer_support().run(task)
            if agent_name == "content":
                return self._get_content().run(task)
            if agent_name == "telegram":
                return self._get_telegram().run(task)
            if agent_name == "youtube":
                return self._get_youtube().run(task)
            if agent_name == "google":
                return self._get_google().run(task)
            if agent_name == "yelp":
                return self._get_yelp().run(task)
            if agent_name == "pinterest":
                return self._get_pinterest().run(task)
            if agent_name == "linkedin":
                return self._get_linkedin().run(task)
            if agent_name == "stripe":
                return self._get_stripe().run(task)
            if agent_name == "hubspot":
                return self._get_hubspot().run(task)
            if agent_name == "shopify":
                return self._get_shopify().run(task)
        except Exception as exc:
            self._log.error("Agent '%s' raised an error: %s", agent_name, exc)
            return {"error": str(exc)}
        return {}

    def _summarise_chain(self, steps: list[tuple[str, str, dict[str, Any]]]) -> str:
        """Produce a human-readable summary for one or more completed agent steps.

        Args:
            steps: List of ``(agent_name, task, result)`` tuples in execution order.

        Returns:
            A concise narrative of what was accomplished, ending with a next action.
        """
        if not steps:
            return "No steps were executed."

        if "error" in steps[-1][2]:
            last_agent, _, last_result = steps[-1]
            return f"⚠️  The {last_agent} agent encountered an error: {last_result['error']}"

        steps_text = "\n\n".join(
            f"Step {i + 1} — {agent} → {task}\n"
            f"Result: {json.dumps(result, indent=2, default=str)}"
            for i, (agent, task, result) in enumerate(steps)
        )
        n = len(steps)
        summary_prompt = (
            f"The following {n} agent step(s) were executed to complete the goal:\n\n"
            f"{steps_text}\n\n"
            "Write a short, direct summary (2-5 sentences) of what was accomplished "
            "across all steps. End with one concrete next action the operator should "
            "take or that you will execute automatically to move the goal forward."
        )
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.4,
            max_tokens=300,
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

    def _get_email(self) -> EmailAgent:
        if self._email is None:
            self._email = EmailAgent(self._cfg)
        return self._email

    def _get_analytics(self) -> AnalyticsAgent:
        if self._analytics is None:
            self._analytics = AnalyticsAgent(self._cfg)
        return self._analytics

    def _get_customer_support(self) -> CustomerSupportAgent:
        if self._customer_support is None:
            self._customer_support = CustomerSupportAgent(self._cfg)
        return self._customer_support

    def _get_content(self) -> ContentAgent:
        if self._content is None:
            self._content = ContentAgent(self._cfg)
        return self._content

    def _get_telegram(self) -> TelegramAgent:
        if self._telegram is None:
            self._telegram = TelegramAgent(self._cfg)
        return self._telegram

    def _get_youtube(self) -> YouTubeAgent:
        if self._youtube is None:
            self._youtube = YouTubeAgent(self._cfg)
        return self._youtube

    def _get_google(self) -> GoogleAgent:
        if self._google is None:
            self._google = GoogleAgent(self._cfg)
        return self._google

    def _get_yelp(self) -> YelpAgent:
        if self._yelp is None:
            self._yelp = YelpAgent(self._cfg)
        return self._yelp

    def _get_pinterest(self) -> PinterestAgent:
        if self._pinterest is None:
            self._pinterest = PinterestAgent(self._cfg)
        return self._pinterest

    def _get_linkedin(self) -> LinkedInAgent:
        if self._linkedin is None:
            self._linkedin = LinkedInAgent(self._cfg)
        return self._linkedin

    def _get_stripe(self) -> StripeAgent:
        if self._stripe is None:
            self._stripe = StripeAgent(self._cfg)
        return self._stripe

    def _get_hubspot(self) -> HubSpotAgent:
        if self._hubspot is None:
            self._hubspot = HubSpotAgent(self._cfg)
        return self._hubspot

    def _get_shopify(self) -> ShopifyAgent:
        if self._shopify is None:
            self._shopify = ShopifyAgent(self._cfg)
        return self._shopify

