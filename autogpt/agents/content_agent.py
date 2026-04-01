"""Content Agent — generates marketing and editorial content using GPT.

Responsibilities
----------------
* Write SEO-ready blog posts from a content brief.
* Generate landing-page copy (headline, sub-headline, features, CTA).
* Produce platform-specific social-media posts (Twitter/X, LinkedIn, Instagram).
* Draft email marketing campaigns (subject line + body).

No third-party API credentials are required beyond ``OPENAI_API_KEY``.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import openai

from autogpt.config import Config
from autogpt.utils.logger import get_logger

# ------------------------------------------------------------------ #
# Prompt templates
# ------------------------------------------------------------------ #

_BLOG_POST_PROMPT = """\
You are an expert content writer for a fast-growing startup. Given a brief,
write a complete SEO-ready blog post as a JSON object:
{
  "title": "<compelling, keyword-rich title>",
  "meta_description": "<one-sentence meta description ≤155 chars>",
  "introduction": "<2-3 sentence introduction that hooks the reader>",
  "sections": [
    {"heading": "<H2 heading>", "body": "<2-4 paragraph section body>"},
    ...
  ],
  "conclusion": "<3-4 sentence conclusion with a clear call to action>"
}
Include 3-5 sections. Write in an authoritative yet accessible tone.
Output ONLY the JSON object — no prose, no markdown fences.
"""

_LANDING_PAGE_PROMPT = """\
You are an expert conversion copywriter. Given a product or service brief,
write landing-page copy as a JSON object:
{
  "headline": "<short, punchy headline ≤10 words>",
  "subheadline": "<supporting sentence that expands on the headline>",
  "value_proposition": "<2-3 sentence explanation of the core benefit>",
  "features": [
    {"title": "<feature title>", "description": "<1-2 sentence feature description>"},
    ...
  ],
  "social_proof": "<short testimonial or trust signal>",
  "cta_primary": "<primary call-to-action button text>",
  "cta_secondary": "<secondary/softer CTA text>"
}
Include 3-5 features. Focus on outcomes and benefits, not features alone.
Output ONLY the JSON object — no prose, no markdown fences.
"""

_SOCIAL_CONTENT_PROMPT = """\
You are a social media manager for a startup. Given a brief and platform,
write a JSON object:
{
  "post": "<platform-specific post text>",
  "hashtags": ["<tag1>", "<tag2>", ...],
  "notes": "<optional posting tips>"
}
Platform-specific guidelines:
- twitter: ≤280 chars total including hashtags; punchy, conversational.
- linkedin: 150-300 words; professional, insight-driven; 3-5 hashtags.
- instagram: Engaging caption 100-200 words; 10-15 hashtags.
Output ONLY the JSON object — no prose, no markdown fences.
"""

_EMAIL_CAMPAIGN_PROMPT = """\
You are an email marketing specialist for a startup. Given a campaign brief,
write a JSON object:
{
  "subject": "<subject line that drives opens — ≤60 chars>",
  "preview_text": "<preview/preheader text ≤90 chars>",
  "body": "<full plain-text email body — 150-300 words; include a clear CTA>"
}
Write in a conversational, human tone. Use short paragraphs (2-3 sentences).
Output ONLY the JSON object — no prose, no markdown fences.
"""


class ContentAgent:
    """Generates marketing and editorial content using GPT.

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

    def write_blog_post(self, brief: str) -> dict[str, Any]:
        """Generate a complete SEO-ready blog post from a brief.

        Args:
            brief: Plain-English description of the topic, audience, and
                key points to cover.

        Returns:
            Dict with ``title``, ``meta_description``, ``introduction``,
            ``sections`` (list), and ``conclusion``.
        """
        self._log.info("Writing blog post for brief: %s", brief[:80])
        raw = self._call_gpt(_BLOG_POST_PROMPT, brief, max_tokens=1500)
        result = self._parse_json(raw)
        result.setdefault("sections", [])
        self._log.info("Blog post written: %s", result.get("title", "")[:60])
        return result

    def write_landing_page(self, brief: str) -> dict[str, Any]:
        """Generate landing-page copy from a product/service brief.

        Args:
            brief: Plain-English description of the product, target audience,
                and main value proposition.

        Returns:
            Dict with ``headline``, ``subheadline``, ``value_proposition``,
            ``features``, ``social_proof``, ``cta_primary``, ``cta_secondary``.
        """
        self._log.info("Writing landing page for brief: %s", brief[:80])
        raw = self._call_gpt(_LANDING_PAGE_PROMPT, brief, max_tokens=900)
        result = self._parse_json(raw)
        result.setdefault("features", [])
        self._log.info("Landing page written: %s", result.get("headline", "")[:60])
        return result

    def write_social_content(
        self, brief: str, platform: str = "twitter"
    ) -> dict[str, Any]:
        """Generate a social-media post for the specified platform.

        Args:
            brief: Content brief describing what to communicate.
            platform: Target platform — ``"twitter"``, ``"linkedin"``, or
                ``"instagram"`` (default: ``"twitter"``).

        Returns:
            Dict with ``post``, ``hashtags``, and ``notes``.
        """
        supported = {"twitter", "linkedin", "instagram"}
        plat = platform.lower()
        if plat not in supported:
            plat = "twitter"
            self._log.warning(
                "Unknown platform %r — defaulting to twitter.", platform
            )

        self._log.info("Writing %s post for brief: %s", plat, brief[:80])
        user_content = f"Platform: {plat}\nBrief: {brief}"
        raw = self._call_gpt(_SOCIAL_CONTENT_PROMPT, user_content, max_tokens=400)
        result = self._parse_json(raw)
        result.setdefault("hashtags", [])
        result["platform"] = plat
        return result

    def write_email_campaign(self, brief: str) -> dict[str, Any]:
        """Draft an email marketing campaign from a brief.

        Args:
            brief: Campaign objective, audience, offer, and any specific
                messaging requirements.

        Returns:
            Dict with ``subject``, ``preview_text``, and ``body``.
        """
        self._log.info("Writing email campaign for brief: %s", brief[:80])
        raw = self._call_gpt(_EMAIL_CAMPAIGN_PROMPT, brief, max_tokens=600)
        result = self._parse_json(raw)
        self._log.info("Email campaign written: %s", result.get("subject", "")[:60])
        return result

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point — parse the task and route to the right method.

        Recognises keywords:
        * ``"blog"`` / ``"article"`` / ``"post"`` → :meth:`write_blog_post`
        * ``"landing page"`` / ``"homepage"`` → :meth:`write_landing_page`
        * ``"linkedin"`` / ``"instagram"`` → :meth:`write_social_content`
        * ``"email campaign"`` / ``"newsletter"`` → :meth:`write_email_campaign`
        * Default → :meth:`write_blog_post`

        Args:
            task: Natural-language task description.

        Returns:
            Result dict from the invoked method.
        """
        t = task.lower()

        if any(kw in t for kw in ("landing page", "homepage", "landing copy")):
            return self.write_landing_page(task)

        if any(kw in t for kw in ("email campaign", "newsletter", "email blast")):
            return self.write_email_campaign(task)

        if "linkedin" in t:
            return self.write_social_content(task, platform="linkedin")
        if "instagram" in t:
            return self.write_social_content(task, platform="instagram")
        # Only route to Twitter social when the task is explicitly about a tweet or
        # a social post — NOT when "social media" merely describes the topic of a
        # blog or other long-form piece.
        if any(kw in t for kw in ("write a tweet", "post a tweet", "post on twitter",
                                   "write a social post", "write a social media post")):
            return self.write_social_content(task, platform="twitter")

        # Default: blog post (also catches "blog post about social media trends", etc.)
        return self.write_blog_post(task)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _call_gpt(self, system: str, user: str, max_tokens: int = 600) -> str:
        """Call the OpenAI chat API and return the raw string response."""
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "{}").strip()

    def _parse_json(self, raw: str) -> dict[str, Any]:
        """Parse a JSON string, returning the dict or a fallback."""
        try:
            return json.loads(raw)
        except Exception:
            self._log.warning("Could not parse GPT response as JSON.")
            return {"body": raw}
