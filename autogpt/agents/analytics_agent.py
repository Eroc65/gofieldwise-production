"""Analytics Agent — collects startup metrics and delivers weekly reports.

Responsibilities
----------------
* Collect high-level metrics from configured services (Twitter, Meta Ads).
* Ask GPT to compile them into a concise executive-summary report.
* Deliver the report via email and/or Slack.

The agent is intentionally lightweight: it does not depend on the other
agent objects at runtime.  It calls the underlying APIs directly so it can
be invoked on its own by the scheduler without a full orchestrator context.

Configuration
-------------
The agent reuses existing service credentials already in ``.env``
(Twitter, Meta, Slack) and additionally::

    EMAIL_DEFAULT_TO=founders@yourstartup.com
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_REPORT_SYSTEM_PROMPT = """\
You are a data-savvy startup COO preparing a weekly operations report for
the founding team.  Given a JSON object of metrics and events, write a
concise plain-text executive summary (4-7 sentences).  Structure it as:
1. What happened this week (key numbers).
2. What's going well.
3. One specific recommended action for next week.
Output ONLY the summary — no subject line, no markdown, no preamble.
"""


class AnalyticsAgent:
    """Collects startup metrics and generates executive summary reports.

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

    def collect_metrics(self, period_days: int = 7) -> dict[str, Any]:
        """Collect available metrics from configured services.

        Each section is optional — if the relevant credentials are absent the
        section is simply omitted so the agent can still produce a useful
        partial report.

        Args:
            period_days: Look-back window in days (used where the API supports
                it).

        Returns:
            A dict with keys ``twitter``, ``meta_ads``, and ``period_days``.
        """
        metrics: dict[str, Any] = {"period_days": period_days}

        twitter = self._collect_twitter()
        if twitter:
            metrics["twitter"] = twitter

        meta = self._collect_meta()
        if meta:
            metrics["meta_ads"] = meta

        return metrics

    def generate_report(
        self, metrics: dict[str, Any] | None = None, period_days: int = 7
    ) -> str:
        """Generate a GPT-written executive summary from metrics.

        Args:
            metrics: Pre-collected metrics dict.  When ``None``, the agent
                calls :meth:`collect_metrics` automatically.
            period_days: Look-back window passed to :meth:`collect_metrics`
                when *metrics* is ``None``.

        Returns:
            Plain-text report body.
        """
        if metrics is None:
            metrics = self.collect_metrics(period_days)

        metrics_json = json.dumps(metrics, indent=2, default=str)
        self._log.info("Generating report from metrics: %s", metrics_json[:200])

        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _REPORT_SYSTEM_PROMPT},
                {"role": "user", "content": metrics_json},
            ],
            temperature=0.4,
            max_tokens=400,
        )
        return (response.choices[0].message.content or "No data available.").strip()

    def deliver_report(
        self,
        report: str,
        subject: str = "Weekly Startup Operations Report",
        email_to: str | list[str] | None = None,
        slack_channel: str | None = None,
    ) -> dict[str, Any]:
        """Send a report via email and/or Slack.

        At least one delivery channel must be configured.

        Args:
            report: Plain-text report body.
            subject: Email subject line.
            email_to: Email recipient(s).  Falls back to ``EMAIL_DEFAULT_TO``
                when omitted.
            slack_channel: Slack channel name (without ``#``).  Falls back to
                ``SLACK_DEFAULT_CHANNEL`` when omitted.

        Returns:
            Dict with keys ``email`` and ``slack``, each containing the
            delivery result or ``{"skipped": True}`` when that channel is not
            configured.
        """
        results: dict[str, Any] = {}

        # Email delivery
        email_recipient = email_to or self._cfg.email_default_to
        if email_recipient and (
            self._cfg.email_sendgrid_api_key or self._cfg.email_smtp_host
        ):
            from autogpt.agents.email_agent import EmailAgent

            try:
                results["email"] = EmailAgent(self._cfg).send_report(
                    subject=subject, body=report, to=email_recipient
                )
            except Exception as exc:
                self._log.warning("Email delivery failed: %s", exc)
                results["email"] = {"ok": False, "error": str(exc)}
        else:
            results["email"] = {"skipped": True}

        # Slack delivery
        channel = slack_channel or self._cfg.slack_default_channel
        if self._cfg.slack_webhook_url or self._cfg.slack_bot_token:
            from autogpt.agents.slack_agent import SlackAgent

            try:
                slack_text = f"*{subject}*\n\n{report}"
                results["slack"] = SlackAgent(self._cfg).post_message(
                    slack_text, channel=channel
                )
            except Exception as exc:
                self._log.warning("Slack delivery failed: %s", exc)
                results["slack"] = {"ok": False, "error": str(exc)}
        else:
            results["slack"] = {"skipped": True}

        return results

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point — generate and deliver a report.

        The *task* string is used to extract optional directives (e.g. which
        email to send to, or how many days to look back), then the report is
        generated and delivered.

        Args:
            task: Natural-language description, e.g. ``"Generate a weekly
                report and email it to ceo@example.com"``.

        Returns:
            Dict with ``report`` (the text) and ``delivery`` (channel results).
        """
        period_days = 7
        for token in task.split():
            if token.isdigit():
                period_days = int(token)
                break

        metrics = self.collect_metrics(period_days)
        report = self.generate_report(metrics=metrics)
        delivery = self.deliver_report(report)
        return {"report": report, "delivery": delivery, "metrics": metrics}

    # ------------------------------------------------------------------ #
    # Data collection helpers
    # ------------------------------------------------------------------ #

    def _collect_twitter(self) -> dict[str, Any] | None:
        """Return basic Twitter account stats, or None if unconfigured."""
        if not self._cfg.twitter_bearer_token:
            return None
        try:
            import tweepy  # type: ignore[import]

            client = tweepy.Client(
                bearer_token=self._cfg.twitter_bearer_token,
                wait_on_rate_limit=False,
            )
            me = client.get_me(user_fields=["public_metrics"])
            if not me.data:
                return None
            metrics = getattr(me.data, "public_metrics", {}) or {}
            return {
                "followers_count": metrics.get("followers_count"),
                "following_count": metrics.get("following_count"),
                "tweet_count": metrics.get("tweet_count"),
            }
        except Exception as exc:
            self._log.debug("Twitter metrics unavailable: %s", exc)
            return None

    def _collect_meta(self) -> dict[str, Any] | None:
        """Return Meta Ads account summary, or None if unconfigured."""
        if not (self._cfg.meta_access_token and self._cfg.meta_ad_account_id):
            return None
        try:
            account_id = self._cfg.meta_ad_account_id
            url = (
                f"https://graph.facebook.com/v19.0/act_{account_id}/insights"
            )
            resp = requests.get(
                url,
                params={
                    "access_token": self._cfg.meta_access_token,
                    "fields": "spend,impressions,clicks,ctr",
                    "date_preset": "last_7d",
                },
                timeout=15,
            )
            if not resp.ok:
                self._log.debug("Meta insights error %d", resp.status_code)
                return None
            data = resp.json().get("data", [])
            if not data:
                return {"spend": "0", "impressions": "0", "clicks": "0"}
            row = data[0]
            return {
                "spend": row.get("spend"),
                "impressions": row.get("impressions"),
                "clicks": row.get("clicks"),
                "ctr": row.get("ctr"),
            }
        except Exception as exc:
            self._log.debug("Meta metrics unavailable: %s", exc)
            return None
