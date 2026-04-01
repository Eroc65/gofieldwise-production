"""LinkedIn Agent — manages a LinkedIn company page and supports B2B outreach.

Responsibilities
----------------
* Post text/article updates to a LinkedIn company page or personal profile.
* Search for people and companies using the LinkedIn Search API.
* Retrieve basic analytics for a company page (followers, impressions).
* GPT-compose posts from a content brief.

Configuration
-------------
``LINKEDIN_ACCESS_TOKEN``   — OAuth 2.0 access token with the
    ``w_member_social``, ``r_organization_social``, and ``rw_organization_admin``
    scopes, obtained via the LinkedIn developer portal.
``LINKEDIN_PERSON_URN``     — URN of the authenticated member (e.g.
    ``urn:li:person:ABC123``).  Used when posting to a personal profile.
``LINKEDIN_ORG_ID``         — Numeric ID of the LinkedIn organization / company
    page (e.g. ``12345678``).  Used for company-page posts and analytics.

No third-party SDK is required; the agent uses plain ``requests``.
"""

from __future__ import annotations

import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_LINKEDIN_BASE = "https://api.linkedin.com/v2"
_LINKEDIN_REST_BASE = "https://api.linkedin.com/rest"

_POST_PROMPT = """\
You are a professional LinkedIn content strategist for a startup.
Given a content brief, write a compelling LinkedIn post (150–300 words) that
is insightful, professional, and ends with a thought-provoking question or
clear call-to-action. Use short paragraphs and occasional line breaks for
readability.
Output ONLY the post text — no preamble, no quotes, no markdown fences.
"""


