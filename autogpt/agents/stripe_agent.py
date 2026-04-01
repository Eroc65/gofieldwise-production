"""Stripe Agent — revenue, subscription, and customer financial operations.

Responsibilities
----------------
* Retrieve key revenue metrics: MRR, total revenue, active subscribers.
* List and filter customers and their subscriptions.
* Create payment links for one-off purchases.
* Fetch recent charges and invoices.
* Identify and list past-due / failed payment customers for follow-up.
* GPT-compose revenue summary reports.

Configuration
-------------
``STRIPE_SECRET_KEY`` — Secret API key from the Stripe dashboard
    (https://dashboard.stripe.com/apikeys).  Use a restricted key in
    production.  The key must have read access to Customers, Subscriptions,
    Charges, Invoices, and Payment Links.
``STRIPE_DEFAULT_CURRENCY`` — ISO-4217 currency code used when creating
    payment links (default: ``"usd"``).

No third-party SDK is required; the agent uses plain ``requests`` against
the Stripe REST API.
"""

from __future__ import annotations

import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_STRIPE_BASE = "https://api.stripe.com/v1"

_REVENUE_REPORT_PROMPT = """\
You are a CFO preparing a concise revenue summary for the founding team.
Given a JSON object of Stripe metrics, write a 3-5 sentence plain-text
summary covering: total active subscribers, estimated MRR, recent revenue,
any outstanding / past-due invoices, and one actionable recommendation.
Output ONLY the summary — no preamble, no markdown, no JSON.
"""


