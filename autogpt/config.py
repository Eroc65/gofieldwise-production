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
    # Email  (email agent)
    # ------------------------------------------------------------------ #
    email_sendgrid_api_key: str = os.getenv("EMAIL_SENDGRID_API_KEY", "")
    email_from_address: str = os.getenv("EMAIL_FROM_ADDRESS", "")
    email_default_to: str = os.getenv("EMAIL_DEFAULT_TO", "")
    email_smtp_host: str = os.getenv("EMAIL_SMTP_HOST", "")
    email_smtp_port: int = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    email_smtp_user: str = os.getenv("EMAIL_SMTP_USER", "")
    email_smtp_password: str = os.getenv("EMAIL_SMTP_PASSWORD", "")

    # ------------------------------------------------------------------ #
    # Telegram
    # ------------------------------------------------------------------ #
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_default_chat_id: str = os.getenv("TELEGRAM_DEFAULT_CHAT_ID", "")

    # ------------------------------------------------------------------ #
    # YouTube
    # ------------------------------------------------------------------ #
    youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")
    youtube_channel_id: str = os.getenv("YOUTUBE_CHANNEL_ID", "")

    # ------------------------------------------------------------------ #
    # Google Custom Search
    # ------------------------------------------------------------------ #
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_search_engine_id: str = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")

    # ------------------------------------------------------------------ #
    # Yelp
    # ------------------------------------------------------------------ #
    yelp_api_key: str = os.getenv("YELP_API_KEY", "")

    # ------------------------------------------------------------------ #
    # Pinterest
    # ------------------------------------------------------------------ #
    pinterest_access_token: str = os.getenv("PINTEREST_ACCESS_TOKEN", "")
    pinterest_default_board_id: str = os.getenv("PINTEREST_DEFAULT_BOARD_ID", "")

    # ------------------------------------------------------------------ #
    # LinkedIn
    # ------------------------------------------------------------------ #
    linkedin_access_token: str = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    linkedin_person_urn: str = os.getenv("LINKEDIN_PERSON_URN", "")
    linkedin_org_id: str = os.getenv("LINKEDIN_ORG_ID", "")

    # ------------------------------------------------------------------ #
    # Stripe
    # ------------------------------------------------------------------ #
    stripe_secret_key: str = os.getenv("STRIPE_SECRET_KEY", "")
    stripe_default_currency: str = os.getenv("STRIPE_DEFAULT_CURRENCY", "usd")

    # ------------------------------------------------------------------ #
    # HubSpot
    # ------------------------------------------------------------------ #
    hubspot_api_key: str = os.getenv("HUBSPOT_API_KEY", "")
    hubspot_default_pipeline_id: str = os.getenv("HUBSPOT_DEFAULT_PIPELINE_ID", "")

    # ------------------------------------------------------------------ #
    # Shopify
    # ------------------------------------------------------------------ #
    shopify_store_domain: str = os.getenv("SHOPIFY_STORE_DOMAIN", "")
    shopify_access_token: str = os.getenv("SHOPIFY_ACCESS_TOKEN", "")
    shopify_currency: str = os.getenv("SHOPIFY_CURRENCY", "USD")

    # ------------------------------------------------------------------ #
    # Scheduler
    # ------------------------------------------------------------------ #
    scheduler_enabled: bool = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"

    # ------------------------------------------------------------------ #
    # Web UI
    # ------------------------------------------------------------------ #
    web_port: int = int(os.getenv("WEB_PORT", "8000"))
    session_secret: str = os.getenv("SESSION_SECRET", "")
    web_api_key: str = os.getenv("WEB_API_KEY", "")

    # ------------------------------------------------------------------ #
    # General
    # ------------------------------------------------------------------ #
    verbose: bool = os.getenv("VERBOSE", "false").lower() == "true"
    max_iterations: int = int(os.getenv("MAX_ITERATIONS", "10"))

    def validate(self) -> None:
        """Raise ``ValueError`` if critical credentials are missing."""
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required but not set.")