class LinkedInAgent:
    """Manages LinkedIn presence via the LinkedIn REST and v2 APIs.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key

    # ------------------------------------------------------------------ #
    # Public interface — Posting
    # ------------------------------------------------------------------ #

    def post_update(
        self,
        text: str,
        as_organization: bool = False,
    ) -> dict[str, Any]:
        """Post a text update to LinkedIn.

        Args:
            text: The post body (plain text).
            as_organization: When ``True`` and ``LINKEDIN_ORG_ID`` is
                configured, post as the company page; otherwise post as the
                authenticated member.

        Returns:
            Dict with ``post_id`` and ``author`` on success.
        """
        self._require_token()
        author = self._resolve_author(as_organization)
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }
        resp = requests.post(
            f"{_LINKEDIN_BASE}/ugcPosts",
            headers=self._headers(),
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        post_id = resp.headers.get("x-restli-id", "")
        self._log.info("LinkedIn post published (id=%s) as %s", post_id, author)
        return {"post_id": post_id, "author": author, "text_preview": text[:100]}

    def compose_and_post(
        self,
        brief: str,
        as_organization: bool = False,
    ) -> dict[str, Any]:
        """GPT-compose a LinkedIn post from a brief and publish it.

        Args:
            brief: Plain-English description of what the post should cover.
            as_organization: When ``True``, post as the company page.

        Returns:
            Dict with ``text``, ``post_id``, and ``author``.
        """
        text = self._compose_post(brief)
        self._log.info("Composed LinkedIn post: %s…", text[:80])
        result = self.post_update(text, as_organization=as_organization)
        result["text"] = text
        return result

    # ------------------------------------------------------------------ #
    # Public interface — Search
    # ------------------------------------------------------------------ #

    def search_people(
        self,
        keywords: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for LinkedIn members by keyword.

        Uses the People Search API (requires ``r_liteprofile`` scope).

        Args:
            keywords: Search terms (e.g. ``"startup CTO San Francisco"``).
            max_results: Number of results to return (1–50).

        Returns:
            List of member dicts with ``urn``, ``first_name``, ``last_name``,
            and ``headline``.
        """
        self._require_token()
        params: dict[str, Any] = {
            "q": "people",
            "keywords": keywords,
            "count": max(1, min(max_results, 50)),
            "projection": "(elements*(id,firstName,lastName,headline))",
        }
        resp = requests.get(
            f"{_LINKEDIN_BASE}/people",
            headers=self._headers(),
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        elements = data.get("elements", [])
        return [
            {
                "urn": f"urn:li:person:{e.get('id', '')}",
                "first_name": (e.get("firstName") or {}).get("localized", {}).get("en_US", ""),
                "last_name": (e.get("lastName") or {}).get("localized", {}).get("en_US", ""),
                "headline": (e.get("headline") or {}).get("localized", {}).get("en_US", ""),
            }
            for e in elements
        ]

    def search_companies(
        self,
        keywords: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for companies by keyword.

        Args:
            keywords: Search terms (e.g. ``"Series A fintech London"``).
            max_results: Number of results to return (1–50).

        Returns:
            List of company dicts with ``id``, ``name``, and ``description``.
        """
        self._require_token()
        params: dict[str, Any] = {
            "q": "search",
            "query.keywords": keywords,
            "count": max(1, min(max_results, 50)),
        }
        resp = requests.get(
            f"{_LINKEDIN_BASE}/organizations",
            headers=self._headers(),
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        elements = data.get("elements", [])
        return [
            {
                "id": e.get("id", ""),
                "name": (e.get("localizedName") or ""),
                "description": (e.get("localizedDescription") or ""),
            }
            for e in elements
        ]

    # ------------------------------------------------------------------ #
    # Public interface — Analytics
    # ------------------------------------------------------------------ #

    def get_company_stats(self) -> dict[str, Any]:
        """Retrieve follower and share statistics for the configured company page.

        Requires ``LINKEDIN_ORG_ID`` to be set and the access token to have
        ``r_organization_social`` scope.

        Returns:
            Dict with ``follower_count``, ``share_count``, and ``org_id``.
        """
        self._require_token()
        if not self._cfg.linkedin_org_id:
            raise ValueError("LINKEDIN_ORG_ID is not configured.")

        org_id = self._cfg.linkedin_org_id

        # Follower count
        follower_count: int | None = None
        try:
            resp = requests.get(
                f"{_LINKEDIN_BASE}/networkSizes/urn:li:organization:{org_id}",
                headers=self._headers(),
                params={"edgeType": "CompanyFollowedByMember"},
                timeout=20,
            )
            if resp.ok:
                follower_count = resp.json().get("firstDegreeSize")
        except Exception as exc:
            self._log.debug("Could not fetch follower count: %s", exc)

        # Share / post count via organization shares endpoint
        share_count: int | None = None
        try:
            resp2 = requests.get(
                f"{_LINKEDIN_BASE}/shares",
                headers=self._headers(),
                params={"q": "owners", "owners": f"urn:li:organization:{org_id}", "count": 1},
                timeout=20,
            )
            if resp2.ok:
                share_count = resp2.json().get("paging", {}).get("total")
        except Exception as exc:
            self._log.debug("Could not fetch share count: %s", exc)

        return {
            "org_id": org_id,
            "follower_count": follower_count,
            "share_count": share_count,
        }

    # ------------------------------------------------------------------ #
    # Orchestrator entry point
    # ------------------------------------------------------------------ #

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point.

        Recognises keywords:
        * ``"search people"`` / ``"find people"`` → :meth:`search_people`
        * ``"search companies"`` / ``"find companies"`` → :meth:`search_companies`
        * ``"company stats"`` / ``"page stats"`` / ``"followers"`` → :meth:`get_company_stats`
        * ``"post"`` / ``"publish"`` / ``"share"`` / (default) → :meth:`compose_and_post`

        Args:
            task: Natural-language task description.

        Returns:
            Result dict.
        """
        t = task.lower()

        if any(kw in t for kw in ("search people", "find people", "lookup people")):
            results = self.search_people(task)
            return {"people": results, "count": len(results)}

        if any(kw in t for kw in ("search companies", "find companies", "lookup companies")):
            results = self.search_companies(task)
            return {"companies": results, "count": len(results)}

        if any(kw in t for kw in ("company stats", "page stats", "follower", "analytics")):
            return self.get_company_stats()

        as_org = any(kw in t for kw in ("company page", "org page", "organization", "as company", "as org"))
        return self.compose_and_post(task, as_organization=as_org)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_token(self) -> None:
        if not self._cfg.linkedin_access_token:
            raise ValueError("LINKEDIN_ACCESS_TOKEN is not configured.")

    def _resolve_author(self, as_organization: bool) -> str:
        """Return the appropriate author URN."""
        if as_organization and self._cfg.linkedin_org_id:
            return f"urn:li:organization:{self._cfg.linkedin_org_id}"
        if self._cfg.linkedin_person_urn:
            return self._cfg.linkedin_person_urn
        raise ValueError(
            "Neither LINKEDIN_PERSON_URN nor LINKEDIN_ORG_ID is configured."
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._cfg.linkedin_access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _compose_post(self, brief: str) -> str:
        """Use GPT to write a LinkedIn post from a content brief."""
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _POST_PROMPT},
                {"role": "user", "content": brief},
            ],
            temperature=0.7,
            max_tokens=400,
        )
        return (response.choices[0].message.content or "").strip()
