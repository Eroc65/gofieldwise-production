"""YouTube Agent — searches videos and retrieves channel/video statistics.

Responsibilities
----------------
* Search YouTube for videos matching a query.
* Fetch detailed statistics for a specific video (views, likes, comments).
* Retrieve channel statistics (subscriber count, total views, video count).
* List the most recent uploads from the configured channel.
* GPT-summarise search results or channel performance.

Configuration
-------------
``YOUTUBE_API_KEY`` — Google Cloud API key with YouTube Data API v3 enabled.
``YOUTUBE_CHANNEL_ID`` — Channel ID for channel-specific queries (optional).

No third-party SDK is required; the agent uses plain ``requests``.
"""

from __future__ import annotations

import logging
from typing import Any

import openai
import requests

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_YOUTUBE_BASE = "https://www.googleapis.com/youtube/v3"

_SUMMARISE_PROMPT = """\
You are a data analyst summarising YouTube performance data for a startup.
Given a JSON dataset, write a concise 2–4 sentence summary highlighting the
most important metrics and any actionable insights.
Output ONLY the summary text.
"""


class YouTubeAgent:
    """Searches YouTube and fetches video/channel statistics.

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

    def search_videos(
        self,
        query: str,
        max_results: int = 10,
        order: str = "relevance",
    ) -> list[dict[str, Any]]:
        """Search YouTube for videos matching *query*.

        Args:
            query: Search query string.
            max_results: Number of results to return (1–50).
            order: Result ordering — ``"relevance"``, ``"date"``, ``"viewCount"``.

        Returns:
            List of video summary dicts (``id``, ``title``, ``channel``,
            ``published_at``, ``description``).

        Raises:
            ValueError: If ``YOUTUBE_API_KEY`` is not set.
        """
        self._require_api_key()
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max(1, min(max_results, 50)),
            "order": order,
            "key": self._cfg.youtube_api_key,
        }
        resp = requests.get(f"{_YOUTUBE_BASE}/search", params=params, timeout=20)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        results = []
        for item in items:
            snip = item.get("snippet", {})
            results.append({
                "id": item.get("id", {}).get("videoId", ""),
                "title": snip.get("title", ""),
                "channel": snip.get("channelTitle", ""),
                "published_at": snip.get("publishedAt", ""),
                "description": snip.get("description", "")[:200],
            })
        self._log.info("YouTube search for %r returned %d results.", query, len(results))
        return results

    def get_video_stats(self, video_id: str) -> dict[str, Any]:
        """Fetch statistics for a specific video.

        Args:
            video_id: YouTube video ID (the ``v=`` parameter).

        Returns:
            Dict with ``title``, ``view_count``, ``like_count``,
            ``comment_count``, ``published_at``.
        """
        self._require_api_key()
        params = {
            "part": "snippet,statistics",
            "id": video_id,
            "key": self._cfg.youtube_api_key,
        }
        resp = requests.get(f"{_YOUTUBE_BASE}/videos", params=params, timeout=20)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return {"error": f"Video {video_id!r} not found."}
        item = items[0]
        stats = item.get("statistics", {})
        snip = item.get("snippet", {})
        return {
            "id": video_id,
            "title": snip.get("title", ""),
            "channel": snip.get("channelTitle", ""),
            "published_at": snip.get("publishedAt", ""),
            "view_count": int(stats.get("viewCount", 0)),
            "like_count": int(stats.get("likeCount", 0)),
            "comment_count": int(stats.get("commentCount", 0)),
        }

    def get_channel_stats(self, channel_id: str | None = None) -> dict[str, Any]:
        """Fetch statistics for a YouTube channel.

        Args:
            channel_id: YouTube channel ID.  Falls back to
                ``YOUTUBE_CHANNEL_ID`` when omitted.

        Returns:
            Dict with ``title``, ``subscriber_count``, ``video_count``,
            ``view_count``.
        """
        self._require_api_key()
        cid = channel_id or self._cfg.youtube_channel_id
        if not cid:
            raise ValueError("No channel_id provided and YOUTUBE_CHANNEL_ID is not set.")
        params = {
            "part": "snippet,statistics",
            "id": cid,
            "key": self._cfg.youtube_api_key,
        }
        resp = requests.get(f"{_YOUTUBE_BASE}/channels", params=params, timeout=20)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if not items:
            return {"error": f"Channel {cid!r} not found."}
        item = items[0]
        stats = item.get("statistics", {})
        snip = item.get("snippet", {})
        return {
            "id": cid,
            "title": snip.get("title", ""),
            "description": snip.get("description", "")[:200],
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
        }

    def list_channel_videos(
        self,
        channel_id: str | None = None,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Return the most recent uploads from a channel.

        Args:
            channel_id: YouTube channel ID.  Falls back to
                ``YOUTUBE_CHANNEL_ID``.
            max_results: Number of videos to return (1–50).

        Returns:
            List of video summary dicts.
        """
        return self.search_videos(
            query="",
            max_results=max_results,
        )

    def summarise(self, data: Any) -> str:
        """GPT-summarise a search result list or stats dict.

        Args:
            data: A list or dict of YouTube data.

        Returns:
            Plain-text summary string.
        """
        import json
        user_content = json.dumps(data, default=str)[:3000]
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _SUMMARISE_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return (response.choices[0].message.content or "").strip()

    def run(self, task: str) -> dict[str, Any]:
        """Orchestrator entry point.

        Recognises keywords:
        * ``"channel stats"`` / ``"channel analytics"`` → :meth:`get_channel_stats`
        * ``"video stats"`` / ``"video details"`` + a video ID → :meth:`get_video_stats`
        * Everything else → :meth:`search_videos` + GPT summary

        Args:
            task: Natural-language task description.

        Returns:
            Result dict.
        """
        import re
        t = task.lower()

        if any(kw in t for kw in ("channel stats", "channel analytics", "my channel")):
            stats = self.get_channel_stats()
            summary = self.summarise(stats)
            return {"stats": stats, "summary": summary}

        # Check for a video ID in the task
        video_id_match = re.search(r"[A-Za-z0-9_-]{11}", task)
        if any(kw in t for kw in ("video stats", "video details", "stats for")) and video_id_match:
            vid = video_id_match.group(0)
            stats = self.get_video_stats(vid)
            summary = self.summarise(stats)
            return {"stats": stats, "summary": summary}

        videos = self.search_videos(task)
        summary = self.summarise(videos)
        return {"videos": videos, "count": len(videos), "summary": summary}

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _require_api_key(self) -> None:
        if not self._cfg.youtube_api_key:
            raise ValueError("YOUTUBE_API_KEY is not configured.")
