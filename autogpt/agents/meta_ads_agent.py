"""Meta Ads Agent — creates and manages Meta (Facebook/Instagram) ad campaigns.

Responsibilities
----------------
* Create ad campaigns, ad sets, and ads via the Meta Marketing API.
* Fetch campaign performance insights.
* Pause / resume / update campaigns.
* Generate ad copy and creative briefs with the OpenAI API.

Requires the ``facebook-sdk`` library:
    pip install facebook-sdk
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_META_API_VERSION = "v19.0"
_META_BASE = f"https://graph.facebook.com/{_META_API_VERSION}"

_AD_COPY_PROMPT = """\
You are an expert digital advertising copywriter.
Given a product or service brief, write ad copy as a JSON object:
{
  "headline": "<short, punchy headline ≤40 chars>",
  "body": "<engaging body copy ≤125 chars>",
  "cta": "<call-to-action text, e.g. 'Shop Now'>"
}
Output ONLY the JSON object — no prose, no markdown fences.
"""


class MetaAdsAgent:
    """Creates and manages Meta advertising campaigns.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        self._token = config.meta_access_token
        self._account_id = config.meta_ad_account_id
        openai.api_key = config.openai_api_key

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def create_campaign(
        self,
        name: str,
        objective: str = "OUTCOME_TRAFFIC",
        status: str = "PAUSED",
    ) -> dict[str, Any]:
        """Create a new top-level campaign.

        Args:
            name: Display name for the campaign.
            objective: Meta campaign objective constant.
            status: ``"ACTIVE"`` or ``"PAUSED"`` (default: ``"PAUSED"``).

        Returns:
            API response with ``id`` of the created campaign.
        """
        resp = requests.post(
            f"{_META_BASE}/act_{self._account_id}/campaigns",
            params={
                "access_token": self._token,
                "name": name,
                "objective": objective,
                "status": status,
                "special_ad_categories": "[]",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._log.info("Created campaign '%s' id=%s", name, data.get("id"))
        return data

    def create_ad_set(
        self,
        campaign_id: str,
        name: str,
        daily_budget_cents: int,
        targeting: dict[str, Any] | None = None,
        status: str = "PAUSED",
    ) -> dict[str, Any]:
        """Create an ad set inside an existing campaign.

        Args:
            campaign_id: Parent campaign ID.
            name: Ad set name.
            daily_budget_cents: Daily budget in account currency minor units
                (e.g. 1000 = $10.00 USD).
            targeting: Meta targeting spec dict.  Defaults to a broad US spec.
            status: ``"ACTIVE"`` or ``"PAUSED"``.

        Returns:
            API response with ``id`` of the created ad set.
        """
        if targeting is None:
            targeting = {"geo_locations": {"countries": ["US"]}, "age_min": 18}

        resp = requests.post(
            f"{_META_BASE}/act_{self._account_id}/adsets",
            params={
                "access_token": self._token,
                "name": name,
                "campaign_id": campaign_id,
                "daily_budget": daily_budget_cents,
                "billing_event": "IMPRESSIONS",
                "optimization_goal": "REACH",
                "targeting": json.dumps(targeting),
                "status": status,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._log.info("Created ad set '%s' id=%s", name, data.get("id"))
        return data

    def create_ad(
        self,
        ad_set_id: str,
        name: str,
        creative_id: str,
        status: str = "PAUSED",
    ) -> dict[str, Any]:
        """Create an individual ad inside an ad set.

        Args:
            ad_set_id: Parent ad set ID.
            name: Ad name.
            creative_id: Pre-existing Meta ad creative ID.
            status: ``"ACTIVE"`` or ``"PAUSED"``.

        Returns:
            API response with ``id`` of the created ad.
        """
        resp = requests.post(
            f"{_META_BASE}/act_{self._account_id}/ads",
            params={
                "access_token": self._token,
                "name": name,
                "adset_id": ad_set_id,
                "creative": f'{{"creative_id": "{creative_id}"}}',
                "status": status,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self._log.info("Created ad '%s' id=%s", name, data.get("id"))
        return data

    def get_insights(
        self,
        campaign_id: str,
        fields: list[str] | None = None,
        date_preset: str = "last_7d",
    ) -> list[dict[str, Any]]:
        """Fetch performance insights for a campaign.

        Args:
            campaign_id: The campaign to query.
            fields: Insight fields to retrieve.  Defaults to
                ``["impressions", "clicks", "spend", "ctr"]``.
            date_preset: Meta date preset string.

        Returns:
            List of insight row dicts.
        """
        if fields is None:
            fields = ["impressions", "clicks", "spend", "ctr"]
        resp = requests.get(
            f"{_META_BASE}/{campaign_id}/insights",
            params={
                "access_token": self._token,
                "fields": ",".join(fields),
                "date_preset": date_preset,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    def update_campaign_status(self, campaign_id: str, status: str) -> dict[str, Any]:
        """Pause or activate a campaign.

        Args:
            campaign_id: The campaign to update.
            status: ``"ACTIVE"`` or ``"PAUSED"``.

        Returns:
            API response.
        """
        resp = requests.post(
            f"{_META_BASE}/{campaign_id}",
            params={"access_token": self._token, "status": status},
            timeout=30,
        )
        resp.raise_for_status()
        self._log.info("Updated campaign %s status to %s", campaign_id, status)
        return resp.json()

    def generate_ad_copy(self, brief: str) -> dict[str, str]:
        """Use GPT to generate ad headline, body, and CTA from a brief.

        Args:
            brief: Plain-English description of the product or offer.

        Returns:
            Dict with ``headline``, ``body``, and ``cta`` keys.
        """
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _AD_COPY_PROMPT},
                {"role": "user", "content": brief},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            self._log.warning("Could not parse GPT ad copy as JSON.")
            return {"headline": "", "body": raw, "cta": "Learn More"}
