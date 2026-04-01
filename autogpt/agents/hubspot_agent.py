"""HubSpot Agent — CRM contacts, deals, and pipeline management.

Responsibilities
----------------
* Create and look up contacts in HubSpot CRM.
* List and update deals in the sales pipeline.
* Log notes/activities against contacts or deals.
* Retrieve pipeline-stage summaries and deal velocity metrics.
* GPT-compose CRM status reports from live data.

Configuration
-------------
``HUBSPOT_API_KEY`` — Private-app access token from HubSpot
    (Settings → Integrations → Private Apps).  The token must have
    CRM *read* + *write* scopes for contacts, deals, and notes.
``HUBSPOT_DEFAULT_PIPELINE_ID`` — ID of the default sales pipeline
    used when listing deal stages (optional; defaults to the first
    pipeline returned by the API).

No third-party SDK is required; the agent uses the HubSpot REST API v3
via plain ``requests``.
"""

from __future__ import annotations

import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_HS_BASE = "https://api.hubapi.com"

_CRM_REPORT_PROMPT = """\
You are a sales operations manager preparing a concise CRM status report.
Given a JSON object with HubSpot metrics, write a 3-5 sentence plain-text
summary covering: total open deals, their combined value, the stage
distribution, recent new contacts, and one actionable recommendation.
Output ONLY the summary — no preamble, no markdown, no JSON.
"""


