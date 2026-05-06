from __future__ import annotations

import hmac
import os
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request

from ..schemas.external_integrations import DailyViralGoodsHealthOut, LandbotDailyViralGoodsOut
from ..services.dailyviralgoods_flow import healthcheck, normalize_landbot_payload, push_to_airtable, sync_to_shopify
from ..services.dailyviralgoods_flow import push_to_zapier


router = APIRouter()


def _expected_webhook_secret() -> str:
    return os.getenv("LANDBOT_WEBHOOK_SECRET", "").strip()


def _require_landbot_secret(request: Request) -> None:
    expected = _expected_webhook_secret()
    if not expected:
        return
    candidates = [
        request.headers.get("x-landbot-secret", "").strip(),
        request.headers.get("x-webhook-secret", "").strip(),
    ]
    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        candidates.append(auth_header.split(" ", 1)[1].strip())
    if not any(candidate and hmac.compare_digest(candidate, expected) for candidate in candidates):
        raise HTTPException(status_code=401, detail="Invalid Landbot webhook secret")


@router.get("/integrations/dailyviralgoods/health", response_model=DailyViralGoodsHealthOut)
def get_dailyviralgoods_health():
    return healthcheck()


@router.post("/integrations/landbot/dailyviralgoods/webhook", response_model=LandbotDailyViralGoodsOut)
async def landbot_dailyviralgoods_webhook(request: Request):
    _require_landbot_secret(request)
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    normalized = normalize_landbot_payload(cast(dict[str, Any], body))
    dry_run = str(request.query_params.get("dry_run", "")).strip().lower() in {"1", "true", "yes", "on"}
    if dry_run:
        return LandbotDailyViralGoodsOut(
            ok=True,
            airtable_synced=False,
            shopify_synced=False,
            zapier_triggered=False,
            summary="Dry run completed. Payload normalized successfully.",
            error=None,
        )

    airtable_ok, airtable_record_id, airtable_error = push_to_airtable(normalized)
    shopify_ok, shopify_customer_id, shopify_error = sync_to_shopify(normalized, airtable_record_id=airtable_record_id)
    zapier_ok, zapier_error = push_to_zapier(
        normalized,
        airtable_record_id=airtable_record_id,
        shopify_customer_id=shopify_customer_id,
    )

    if not airtable_ok and not shopify_ok and not zapier_ok:
        return LandbotDailyViralGoodsOut(
            ok=False,
            airtable_synced=False,
            shopify_synced=False,
            zapier_triggered=False,
            summary="Landbot payload received, but Airtable and Shopify sync both failed.",
            error="; ".join(part for part in [airtable_error, shopify_error, zapier_error] if part) or "Unknown sync failure",
        )

    summary_parts = []
    if airtable_ok:
        summary_parts.append("Airtable synced")
    if shopify_ok:
        summary_parts.append("Shopify synced")
    if zapier_ok:
        summary_parts.append("Zapier triggered")
    if not shopify_ok and shopify_error:
        summary_parts.append("Shopify skipped or failed")
    if not airtable_ok and airtable_error:
        summary_parts.append("Airtable failed")
    if not zapier_ok and zapier_error:
        summary_parts.append("Zapier skipped or failed")

    return LandbotDailyViralGoodsOut(
        ok=airtable_ok or shopify_ok or zapier_ok,
        airtable_synced=airtable_ok,
        shopify_synced=shopify_ok,
        zapier_triggered=zapier_ok,
        airtable_record_id=airtable_record_id,
        shopify_customer_id=shopify_customer_id,
        summary=". ".join(summary_parts) + ".",
        error="; ".join(part for part in [airtable_error, shopify_error, zapier_error] if part) or None,
    )
