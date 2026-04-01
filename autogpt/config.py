"""Central configuration for the startup operations platform.

All secrets and tunable parameters are loaded from environment variables
(typically via a ``.env`` file).  See ``.env.example`` for a full list.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root (one level above this package)
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(_env_path, override=False)


class Config:
    """Application-wide configuration."""

    # ------------------------------------------------------------------ #
    # OpenAI
    # ------------------------------------------------------------------ #
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # ------------------------------------------------------------------ #
    # GitHub
    # ------------------------------------------------------------------ #
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_org: str = os.getenv("GITHUB_ORG", "")

    # ------------------------------------------------------------------ #
    # Render (deployment)
    # ------------------------------------------------------------------ #
    render_api_key: str = os.getenv("RENDER_API_KEY", "")
    render_owner_id: str = os.getenv("RENDER_OWNER_ID", "")

    # ------------------------------------------------------------------ #
    # PostgreSQL / Neon / Render Postgres
    # ------------------------------------------------------------------ #
    database_url: str = os.getenv("DATABASE_URL", "")

    # ------------------------------------------------------------------ #
    # Twitter / X
    # ------------------------------------------------------------------ #
    twitter_api_key: str = os.getenv("TWITTER_API_KEY", "")
    twitter_api_secret: str = os.getenv("TWITTER_API_SECRET", "")
    twitter_access_token: str = os.getenv("TWITTER_ACCESS_TOKEN", "")
    twitter_access_secret: str = os.getenv("TWITTER_ACCESS_SECRET", "")
    twitter_bearer_token: str = os.getenv("TWITTER_BEARER_TOKEN", "")

    # ------------------------------------------------------------------ #
    # Meta / Facebook Ads
    # ------------------------------------------------------------------ #
    meta_app_id: str = os.getenv("META_APP_ID", "")
    meta_app_secret: str = os.getenv("META_APP_SECRET", "")
    meta_access_token: str = os.getenv("META_ACCESS_TOKEN", "")
    meta_ad_account_id: str = os.getenv("META_AD_ACCOUNT_ID", "")

    # ------------------------------------------------------------------ #
    # Slack
    # ------------------------------------------------------------------ #
    slack_webhook_url: str = os.getenv("SLACK_WEBHOOK_URL", "")
    slack_bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
    slack_default_channel: str = os.getenv("SLACK_DEFAULT_CHANNEL", "general")

    # ------------------------------------------------------------------ #
    # Scheduler
    # ------------------------------------------------------------------ #
    scheduler_enabled: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

    # ------------------------------------------------------------------ #
    # Web UI
    # ------------------------------------------------------------------ #
    web_port: int = int(os.getenv("WEB_PORT", "8000"))
    session_secret: str = os.getenv("SESSION_SECRET", "")

    # ------------------------------------------------------------------ #
    # General
    # ------------------------------------------------------------------ #
    verbose: bool = os.getenv("VERBOSE", "false").lower() == "true"
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "10"))

    def validate(self) -> None:
        """Raise ``ValueError`` if critical credentials are missing."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required but not set.")
