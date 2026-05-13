"""
POST /api/billing/sync
────────────────────
Called by the Next.js Stripe webhook handler immediately after it writes
subscription state to Supabase, so that FastAPI's own Postgres record of
org.is_active stays in sync.

Authentication: shared secret header X-Billing-Sync-Secret.
The secret must match the env var BILLING_SYNC_SECRET (≥32 chars recommended).
Never expose this endpoint without the secret check.
"""

import hmac
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.db import get_db
from ..models.core import Organization

router = APIRouter()


class BillingSyncRequest(BaseModel):
    # FastAPI integer org_id preferred; stripe_customer_id used as fallback.
    org_id: Optional[int] = None
    stripe_customer_id: Optional[str] = None
    is_active: bool
    subscription_status: Optional[str] = None


def _verify_billing_secret(x_billing_sync_secret: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("BILLING_SYNC_SECRET", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Billing sync not configured on this server")
    if not x_billing_sync_secret:
        raise HTTPException(status_code=401, detail="Missing X-Billing-Sync-Secret header")
    # Constant-time compare to prevent timing attacks
    if not hmac.compare_digest(x_billing_sync_secret.strip(), expected.strip()):
        raise HTTPException(status_code=403, detail="Invalid billing sync secret")


@router.post("/api/billing/sync", tags=["billing"])
def billing_sync(
    payload: BillingSyncRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_billing_secret),
):
    """
    Flip org.is_active in FastAPI's Postgres to match Supabase billing state.
    Lookup order: org_id (integer PK) → stripe_customer_id metadata column.
    """
    org: Optional[Organization] = None

    if payload.org_id is not None:
        org = db.query(Organization).filter(Organization.id == payload.org_id).first()

    if org is None and payload.stripe_customer_id:
        # Organizations don't store stripe_customer_id yet in FastAPI Postgres —
        # this lookup will always return None for now. It's here so the endpoint
        # is forward-compatible when that column is added.
        pass

    if org is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Organization not found "
                f"(org_id={payload.org_id}, stripe_customer_id={payload.stripe_customer_id})"
            ),
        )

    org.is_active = payload.is_active  # type: ignore[assignment]
    db.commit()

    return {
        "ok": True,
        "org_id": org.id,
        "is_active": org.is_active,
        "subscription_status": payload.subscription_status,
    }
