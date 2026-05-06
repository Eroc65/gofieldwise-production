from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LandbotDailyViralGoodsOut(BaseModel):
    ok: bool
    airtable_synced: bool
    shopify_synced: bool
    zapier_triggered: bool = False
    airtable_record_id: str | None = None
    shopify_customer_id: str | None = None
    summary: str
    error: str | None = None


class DailyViralGoodsHealthOut(BaseModel):
    ok: bool
    landbot_configured: bool
    airtable_configured: bool
    shopify_configured: bool
    zapier_configured: bool
    airtable_reachable: bool
    shopify_reachable: bool
    zapier_reachable: bool
    airtable_table: str | None = None
    shopify_store_domain: str | None = None
    notes: list[str] = Field(default_factory=list)