class StripeAgent:
    """Revenue and billing operations via the Stripe REST API.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key

    # ------------------------------------------------------------------ #
    # Public interface — Metrics
    # ------------------------------------------------------------------ #

    def get_mrr(self) -> dict[str, Any]:
        """Estimate Monthly Recurring Revenue from active subscriptions.

        Iterates over all ``active`` subscriptions and sums the plan amounts.

        Returns:
            Dict with ``mrr_cents``, ``mrr_formatted``, ``currency``, and
            ``active_subscription_count``.
        """
        self._require_key()
        subscriptions = self._list_all("/subscriptions", params={"status": "active", "limit": 100})
        currency = self._cfg.stripe_default_currency.lower()
        total_cents = 0
        for sub in subscriptions:
            items = (sub.get("items") or {}).get("data") or []
            for item in items:
                plan = item.get("plan") or {}
                amount = plan.get("amount") or 0
                interval = plan.get("interval", "month")
                quantity = item.get("quantity") or 1
                # Normalise everything to monthly
                if interval == "year":
                    amount = amount // 12
                elif interval == "week":
                    amount = amount * 4
                total_cents += amount * quantity
                if plan.get("currency"):
                    currency = plan["currency"]
        self._log.info("MRR calculated: %d cents (%s)", total_cents, currency)
        return {
            "mrr_cents": total_cents,
            "mrr_formatted": self._format_amount(total_cents, currency),
            "currency": currency,
            "active_subscription_count": len(subscriptions),
        }

    def get_recent_revenue(self, limit: int = 50) -> dict[str, Any]:
        """Retrieve the most recent successful charges.

        Args:
            limit: Number of charges to retrieve (1–100).

        Returns:
            Dict with ``total_cents``, ``total_formatted``, ``currency``,
            and ``charges`` list.
        """
        self._require_key()
        data = self._get("/charges", params={"limit": max(1, min(limit, 100))})
        charges = data.get("data", [])
        successful = [c for c in charges if c.get("paid") and not c.get("refunded")]
        total = sum(c.get("amount", 0) for c in successful)
        currency = successful[0].get("currency", self._cfg.stripe_default_currency) if successful else self._cfg.stripe_default_currency
        return {
            "total_cents": total,
            "total_formatted": self._format_amount(total, currency),
            "currency": currency,
            "charge_count": len(successful),
            "charges": [
                {
                    "id": c.get("id"),
                    "amount_formatted": self._format_amount(c.get("amount", 0), c.get("currency", currency)),
                    "customer": c.get("customer"),
                    "description": c.get("description") or "",
                    "created": c.get("created"),
                }
                for c in successful[:10]
            ],
        }

    def get_past_due_customers(self) -> list[dict[str, Any]]:
        """Return customers with past-due subscriptions or unpaid invoices.

        Returns:
            List of dicts with ``customer_id``, ``email``, ``subscription_id``,
            and ``status``.
        """
        self._require_key()
        past_due_subs = self._list_all("/subscriptions", params={"status": "past_due", "limit": 100})
        results = []
        for sub in past_due_subs:
            customer_id = sub.get("customer", "")
            email = self._get_customer_email(customer_id)
            results.append({
                "customer_id": customer_id,
                "email": email,
                "subscription_id": sub.get("id", ""),
                "status": sub.get("status", ""),
                "current_period_end": sub.get("current_period_end"),
            })
        return results

    # ------------------------------------------------------------------ #
    # Public interface — Customers & Subscriptions
    # ------------------------------------------------------------------ #

    def list_customers(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent Stripe customers.

        Args:
            limit: Number of customers to return (1–100).

        Returns:
            List of customer dicts.
        """
        self._require_key()
        data = self._get("/customers", params={"limit": max(1, min(limit, 100))})
        customers = data.get("data", [])
        return [
            {
                "id": c.get("id"),
                "email": c.get("email") or "",
                "name": c.get("name") or "",
                "created": c.get("created"),
                "currency": c.get("currency") or "",
            }
            for c in customers
        ]

    def list_subscriptions(
        self,
        status: str = "active",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List subscriptions filtered by status.

        Args:
            status: One of ``"active"``, ``"past_due"``, ``"canceled"``,
                ``"trialing"``, ``"all"``.
            limit: Number of results (1–100).

        Returns:
            List of subscription summary dicts.
        """
        self._require_key()
        params: dict[str, Any] = {"limit": max(1, min(limit, 100))}
        if status != "all":
            params["status"] = status
        data = self._get("/subscriptions", params=params)
        subs = data.get("data", [])
        return [
            {
                "id": s.get("id"),
                "customer": s.get("customer"),
                "status": s.get("status"),
                "current_period_end": s.get("current_period_end"),
                "cancel_at_period_end": s.get("cancel_at_period_end"),
            }
            for s in subs
        ]

    # ------------------------------------------------------------------ #
    # Public interface — Payment Links
    # ------------------------------------------------------------------ #

    def create_payment_link(
        self,
        price_id: str,
        quantity: int = 1,
    ) -> dict[str, Any]:
        """Create a Stripe Payment Link for a given price.

        Args:
            price_id: The Stripe Price ID to attach to the link
                (e.g. ``"price_1ABCDEFxyz"``).
            quantity: Number of units.

        Returns:
            Dict with ``url``, ``id``, and ``active``.
        """
        self._require_key()
        resp = requests.post(
            f"{_STRIPE_BASE}/payment_links",
            auth=(self._cfg.stripe_secret_key, ""),
            data={"line_items[0][price]": price_id, "line_items[0][quantity]": str(quantity)},
            timeout=20,
        )
        resp.raise_for_status()
        link = resp.json()
        self._log.info("Created payment link: %s", link.get("url"))
        return {"id": link.get("id"), "url": link.get("url"), "active": link.get("active", True)}

    # ------------------------------------------------------------------ #
    # Public interface — Reports
    # ------------------------------------------------------------------ #

    def generate_revenue_report(self) -> dict[str, Any]:
        """Generate a GPT-written revenue summary from current Stripe data.

        Returns:
            Dict with ``report`` (plain text) and ``metrics`` (raw numbers).
        """
        import json
        mrr = self.get_mrr()
        revenue = self.get_recent_revenue()
        past_due = self.get_past_due_customers()
        metrics = {
            "mrr": mrr,
            "recent_revenue": {k: v for k, v in revenue.items() if k != "charges"},
            "past_due_count": len(past_due),
        }
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _REVENUE_REPORT_PROMPT},
                {"role": "user", "content": json.dumps(metrics, default=str)},
            ],
            temperature=0.4,
            max_tokens=300,
        )
        report = (response.choices[0].message.content or "No data available.").strip()
        return {"report": report, "metrics": metrics}

    # ------------------------------------------------------------------ #
    # Orchestrator entry point
    # ------------------------------------------------------------------ #

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point.

        Recognises keywords:
        * ``"mrr"`` / ``"monthly recurring"`` → :meth:`get_mrr`
        * ``"revenue"`` / ``"charges"`` / ``"income"`` → :meth:`get_recent_revenue`
        * ``"past due"`` / ``"failed payment"`` / ``"overdue"`` → :meth:`get_past_due_customers`
        * ``"customers"`` / ``"subscribers"`` → :meth:`list_customers` or :meth:`list_subscriptions`
        * ``"payment link"`` / ``"create link"`` → :meth:`create_payment_link`
        * ``"report"`` / ``"summary"`` / (default) → :meth:`generate_revenue_report`

        Args:
            task: Natural-language task description.

        Returns:
            Result dict.
        """
        t = task.lower()

        if any(kw in t for kw in ("mrr", "monthly recurring revenue")):
            return self.get_mrr()

        if any(kw in t for kw in ("recent revenue", "charges", "income", "collected")):
            return self.get_recent_revenue()

        if any(kw in t for kw in ("past due", "failed payment", "overdue", "unpaid")):
            customers = self.get_past_due_customers()
            return {"past_due_customers": customers, "count": len(customers)}

        if any(kw in t for kw in ("list customers", "show customers")):
            customers = self.list_customers()
            return {"customers": customers, "count": len(customers)}

        if any(kw in t for kw in ("subscriptions", "subscribers")):
            status = "active"
            for s in ("past_due", "canceled", "trialing", "all"):
                if s in t:
                    status = s
                    break
            subs = self.list_subscriptions(status=status)
            return {"subscriptions": subs, "count": len(subs)}

        if any(kw in t for kw in ("payment link", "create link", "buy link")):
            # Parse price_id from task — expect a token starting with "price_"
            price_id = ""
            for token in task.split():
                if token.startswith("price_"):
                    price_id = token.strip(".,;")
                    break
            if not price_id:
                return {"error": "Please provide a Stripe price ID (e.g. price_1ABCDEFxyz)."}
            return self.create_payment_link(price_id)

        # Default: full revenue report
        return self.generate_revenue_report()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_key(self) -> None:
        if not self._cfg.stripe_secret_key:
            raise ValueError("STRIPE_SECRET_KEY is not configured.")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = requests.get(
            f"{_STRIPE_BASE}{path}",
            auth=(self._cfg.stripe_secret_key, ""),
            params=params or {},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def _list_all(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Auto-paginate a Stripe list endpoint and return all objects."""
        params = dict(params or {})
        results: list[dict[str, Any]] = []
        while True:
            data = self._get(path, params)
            page = data.get("data", [])
            results.extend(page)
            if not data.get("has_more") or not page:
                break
            params["starting_after"] = page[-1]["id"]
        return results

    def _get_customer_email(self, customer_id: str) -> str:
        """Fetch a customer's email address by ID."""
        if not customer_id:
            return ""
        try:
            data = self._get(f"/customers/{customer_id}")
            return data.get("email") or ""
        except Exception:
            return ""

    @staticmethod
    def _format_amount(amount_cents: int, currency: str) -> str:
        """Format a Stripe integer amount as a human-readable currency string."""
        major = amount_cents / 100.0
        symbol = {"usd": "$", "eur": "€", "gbp": "£"}.get(currency.lower(), currency.upper() + " ")
        return f"{symbol}{major:,.2f}"
