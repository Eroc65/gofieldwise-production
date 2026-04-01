"""Google Agent — web search and result summarisation via Google Custom Search API.

Responsibilities
----------------
* Run Google web searches using the Custom Search JSON API.
* GPT-summarise search results into a concise research brief.
* Optionally filter results by site or date.

Configuration
-------------
``GOOGLE_API_KEY``       — Google Cloud API key with Custom Search API enabled.
``GOOGLE_SEARCH_ENGINE_ID`` — Programmable Search Engine ID (cx parameter).

No third-party SDK is required; the agent uses plain ``requests``.
"""

from __future__ import annotations

import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_GOOGLE_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

_SUMMARISE_PROMPT = """\
You are a research assistant helping a startup founder synthesise web-search results.
Given a list of search results (title, snippet, URL), write a concise 3–5 sentence
research brief that captures the key findings.  Include the most relevant URLs as
inline references.
Output ONLY the research brief — no preamble.
"""

_ANSWER_PROMPT = """\
You are a knowledgeable assistant. Answer the user's question directly and
concisely (2–4 sentences) based on the provided search results.
If the results don't contain enough information, say so.
Output ONLY the answer.
"""


class GoogleAgent:
    """Runs Google web searches and summarises results with GPT.

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

    def search(
        self,
        query: str,
        num_results: int = 5,
        site_filter: str | None = None,
        date_restrict: str | None = None,
    ) -> list[dict[str, Any]]:
        """Run a Google Custom Search.

        Args:
            query: The search query.
            num_results: Number of results (1–10; Google API cap).
            site_filter: Restrict results to a specific site (e.g.
                ``"techcrunch.com"``).
            date_restrict: Restrict to recent results, e.g. ``"d7"`` (past 7
                days), ``"m1"`` (past month), ``"y1"`` (past year).

        Returns:
            List of result dicts with ``title``, ``link``, ``snippet``.

        Raises:
            ValueError: If ``GOOGLE_API_KEY`` or
                ``GOOGLE_SEARCH_ENGINE_ID`` are not set.
        """
        self._require_credentials()
        effective_query = f"{query} site:{site_filter}" if site_filter else query
        params: dict[str, Any] = {
            "key": self._cfg.google_api_key,
            "cx": self._cfg.google_search_engine_id,
            "q": effective_query,
            "num": max(1, min(num_results, 10)),
        }
        if date_restrict:
            params["dateRestrict"] = date_restrict

        self._log.info("Google search: %r (n=%d)", effective_query[:80], params["num"])
        resp = requests.get(_GOOGLE_SEARCH_URL, params=params, timeout=20)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        results = [
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in items
        ]
        self._log.info("Google search returned %d results.", len(results))
        return results

    def search_and_summarise(
        self,
        query: str,
        num_results: int = 5,
        site_filter: str | None = None,
    ) -> dict[str, Any]:
        """Search Google and GPT-summarise the results.

        Args:
            query: The research question or topic.
            num_results: Number of search results to retrieve.
            site_filter: Restrict to a specific domain.

        Returns:
            Dict with ``query``, ``results`` (list), and ``summary`` (str).
        """
        results = self.search(query, num_results=num_results, site_filter=site_filter)
        summary = self._summarise(query, results, prompt=_SUMMARISE_PROMPT)
        return {"query": query, "results": results, "summary": summary}

    def answer_question(self, question: str, num_results: int = 5) -> dict[str, Any]:
        """Use Google + GPT to answer a factual question.

        Args:
            question: The question to answer.
            num_results: Number of search results to use as context.

        Returns:
            Dict with ``question``, ``answer``, and ``sources``.
        """
        results = self.search(question, num_results=num_results)
        answer = self._summarise(question, results, prompt=_ANSWER_PROMPT)
        sources = [r["link"] for r in results if r.get("link")]
        return {"question": question, "answer": answer, "sources": sources}

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point.

        Recognises keywords:
        * ``"answer"`` / ``"what is"`` / ``"who is"`` / ``"how"`` →
          :meth:`answer_question`
        * Everything else → :meth:`search_and_summarise`

        Args:
            task: Natural-language task description.

        Returns:
            Result dict.
        """
        t = task.lower()
        if any(kw in t for kw in ("answer", "what is", "who is", "how does",
                                   "how do", "why is", "when did")):
            return self.answer_question(task)
        return self.search_and_summarise(task)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_credentials(self) -> None:
        if not self._cfg.google_api_key:
            raise ValueError("GOOGLE_API_KEY is not configured.")
        if not self._cfg.google_search_engine_id:
            raise ValueError("GOOGLE_SEARCH_ENGINE_ID is not configured.")

    def _summarise(
        self, query: str, results: list[dict[str, Any]], prompt: str
    ) -> str:
        """GPT-summarise a list of search results."""
        import json
        context = json.dumps(
            [{"title": r["title"], "snippet": r["snippet"], "url": r["link"]} for r in results],
            indent=2,
        )[:3000]
        user_content = f"Query: {query}\n\nSearch results:\n{context}"
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        return (response.choices[0].message.content or "").strip()