class HubSpotAgent:
    """CRM contacts, deals, and pipeline operations via the HubSpot REST API.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key

    # ------------------------------------------------------------------ #
    # Contacts
    # ------------------------------------------------------------------ #

    def create_contact(
        self,
        email: str,
        firstname: str = "",
        lastname: str = "",
        phone: str = "",
        company: str = "",
    ) -> dict[str, Any]:
        """Create a new contact in HubSpot.

        Args:
            email: Contact's email address (required).
            firstname: First name.
            lastname: Last name.
            phone: Phone number.
            company: Company / organisation name.

        Returns:
            Dict with ``id`` and ``properties`` of the created contact.
        """
        self._require_key()
        properties: dict[str, str] = {"email": email}
        if firstname:
            properties["firstname"] = firstname
        if lastname:
            properties["lastname"] = lastname
        if phone:
            properties["phone"] = phone
        if company:
            properties["company"] = company

        resp = requests.post(
            f"{_HS_BASE}/crm/v3/objects/contacts",
            headers=self._headers(),
            json={"properties": properties},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        self._log.info("Created HubSpot contact id=%s email=%s", data.get("id"), email)
        return {"id": data.get("id"), "properties": data.get("properties", {})}

    def get_contact(self, email: str) -> dict[str, Any]:
        """Look up a contact by email address.

        Args:
            email: Email address to search for.

        Returns:
            Dict with ``id`` and ``properties``, or ``{"error": ...}`` if not
            found.
        """
        self._require_key()
        resp = requests.post(
            f"{_HS_BASE}/crm/v3/objects/contacts/search",
            headers=self._headers(),
            json={
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email,
                            }
                        ]
                    }
                ],
                "properties": ["email", "firstname", "lastname", "phone", "company"],
                "limit": 1,
            },
            timeout=20,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return {"error": f"No contact found with email '{email}'."}
        contact = results[0]
        return {"id": contact.get("id"), "properties": contact.get("properties", {})}

    def list_contacts(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent contacts.

        Args:
            limit: Number of contacts to return (1–100).

        Returns:
            List of contact summary dicts.
        """
        self._require_key()
        resp = requests.get(
            f"{_HS_BASE}/crm/v3/objects/contacts",
            headers=self._headers(),
            params={
                "limit": max(1, min(limit, 100)),
                "properties": "email,firstname,lastname,company",
            },
            timeout=20,
        )
        resp.raise_for_status()
        contacts = resp.json().get("results", [])
        return [
            {
                "id": c.get("id"),
                "email": c.get("properties", {}).get("email", ""),
                "name": " ".join(
                    filter(
                        None,
                        [
                            c.get("properties", {}).get("firstname", ""),
                            c.get("properties", {}).get("lastname", ""),
                        ],
                    )
                ),
                "company": c.get("properties", {}).get("company", ""),
            }
            for c in contacts
        ]

    # ------------------------------------------------------------------ #
    # Deals
    # ------------------------------------------------------------------ #

    def create_deal(
        self,
        name: str,
        amount: float = 0.0,
        stage: str = "appointmentscheduled",
        close_date: str = "",
    ) -> dict[str, Any]:
        """Create a new deal record.

        Args:
            name: Deal name.
            amount: Deal value in the account's default currency.
            stage: Pipeline stage ID (HubSpot default stage IDs map to names
                like ``"appointmentscheduled"``, ``"qualifiedtobuy"``,
                ``"presentationscheduled"``, ``"decisionmakerboughtin"``,
                ``"contractsent"``, ``"closedwon"``, ``"closedlost"``).
            close_date: Expected close date in ``YYYY-MM-DD`` format.

        Returns:
            Dict with ``id`` and ``properties`` of the created deal.
        """
        self._require_key()
        properties: dict[str, Any] = {
            "dealname": name,
            "dealstage": stage,
        }
        if amount:
            properties["amount"] = str(amount)
        if close_date:
            properties["closedate"] = close_date

        resp = requests.post(
            f"{_HS_BASE}/crm/v3/objects/deals",
            headers=self._headers(),
            json={"properties": properties},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        self._log.info("Created HubSpot deal id=%s name=%s", data.get("id"), name)
        return {"id": data.get("id"), "properties": data.get("properties", {})}

    def list_deals(
        self,
        stage: str = "",
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List open deals, optionally filtered by stage.

        Args:
            stage: Pipeline stage ID to filter by (empty = all stages).
            limit: Number of deals to return (1–100).

        Returns:
            List of deal summary dicts.
        """
        self._require_key()
        payload: dict[str, Any] = {
            "properties": ["dealname", "amount", "dealstage", "closedate", "hubspot_owner_id"],
            "limit": max(1, min(limit, 100)),
        }
        if stage:
            payload["filterGroups"] = [
                {
                    "filters": [
                        {
                            "propertyName": "dealstage",
                            "operator": "EQ",
                            "value": stage,
                        }
                    ]
                }
            ]
            resp = requests.post(
                f"{_HS_BASE}/crm/v3/objects/deals/search",
                headers=self._headers(),
                json=payload,
                timeout=20,
            )
        else:
            resp = requests.get(
                f"{_HS_BASE}/crm/v3/objects/deals",
                headers=self._headers(),
                params={
                    "limit": payload["limit"],
                    "properties": ",".join(payload["properties"]),
                },
                timeout=20,
            )
        resp.raise_for_status()
        deals = resp.json().get("results", [])
        return [
            {
                "id": d.get("id"),
                "name": d.get("properties", {}).get("dealname", ""),
                "amount": d.get("properties", {}).get("amount", ""),
                "stage": d.get("properties", {}).get("dealstage", ""),
                "close_date": d.get("properties", {}).get("closedate", ""),
            }
            for d in deals
        ]

    def update_deal_stage(self, deal_id: str, stage: str) -> dict[str, Any]:
        """Move a deal to a new pipeline stage.

        Args:
            deal_id: HubSpot deal ID.
            stage: New stage ID.

        Returns:
            Dict with ``id`` and updated ``properties``.
        """
        self._require_key()
        resp = requests.patch(
            f"{_HS_BASE}/crm/v3/objects/deals/{deal_id}",
            headers=self._headers(),
            json={"properties": {"dealstage": stage}},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        self._log.info("Updated deal %s to stage %s", deal_id, stage)
        return {"id": data.get("id"), "properties": data.get("properties", {})}

    # ------------------------------------------------------------------ #
    # Notes
    # ------------------------------------------------------------------ #

    def log_note(
        self,
        body: str,
        contact_id: str = "",
        deal_id: str = "",
    ) -> dict[str, Any]:
        """Log a note (engagement) in HubSpot.

        Args:
            body: Note body text.
            contact_id: Associate with this contact ID (optional).
            deal_id: Associate with this deal ID (optional).

        Returns:
            Dict with ``id`` of the created note engagement.
        """
        self._require_key()
        associations: list[dict[str, Any]] = []
        if contact_id:
            associations.append(
                {
                    "to": {"id": contact_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
                }
            )
        if deal_id:
            associations.append(
                {
                    "to": {"id": deal_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 214}],
                }
            )

        payload: dict[str, Any] = {
            "properties": {"hs_note_body": body, "hs_timestamp": ""},
        }
        if associations:
            payload["associations"] = associations

        resp = requests.post(
            f"{_HS_BASE}/crm/v3/objects/notes",
            headers=self._headers(),
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        self._log.info("Logged HubSpot note id=%s", data.get("id"))
        return {"id": data.get("id")}

    # ------------------------------------------------------------------ #
    # Pipeline summary
    # ------------------------------------------------------------------ #

    def get_pipeline_summary(self) -> dict[str, Any]:
        """Return deal counts and values grouped by pipeline stage.

        Returns:
            Dict with ``stages`` list (name, count, total_value) and
            ``totals`` (open_deals, open_value).
        """
        self._require_key()
        deals = self.list_deals(limit=100)
        stage_map: dict[str, dict[str, Any]] = {}
        for deal in deals:
            stage = deal.get("stage", "unknown")
            if stage not in stage_map:
                stage_map[stage] = {"stage": stage, "count": 0, "total_value": 0.0}
            stage_map[stage]["count"] += 1
            try:
                stage_map[stage]["total_value"] += float(deal.get("amount") or 0)
            except (TypeError, ValueError):
                pass
        stages = sorted(stage_map.values(), key=lambda s: -s["total_value"])
        total_count = sum(s["count"] for s in stages)
        total_value = sum(s["total_value"] for s in stages)
        return {
            "stages": stages,
            "totals": {"open_deals": total_count, "open_value": total_value},
        }

    # ------------------------------------------------------------------ #
    # Reports
    # ------------------------------------------------------------------ #

    def generate_crm_report(self) -> dict[str, Any]:
        """Generate a GPT-written CRM status report from live HubSpot data.

        Returns:
            Dict with ``report`` (plain text) and ``metrics`` (raw data).
        """
        import json

        pipeline = self.get_pipeline_summary()
        recent_contacts = self.list_contacts(limit=10)
        metrics = {
            "pipeline_summary": pipeline,
            "recent_contacts_count": len(recent_contacts),
        }
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _CRM_REPORT_PROMPT},
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
        * ``"create contact"`` → :meth:`create_contact`
        * ``"get contact"`` / ``"look up contact"`` / ``"find contact"`` → :meth:`get_contact`
        * ``"list contacts"`` / ``"show contacts"`` → :meth:`list_contacts`
        * ``"create deal"`` / ``"new deal"`` → :meth:`create_deal`
        * ``"list deals"`` / ``"show deals"`` / ``"open deals"`` → :meth:`list_deals`
        * ``"update deal"`` / ``"move deal"`` / ``"deal stage"`` → :meth:`update_deal_stage`
        * ``"log note"`` / ``"add note"`` → :meth:`log_note`
        * ``"pipeline"`` → :meth:`get_pipeline_summary`
        * ``"report"`` / ``"summary"`` / (default) → :meth:`generate_crm_report`

        Args:
            task: Natural-language task description.

        Returns:
            Result dict.
        """
        t = task.lower()

        if "create contact" in t or "add contact" in t:
            # Try to extract email from task
            email = self._extract_email(task)
            if not email:
                return {"error": "Please provide an email address for the new contact."}
            return self.create_contact(email=email)

        if any(kw in t for kw in ("get contact", "look up contact", "find contact", "search contact")):
            email = self._extract_email(task)
            if not email:
                return {"error": "Please provide an email address to look up."}
            return self.get_contact(email)

        if any(kw in t for kw in ("list contacts", "show contacts", "all contacts")):
            contacts = self.list_contacts()
            return {"contacts": contacts, "count": len(contacts)}

        if any(kw in t for kw in ("create deal", "new deal", "add deal")):
            # Try to extract deal name from task — take text after "deal" keyword
            name = self._extract_after(task, ("create deal", "new deal", "add deal"))
            if not name:
                name = "New deal"
            return self.create_deal(name=name)

        if any(kw in t for kw in ("list deals", "show deals", "open deals", "all deals")):
            deals = self.list_deals()
            return {"deals": deals, "count": len(deals)}

        if any(kw in t for kw in ("update deal", "move deal", "deal stage", "change stage")):
            return {"error": "Please provide deal_id and stage directly via update_deal_stage()."}

        if any(kw in t for kw in ("log note", "add note", "create note")):
            body = self._extract_after(task, ("log note", "add note", "create note"))
            if not body:
                return {"error": "Please provide the note body text."}
            return self.log_note(body=body)

        if "pipeline" in t:
            return self.get_pipeline_summary()

        # Default: full CRM report
        return self.generate_crm_report()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_key(self) -> None:
        if not self._cfg.hubspot_api_key:
            raise ValueError("HUBSPOT_API_KEY is not configured.")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._cfg.hubspot_api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _extract_email(text: str) -> str:
        """Extract the first email-like token from *text*."""
        for token in text.split():
            token = token.strip(".,;:<>\"'")
            if "@" in token and "." in token.split("@")[-1]:
                return token
        return ""

    @staticmethod
    def _extract_after(text: str, keywords: tuple[str, ...]) -> str:
        """Return the text that follows the first matched keyword."""
        lower = text.lower()
        for kw in keywords:
            idx = lower.find(kw)
            if idx != -1:
                return text[idx + len(kw):].strip(" :–-")
        return ""
