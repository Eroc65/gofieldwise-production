"""Customer Support Agent — handles customer inquiries with a Postgres knowledge base.

Responsibilities
----------------
* Maintain a knowledge-base (KB) of articles stored in Postgres.
* Answer customer questions by retrieving relevant KB articles and using GPT.
* Log every support interaction as a ticket in Postgres.
* Escalate unresolved tickets via Slack or email.

Configuration
-------------
No new env vars are required — the agent reuses ``DATABASE_URL`` (required for
the KB/ticket tables), ``SLACK_*``, and ``EMAIL_*`` credentials already in
``.env``.  When ``DATABASE_URL`` is absent the KB is stored in memory only
(articles added in one run are lost on restart).
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_ANSWER_SYSTEM_PROMPT = """\
You are the autonomous customer-success lead for a startup.  You have full
authority to resolve customer issues end-to-end.  Answer questions using
everything you know — the provided knowledge-base articles, general product
knowledge, and sound judgment.  Give a clear, confident answer (2–5 sentences).
If the knowledge base is silent on a topic, reason from first principles and
provide the best answer you can.  Only flag an issue for human escalation when
it involves account security, billing disputes, or a bug that requires an
engineer — and in that case, tell the customer you are escalating right now and
take the escalation action immediately.
Output ONLY the answer text — no preamble, no sign-off.
"""

_CREATE_KB_TABLE = """\
CREATE TABLE IF NOT EXISTS autogpt_kb_articles (
    id          SERIAL      PRIMARY KEY,
    title       TEXT        NOT NULL,
    content     TEXT        NOT NULL,
    tags        TEXT[]      NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

_CREATE_TICKETS_TABLE = """\
CREATE TABLE IF NOT EXISTS autogpt_support_tickets (
    id          SERIAL      PRIMARY KEY,
    question    TEXT        NOT NULL,
    answer      TEXT        NOT NULL,
    status      TEXT        NOT NULL DEFAULT 'open',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


class CustomerSupportAgent:
    """Answers customer questions using a Postgres-backed knowledge base.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key

        # In-memory KB fallback when DATABASE_URL is absent.
        self._mem_articles: list[dict[str, Any]] = []
        self._mem_tickets: list[dict[str, Any]] = []

        if config.database_url:
            self._init_tables()

    # ------------------------------------------------------------------ #
    # Knowledge base management
    # ------------------------------------------------------------------ #

    def add_article(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Add a new article to the knowledge base.

        Args:
            title: Short, descriptive title.
            content: Full article body.
            tags: Optional list of topic tags for filtering.

        Returns:
            Dict with ``id``, ``title``, and ``status``.
        """
        t = tags or []
        db = self._get_db()
        if db:
            try:
                rows = db.query(
                    "INSERT INTO autogpt_kb_articles (title, content, tags) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (title, content, t),
                )
                article_id = rows[0]["id"] if rows else None
                self._log.info("KB article added: %s (id=%s)", title[:60], article_id)
                return {"id": article_id, "title": title, "status": "created"}
            except Exception as exc:
                self._log.warning("Could not persist KB article: %s", exc)

        # In-memory fallback
        article_id = len(self._mem_articles) + 1
        self._mem_articles.append(
            {"id": article_id, "title": title, "content": content, "tags": t}
        )
        return {"id": article_id, "title": title, "status": "created (in-memory)"}

    def list_articles(self) -> list[dict[str, Any]]:
        """Return all KB articles (title, id, tags).

        Returns:
            List of article summary dicts.
        """
        db = self._get_db()
        if db:
            try:
                return db.query(
                    "SELECT id, title, tags, created_at FROM autogpt_kb_articles "
                    "ORDER BY created_at DESC"
                )
            except Exception as exc:
                self._log.warning("Could not list KB articles: %s", exc)
        return [
            {"id": a["id"], "title": a["title"], "tags": a["tags"]}
            for a in self._mem_articles
        ]

    def search_kb(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        """Find KB articles relevant to *query* using full-text search.

        Falls back to a simple case-insensitive substring search when the DB
        is unavailable.

        Args:
            query: Keywords or question to search for.
            max_results: Maximum number of articles to return.

        Returns:
            List of matching article dicts (id, title, content, tags).
        """
        db = self._get_db()
        if db:
            try:
                words = [w.strip() for w in query.split() if len(w.strip()) > 2]
                if not words:
                    return []
                # Use Postgres full-text search with a combined ts_query.
                ts_query = " | ".join(words)
                rows = db.query(
                    "SELECT id, title, content, tags FROM autogpt_kb_articles "
                    "WHERE to_tsvector('english', title || ' ' || content) "
                    "@@ to_tsquery('english', %s) "
                    "LIMIT %s",
                    (ts_query, max_results),
                )
                if rows:
                    return rows
                # Fallback: ILIKE on any keyword
                ilike = f"%{words[0]}%"
                return db.query(
                    "SELECT id, title, content, tags FROM autogpt_kb_articles "
                    "WHERE title ILIKE %s OR content ILIKE %s LIMIT %s",
                    (ilike, ilike, max_results),
                )
            except Exception as exc:
                self._log.warning("KB search failed: %s", exc)

        # In-memory search
        q = query.lower()
        results = [
            a
            for a in self._mem_articles
            if q in a["title"].lower() or q in a["content"].lower()
        ]
        return results[:max_results]

    # ------------------------------------------------------------------ #
    # Answering questions
    # ------------------------------------------------------------------ #

    def answer(self, question: str) -> dict[str, Any]:
        """Answer a customer question and log the ticket.

        The agent retrieves relevant KB articles, asks GPT to compose an
        answer, and stores the interaction as a support ticket.

        Args:
            question: The customer's question.

        Returns:
            Dict with ``answer``, ``ticket_id``, ``kb_articles_used``, and
            ``escalation_needed``.
        """
        articles = self.search_kb(question)
        context = self._build_context(articles)

        gpt_answer = self._gpt_answer(question, context)
        escalation_needed = self._needs_escalation(gpt_answer)

        ticket_id = self._log_ticket(question, gpt_answer, status="open")

        self._log.info(
            "Support ticket %s created. Escalation needed: %s",
            ticket_id,
            escalation_needed,
        )
        return {
            "answer": gpt_answer,
            "ticket_id": ticket_id,
            "kb_articles_used": len(articles),
            "escalation_needed": escalation_needed,
        }

    def escalate(
        self,
        ticket_id: int | str,
        slack_channel: str | None = None,
        email_to: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """Escalate a ticket to the team via Slack and/or email.

        Args:
            ticket_id: The ticket to escalate.
            slack_channel: Slack channel (without ``#``).  Defaults to
                ``SLACK_DEFAULT_CHANNEL``.
            email_to: Email recipient(s).  Defaults to ``EMAIL_DEFAULT_TO``.

        Returns:
            Dict with ``slack`` and ``email`` delivery results.
        """
        ticket = self._get_ticket(ticket_id)
        if not ticket:
            return {"error": f"Ticket {ticket_id} not found."}

        message = (
            f"🆘 *Support Escalation* — Ticket #{ticket_id}\n\n"
            f"*Question:* {ticket.get('question', '')}\n\n"
            f"*Initial Answer:* {ticket.get('answer', '')}"
        )

        results: dict[str, Any] = {}

        # Slack
        if self._cfg.slack_webhook_url or self._cfg.slack_bot_token:
            from autogpt.agents.slack_agent import SlackAgent

            try:
                results["slack"] = SlackAgent(self._cfg).post_message(
                    message, channel=slack_channel or self._cfg.slack_default_channel
                )
            except Exception as exc:
                results["slack"] = {"ok": False, "error": str(exc)}
        else:
            results["slack"] = {"skipped": True}

        # Email
        recipient = email_to or self._cfg.email_default_to
        if recipient and (
            self._cfg.email_sendgrid_api_key or self._cfg.email_smtp_host
        ):
            from autogpt.agents.email_agent import EmailAgent

            try:
                results["email"] = EmailAgent(self._cfg).send_email(
                    to=recipient,
                    subject=f"Support Escalation — Ticket #{ticket_id}",
                    body=message.replace("*", ""),
                )
            except Exception as exc:
                results["email"] = {"ok": False, "error": str(exc)}
        else:
            results["email"] = {"skipped": True}

        # Update ticket status
        self._update_ticket_status(ticket_id, "escalated")
        return results

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point — parse the task and route to the right method.

        Recognises keywords:
        * ``"add article"`` / ``"add kb"`` → :meth:`add_article`
        * ``"list articles"`` / ``"list kb"`` → :meth:`list_articles`
        * ``"escalate"`` → :meth:`escalate`
        * Everything else → :meth:`answer`

        Args:
            task: Natural-language task description.

        Returns:
            Result dict from the invoked method.
        """
        t = task.lower()
        if any(kw in t for kw in ("add article", "add kb", "knowledge base article")):
            lines = task.strip().splitlines()
            title = lines[0] if lines else task[:60]
            content = "\n".join(lines[1:]) if len(lines) > 1 else task
            return self.add_article(title, content)
        if any(kw in t for kw in ("list article", "list kb", "show articles")):
            articles = self.list_articles()
            return {"articles": articles, "count": len(articles)}
        if "escalate" in t:
            # Try to extract a ticket ID from the task text
            import re
            numbers = re.findall(r"\d+", task)
            ticket_id = int(numbers[0]) if numbers else 0
            return self.escalate(ticket_id)
        return self.answer(task)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _gpt_answer(self, question: str, context: str) -> str:
        """Use GPT to answer the question given the KB context."""
        user_content = f"Customer question: {question}\n\nKnowledge base:\n{context}"
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _ANSWER_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return (response.choices[0].message.content or "").strip()

    @staticmethod
    def _build_context(articles: list[dict[str, Any]]) -> str:
        """Format KB articles into a context string for the prompt."""
        if not articles:
            return "(No relevant articles found.)"
        parts = []
        for art in articles:
            parts.append(f"## {art.get('title', 'Untitled')}\n{art.get('content', '')}")
        return "\n\n".join(parts)

    @staticmethod
    def _needs_escalation(answer: str) -> bool:
        """Heuristic: escalate only for security, billing, or engineering issues."""
        lower = answer.lower()
        return any(
            phrase in lower
            for phrase in (
                "escalating",
                "escalate",
                "security",
                "billing dispute",
                "engineer",
                "bug",
            )
        )

    def _log_ticket(self, question: str, answer: str, status: str = "open") -> int:
        """Persist a support ticket and return its ID."""
        db = self._get_db()
        if db:
            try:
                db.execute_sql(
                    "INSERT INTO autogpt_support_tickets (question, answer, status) "
                    "VALUES (%s, %s, %s)",
                    (question, answer, status),
                )
                rows = db.query(
                    "SELECT id FROM autogpt_support_tickets "
                    "ORDER BY created_at DESC LIMIT 1"
                )
                return rows[0]["id"] if rows else 0
            except Exception as exc:
                self._log.warning("Could not log ticket: %s", exc)

        # In-memory fallback
        ticket_id = len(self._mem_tickets) + 1
        self._mem_tickets.append(
            {"id": ticket_id, "question": question, "answer": answer, "status": status}
        )
        return ticket_id

    def _get_ticket(self, ticket_id: int | str) -> dict[str, Any] | None:
        """Retrieve a ticket by ID."""
        db = self._get_db()
        if db:
            try:
                rows = db.query(
                    "SELECT id, question, answer, status FROM autogpt_support_tickets "
                    "WHERE id = %s",
                    (int(ticket_id),),
                )
                return rows[0] if rows else None
            except Exception as exc:
                self._log.warning("Could not retrieve ticket: %s", exc)

        for t in self._mem_tickets:
            if t["id"] == int(ticket_id):
                return t
        return None

    def _update_ticket_status(self, ticket_id: int | str, status: str) -> None:
        """Update the status field of a ticket."""
        db = self._get_db()
        if db:
            try:
                db.execute_sql(
                    "UPDATE autogpt_support_tickets SET status = %s WHERE id = %s",
                    (status, int(ticket_id)),
                )
                return
            except Exception as exc:
                self._log.warning("Could not update ticket status: %s", exc)

        for t in self._mem_tickets:
            if t["id"] == int(ticket_id):
                t["status"] = status
                return

    def _init_tables(self) -> None:
        """Create KB and ticket tables if they don't exist."""
        db = self._get_db()
        if db is None:
            return
        for ddl in (_CREATE_KB_TABLE, _CREATE_TICKETS_TABLE):
            try:
                db.execute_sql(ddl)
            except Exception as exc:
                self._log.warning("Could not create support table: %s", exc)

    def _get_db(self) -> "DatabaseTools | None":
        if not self._cfg.database_url:
            return None
        from autogpt.tools.database_tools import DatabaseTools

        return DatabaseTools(self._cfg.database_url, self._cfg.verbose)
