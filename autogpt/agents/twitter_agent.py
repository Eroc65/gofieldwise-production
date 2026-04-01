"""Twitter / X Agent — manages a shared Twitter account.

Responsibilities
----------------
* Post tweets (plain text and with media).
* Read the home timeline.
* Search for tweets by keyword.
* Like and retweet posts.
* Compose & schedule content using the OpenAI API.

Requires the ``tweepy`` library:
    pip install tweepy
"""

from __future__ import annotations

import logging
from typing import Any

import openai

from autogpt.config import Config
from autogpt.utils.logger import get_logger

_COMPOSE_PROMPT = """\
You are a social media manager.  Given a content brief, write a single tweet
(≤280 characters) that is engaging, on-brand, and ends with relevant hashtags.
Output ONLY the tweet text — no quotes, no explanation.
"""


class TwitterAgent:
    """Manages a shared Twitter / X account via the Twitter API v2.

    Args:
        config: Application :class:`~autogpt.config.Config` instance.
    """

    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._log: logging.Logger = get_logger(__name__, config.verbose)
        openai.api_key = config.openai_api_key
        self._client = self._build_client()

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def post_tweet(self, text: str) -> dict[str, Any]:
        """Post a tweet with the given text.

        Args:
            text: The tweet body (≤280 characters).

        Returns:
            Twitter API response dict.
        """
        self._log.info("Posting tweet: %s", text[:60])
        response = self._client.create_tweet(text=text)
        tweet_id = response.data.get("id") if response.data else None
        self._log.info("Tweet posted, id=%s", tweet_id)
        return response.data or {}

    def compose_and_post(self, brief: str) -> dict[str, Any]:
        """Generate a tweet from a content brief and post it immediately.

        Args:
            brief: Plain-English description of what to tweet about.

        Returns:
            Twitter API response dict.
        """
        text = self._compose(brief)
        self._log.info("Composed tweet from brief: %s", text[:60])
        return self.post_tweet(text)

    def get_timeline(self, max_results: int = 10) -> list[dict[str, Any]]:
        """Return the authenticated user's home timeline.

        Args:
            max_results: Number of tweets to return (5–100).

        Returns:
            List of tweet dicts.
        """
        me = self._client.get_me()
        user_id = me.data.id if me.data else None
        if not user_id:
            return []
        response = self._client.get_home_timeline(
            max_results=max(5, min(max_results, 100)),
            tweet_fields=["created_at", "author_id", "text"],
        )
        if not response.data:
            return []
        return [{"id": t.id, "text": t.text} for t in response.data]

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Search recent tweets by keyword or hashtag.

        Args:
            query: Twitter search query string.
            max_results: Number of tweets to return (10–100).

        Returns:
            List of tweet dicts.
        """
        response = self._client.search_recent_tweets(
            query=query,
            max_results=max(10, min(max_results, 100)),
            tweet_fields=["created_at", "author_id", "text"],
        )
        if not response.data:
            return []
        return [{"id": t.id, "text": t.text} for t in response.data]

    def like(self, tweet_id: str) -> dict[str, Any]:
        """Like a tweet.

        Args:
            tweet_id: The ID of the tweet to like.

        Returns:
            Twitter API response dict.
        """
        me = self._client.get_me()
        user_id = me.data.id if me.data else None
        if not user_id:
            return {"liked": False}
        resp = self._client.like(user_id, tweet_id)
        return resp.data or {}

    def retweet(self, tweet_id: str) -> dict[str, Any]:
        """Retweet a post.

        Args:
            tweet_id: The ID of the tweet to retweet.

        Returns:
            Twitter API response dict.
        """
        me = self._client.get_me()
        user_id = me.data.id if me.data else None
        if not user_id:
            return {"retweeted": False}
        resp = self._client.retweet(user_id, tweet_id)
        return resp.data or {}

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_client(self) -> Any:
        try:
            import tweepy  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "tweepy is not installed. Run `pip install tweepy`."
            ) from exc

        return tweepy.Client(
            bearer_token=self._cfg.twitter_bearer_token,
            consumer_key=self._cfg.twitter_api_key,
            consumer_secret=self._cfg.twitter_api_secret,
            access_token=self._cfg.twitter_access_token,
            access_token_secret=self._cfg.twitter_access_secret,
            wait_on_rate_limit=True,
        )

    def _compose(self, brief: str) -> str:
        """Use GPT to write a tweet from a content brief."""
        response = openai.chat.completions.create(
            model=self._cfg.openai_model,
            messages=[
                {"role": "system", "content": _COMPOSE_PROMPT},
                {"role": "user", "content": brief},
            ],
            temperature=0.7,
            max_tokens=120,
        )
        return (response.choices[0].message.content or "").strip()
