"""Yelp Agent — searches local businesses and retrieves reviews via Yelp Fusion API.

Responsibilities
----------------
* Search businesses by term and location.
* Fetch detailed business information (hours, rating, address).
* Retrieve customer reviews for a specific business.
* GPT-summarise reviews or competitor research.

Configuration
-------------
``YELP_API_KEY`` — Private API key from the Yelp Developer portal.

No third-party SDK is required; the agent uses plain ``requests``.
"""

from __future__ import annotations

import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_YELP_BASE = "https://api.yelp.com/v3"

_REVIEW_SUMMARY_PROMPT = """\
You are a business intelligence analyst. Given a set of Yelp reviews for a
business, write a concise 3–5 sentence summary that captures overall sentiment,
recurring praise, and recurring complaints. Include a recommended action if
relevant.
Output ONLY the summary — no preamble.
"""

_COMPETITOR_PROMPT = """\
You are a business strategist. Given a list of local businesses with ratings
and review counts, write a 3–4 sentence competitive analysis highlighting
market leaders, gaps, and opportunities.
Output ONLY the analysis — no preamble.
"""


class YelpAgent:
    """Searches Yelp businesses and reads reviews.

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

    def search_businesses(
        self,
        term: str,
        location: str,
        limit: int = 5,
        sort_by: str = "best_match",
    ) -> list[dict[str, Any]]:
        """Search businesses on Yelp.

        Args:
            term: What to search for (e.g. ``"coffee shop"``).
            location: City, address, or zip code.
            limit: Number of results (1–50).
            sort_by: Sort order — ``"best_match"``, ``"rating"``,
                ``"review_count"``, ``"distance"``.

        Returns:
            List of business summary dicts.

        Raises:
            ValueError: If ``YELP_API_KEY`` is not set.
        """
        self._require_api_key()
        params: dict[str, Any] = {
            "term": term,
            "location": location,
            "limit": max(1, min(limit, 50)),
            "sort_by": sort_by,
        }
        resp = self._get("/businesses/search", params=params)
        businesses = resp.get("businesses", [])
        results = []
        for biz in businesses:
            results.append({
                "id": biz.get("id", ""),
                "name": biz.get("name", ""),
                "rating": biz.get("rating", 0),
                "review_count": biz.get("review_count", 0),
                "address": ", ".join(biz.get("location", {}).get("display_address", [])),
                "phone": biz.get("display_phone", ""),
                "categories": [c["title"] for c in biz.get("categories", [])],
                "url": biz.get("url", ""),
                "is_closed": biz.get("is_closed", False),
            })
        self._log.info("Yelp search %r in %r: %d results.", term, location, len(results))
        return results

    def get_business(self, business_id: str) -> dict[str, Any]:
        """Fetch detailed information about a specific business.

        Args:
            business_id: Yelp business ID (from :meth:`search_businesses`).

        Returns:
            Detailed business dict.
        """
        self._require_api_key()
        resp = self._get(f"/businesses/{business_id}")
        return {
            "id": resp.get("id", ""),
            "name": resp.get("name", ""),
            "rating": resp.get("rating", 0),
            "review_count": resp.get("review_count", 0),
            "phone": resp.get("display_phone", ""),
            "address": ", ".join(resp.get("location", {}).get("display_address", [])),
            "hours": resp.get("hours", []),
            "categories": [c["title"] for c in resp.get("categories", [])],
            "url": resp.get("url", ""),
            "photos": resp.get("photos", [])[:3],
        }

    def get_reviews(self, business_id: str, limit: int = 3) -> list[dict[str, Any]]:
        """Fetch customer reviews for a business.

        Args:
            business_id: Yelp business ID.
            limit: Number of reviews to return (up to 3 in the free tier).

        Returns:
            List of review dicts with ``author``, ``rating``, ``text``,
            ``time_created``.
        """
        self._require_api_key()
        resp = self._get(f"/businesses/{business_id}/reviews", params={"limit": limit})
        reviews = resp.get("reviews", [])
        return [
            {
                "author": r.get("user", {}).get("name", "Anonymous"),
                "rating": r.get("rating", 0),
                "text": r.get("text", ""),
                "time_created": r.get("time_created", ""),
                "url": r.get("url", ""),
            }
            for r in reviews
        ]

    def summarise_reviews(self, business_id: str) -> dict[str, Any]:
        """Fetch and GPT-summarise reviews for a business.

        Args:
            business_id: Yelp business ID.

        Returns:
            Dict with ``reviews`` (list) and ``summary`` (str).
        """
        reviews = self.get_reviews(business_id)
        summary = self._gpt_summarise(reviews, _REVIEW_SUMMARY_PROMPT)
        return {"business_id": business_id, "reviews": reviews, "summary": summary}

    def competitor_analysis(self, term: str, location: str) -> dict[str, Any]:
        """Search businesses and GPT-analyse the competitive landscape.

        Args:
            term: Category or product type (e.g. ``"yoga studio"``).
            location: City or area.

        Returns:
            Dict with ``businesses`` (list), ``analysis`` (str).
        """
        businesses = self.search_businesses(term, location, limit=10, sort_by="rating")
        analysis = self._gpt_summarise(businesses, _COMPETITOR_PROMPT)
        return {"term": term, "location": location, "businesses": businesses, "analysis": analysis}

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point.

        Recognises keywords:
        * ``"reviews"`` / ``"review summary"`` → :meth:`summarise_reviews`
        * ``"competitor"`` / ``"competitive"`` → :meth:`competitor_analysis`
        * ``"business details"`` / ``"info about"`` → :meth:`get_business`
        * Everything else → :meth:`search_businesses` + GPT analysis

        The task text is parsed for location with the pattern ``"in <location>"``.

        Args:
            task: Natural-language task description.

        Returns:
            Result dict.
        """
        t = task.lower()

        # Extract location hint: "coffee shops in Seattle"
        # Use a simple string split to avoid regex backtracking on user input.
        _in_marker = " in "
        _in_pos = t.find(_in_marker)
        if _in_pos != -1:
            after_in = task[_in_pos + len(_in_marker):]
            # Stop at common conjunctions
            for stopper in (" and ", " with ", " near "):
                idx = after_in.lower().find(stopper)
                if idx != -1:
                    after_in = after_in[:idx]
            location = after_in.strip() or "New York, NY"
        else:
            location = "New York, NY"

        if any(kw in t for kw in ("review", "what do customers")):
            # Try to find a business id or name in the task
            words = task.split()
            biz_id = words[-1] if words else ""
            return self.summarise_reviews(biz_id)

        if any(kw in t for kw in ("competitor", "competitive", "competition")):
            # Extract term: everything before " in " (or full task if not found)
            term = task[:_in_pos].strip() if _in_pos != -1 else task
            return self.competitor_analysis(term, location)

        # Default: search
        return {"businesses": self.search_businesses(task, location)}

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_api_key(self) -> None:
        if not self._cfg.yelp_api_key:
            raise ValueError("YELP_API_KEY is not configured.")

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request to the Yelp Fusion API."""
        headers = {"Authorization": f"Bearer {self._cfg.yelp_api_key}"}
        resp = requests.get(
            f"{_YELP_BASE}{path}",
            headers=headers,
            params=params or {},
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()

    def _gpt_summarise(self, data: Any, system_prompt: str) -> str:
        """Run GPT with *system_prompt* over *data*."""
        import json
        content = json.dumps(data, default=str)[:3000]
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        return (response.choices[0].message.content or "").strip()
