"""Email Agent — sends transactional and marketing emails.

Responsibilities
----------------
* Send plain-text or HTML emails via the SendGrid Web API.
* Fallback to stdlib ``smtplib`` when SendGrid is not configured.
* Compose email content from a plain-English brief using GPT.
* Send pre-formatted operation reports to one or more recipients.

Configuration
-------------
Set one of these delivery methods in ``.env``:

**SendGrid (recommended)**::

    EMAIL_SENDGRID_API_KEY=SG.…
    EMAIL_FROM_ADDRESS=noreply@yourstartup.com

**SMTP**::

    EMAIL_SMTP_HOST=smtp.gmail.com
    EMAIL_SMTP_PORT=587
    EMAIL_SMTP_USER=you@gmail.com
    EMAIL_SMTP_PASSWORD=app-password
    EMAIL_FROM_ADDRESS=you@gmail.com

In both cases you can set a default recipient::

    EMAIL_DEFAULT_TO=founders@yourstartup.com
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_SENDGRID_SEND_URL = "https://api.sendgrid.com/v3/mail/send"

_COMPOSE_PROMPT = """\
You are a professional email copywriter for a startup. Given a brief, write a
short, clear email. Respond with a JSON object:
{
  "subject": "<email subject line>",
  "body": "<plain-text email body (2-5 sentences)>"
}
Output ONLY the JSON object — no prose, no markdown fences.
"""

_REPORT_COMPOSE_PROMPT = """\
You are preparing a weekly operations report for startup founders. Given the
metrics and events below, write a concise executive summary email body
(3-6 sentences, plain text, no markdown). Focus on what happened, key numbers,
and one clear next action.
"""


class EmailAgent:
    """Sends emails for the startup operations platform.

    Supports SendGrid (API key) or plain SMTP as the delivery backend.

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

    def send_email(
        self,
        to: str | list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> dict[str, Any]:
        """Send an email to one or more recipients.

        Delivery is attempted via SendGrid first, then SMTP if SendGrid is not
        configured.

        Args:
            to: Recipient address or list of addresses.
            subject: Email subject line.
            body: Plain-text body.
            html_body: Optional HTML body. When provided the email is sent as
                multipart/alternative so clients can render rich content.

        Returns:
            ``{"ok": True}`` on success, or ``{"ok": False, "error": "…"}``
            on failure.

        Raises:
            RuntimeError: When no delivery method is configured.
        """
        recipients = [to] if isinstance(to, str) else to

        if self._cfg.email_sendgrid_api_key:
            return self._send_via_sendgrid(recipients, subject, body, html_body)

        if self._cfg.email_smtp_host:
            return self._send_via_smtp(recipients, subject, body, html_body)

        raise RuntimeError(
            "No email delivery method configured. "
            "Set EMAIL_SENDGRID_API_KEY or EMAIL_SMTP_HOST in your .env file."
        )

    def compose_and_send(
        self,
        brief: str,
        to: str | list[str] | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        """Use GPT to write an email from *brief*, then send it.

        Args:
            brief: Plain-English description of what to communicate.
            to: Recipient(s).  Falls back to ``EMAIL_DEFAULT_TO`` when omitted.
            subject: Override the GPT-generated subject line.

        Returns:
            Result dict from :meth:`send_email`.

        Raises:
            RuntimeError: When *to* is omitted and ``EMAIL_DEFAULT_TO`` is not
                configured, or when no delivery method is available.
        """
        recipient = to or self._cfg.email_default_to
        if not recipient:
            raise RuntimeError(
                "No recipient specified and EMAIL_DEFAULT_TO is not set."
            )

        composed = self._compose(brief)
        final_subject = subject or composed.get("subject", brief[:60])
        body = composed.get("body", brief)

        self._log.info("Composed email — subject: %s", final_subject[:80])
        return self.send_email(recipient, final_subject, body)

    def send_report(
        self,
        subject: str,
        body: str,
        to: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """Send a pre-formatted report email.

        Convenience wrapper around :meth:`send_email` for structured reports
        produced by the :class:`~autogpt.agents.analytics_agent.AnalyticsAgent`.

        Args:
            subject: Report subject line.
            body: Report plain-text body.
            to: Recipient(s).  Falls back to ``EMAIL_DEFAULT_TO``.

        Returns:
            Result dict from :meth:`send_email`.
        """
        recipient = to or self._cfg.email_default_to
        if not recipient:
            raise RuntimeError(
                "No recipient specified and EMAIL_DEFAULT_TO is not set."
            )
        return self.send_email(recipient, subject, body)

    # ------------------------------------------------------------------ #
    # Delivery backends
    # ------------------------------------------------------------------ #

    def _send_via_sendgrid(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        html_body: str | None,
    ) -> dict[str, Any]:
        """POST to the SendGrid v3 mail/send endpoint."""
        payload: dict[str, Any] = {
            "personalizations": [{"to": [{"email": r} for r in recipients]}],
            "from": {"email": self._cfg.email_from_address},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        }
        if html_body:
            payload["content"].append({"type": "text/html", "value": html_body})

        resp = requests.post(
            _SENDGRID_SEND_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._cfg.email_sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        if resp.status_code in (200, 202):
            self._log.info("Email sent via SendGrid to %s.", recipients)
            return {"ok": True, "status_code": resp.status_code}
        self._log.warning(
            "SendGrid error %d: %s", resp.status_code, resp.text[:200]
        )
        return {"ok": False, "error": resp.text, "status_code": resp.status_code}

    def _send_via_smtp(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        html_body: str | None,
    ) -> dict[str, Any]:
        """Send through an SMTP relay using starttls."""
        msg: MIMEMultipart | MIMEText
        if html_body:
            msg = MIMEMultipart("alternative")
            msg.attach(MIMEText(body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
        else:
            msg = MIMEText(body, "plain")

        msg["Subject"] = subject
        msg["From"] = self._cfg.email_from_address
        msg["To"] = ", ".join(recipients)

        port = self._cfg.email_smtp_port
        context = ssl.create_default_context()
        try:
            with smtplib.SMTP(self._cfg.email_smtp_host, port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                if self._cfg.email_smtp_user:
                    server.login(
                        self._cfg.email_smtp_user, self._cfg.email_smtp_password
                    )
                server.sendmail(
                    self._cfg.email_from_address, recipients, msg.as_string()
                )
            self._log.info("Email sent via SMTP to %s.", recipients)
            return {"ok": True}
        except Exception as exc:
            self._log.warning("SMTP error: %s", exc)
            return {"ok": False, "error": str(exc)}

    # ------------------------------------------------------------------ #
    # GPT composition
    # ------------------------------------------------------------------ #

    def _compose(self, brief: str) -> dict[str, Any]:
        """Use GPT to draft a subject + body from a content brief."""
        import json

        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _COMPOSE_PROMPT},
                {"role": "user", "content": brief},
            ],
            temperature=0.6,
            max_tokens=300,
        )
        raw = (response.choices[0].message.content or "{}").strip()
        try:
            return json.loads(raw)
        except Exception:
            return {"subject": brief[:80], "body": raw}
