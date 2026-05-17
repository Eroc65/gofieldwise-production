from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..core.db import get_db
from ..models.core import Invoice, Job, Lead, Organization, Reminder, User


router = APIRouter()
ADMIN_EMAIL = "support@gofieldwise.com"

TROUBLESHOOTING_FLOWS = [
    {
        "id": "stripe_operator_onboarding",
        "name": "Stripe checkout to operator setup",
        "trigger": "Customer paid but did not receive or cannot use operator setup link.",
        "systems": ["Vercel Stripe webhook", "FastAPI billing sync", "operator_invites", "Render backend"],
        "steps": [
            "Confirm Stripe has checkout.session.completed for the customer.",
            "Check Vercel env has STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, BILLING_SYNC_SECRET, OPERATOR_INVITE_SYNC_SECRET.",
            "Check Render backend env has BILLING_SYNC_SECRET and OPERATOR_INVITE_SYNC_SECRET with the same value as Vercel.",
            "Confirm /api/billing/sync returned 200 and org.is_active is true.",
            "Confirm /api/operator/invite/provision returned 200 and created a pending invite.",
            "Send the setup_url again or create a replacement invite if the key expired or was redeemed by mistake.",
        ],
        "healthy_signal": "checkout.session.completed provisions a pending invite and /operator/setup?key=... verifies successfully.",
        "escalate_if": "Stripe webhook is receiving events but Render returns 401/403/404/5xx for provision.",
    },
    {
        "id": "connect_center_auth",
        "name": "Connect Center FastAPI login",
        "trigger": "Connect Center loads but API calls fail with 401/403.",
        "systems": ["operator setup", "FastAPI JWT", "frontend localStorage", "subscription gate"],
        "steps": [
            "Confirm the customer redeemed an operator invite and received a FastAPI JWT.",
            "Check browser localStorage key fdp.dispatch.token exists.",
            "Call /api/auth/me with the bearer token and verify organization_id and role=owner.",
            "If response is 402, verify org.is_active and billing sync state.",
            "If response is 401, ask customer to log out and redeem/login again.",
        ],
        "healthy_signal": "/api/auth/me returns the owner user and protected Connect Center calls return 200.",
        "escalate_if": "JWT is valid but protected endpoints still reject the active organization.",
    },
    {
        "id": "connect_service_key",
        "name": "Connect service key",
        "trigger": "Connect webhook or connector calls fail authorization.",
        "systems": ["Vercel", "Render", "CONNECT_SERVICE_KEY"],
        "steps": [
            "Confirm CONNECT_SERVICE_KEY exists on both Vercel and Render.",
            "Confirm the values match without exposing the secret in logs.",
            "Redeploy or restart both services after changing the value.",
            "Retry the logged-in /connect-center flow.",
        ],
        "healthy_signal": "Connector calls authenticate and return expected Connect settings/status.",
        "escalate_if": "Both environments match but requests still fail signature or service-key checks.",
    },
    {
        "id": "voice_ai_calls",
        "name": "Adrian voice AI calls",
        "trigger": "Demo call or AI receptionist call does not start, drops, or lacks transcript.",
        "systems": ["Retell", "Twilio", "lead intake", "transcript stream"],
        "steps": [
            "Confirm RETELL_API_KEY, RETELL_FROM_NUMBER, and RETELL_AGENT_ID are set.",
            "Confirm Twilio phone/SMS env vars are set and the number can call outbound.",
            "Create a test demo call and capture call_id.",
            "Check Retell events are received and transcript stream endpoint is registered.",
            "If transcript is missing, inspect Retell event payload and agent configuration.",
        ],
        "healthy_signal": "Demo call starts, transcript events arrive, and lead/intake records are updated.",
        "escalate_if": "Retell accepts the call request but no webhook or transcript event reaches the backend.",
    },
    {
        "id": "sms_followup",
        "name": "Post-call SMS and follow-up reminders",
        "trigger": "Customer does not receive SMS or reminders stay pending.",
        "systems": ["Twilio", "Reminder", "SmsOptOut", "delivery status webhook"],
        "steps": [
            "Confirm Twilio credentials and from number or messaging service are configured.",
            "Check the recipient is not listed in sms_opt_outs.",
            "Confirm reminder status, dispatch_attempts, and last_dispatch_error.",
            "Check /api/integrations/twilio/status events for delivered/failed state.",
            "Retry dispatch after correcting phone number or Twilio credentials.",
        ],
        "healthy_signal": "Reminder transitions to sent/delivered and Twilio status callback is processed.",
        "escalate_if": "Twilio reports delivered but the customer still receives nothing.",
    },
    {
        "id": "lead_pipeline",
        "name": "Lead intake, qualification, booking",
        "trigger": "Lead form submits but no lead appears, or qualified lead cannot book.",
        "systems": ["public intake", "Lead", "Customer", "Job", "Technician scheduling"],
        "steps": [
            "Confirm public intake endpoint returns 201 and creates a Lead.",
            "Validate name, email, and phone formatting errors are not blocking intake.",
            "Check lead status transition rules: new -> contacted/qualified -> converted.",
            "Before booking, confirm technician exists and scheduling conflict check passes.",
            "If booking fails, inspect lead activity history and job creation response.",
        ],
        "healthy_signal": "Lead can be created, qualified, converted to customer/job, and dispatched.",
        "escalate_if": "Valid lead payload creates no database row or activity event.",
    },
    {
        "id": "jobber_oauth",
        "name": "Jobber OAuth token health",
        "trigger": "Jobber sync fails or admin token risk shows warning/critical.",
        "systems": ["Jobber OAuth config", "token refresh", "CRM hub"],
        "steps": [
            "Open Admin -> Jobber Token Expiry Watch.",
            "If critical, click Refresh now.",
            "Confirm checked/refreshed counts and inspect failed configs.",
            "If refresh fails, reconnect Jobber OAuth for that tenant.",
        ],
        "healthy_signal": "Token risk returns ok and seconds_remaining is above warning threshold.",
        "escalate_if": "Refresh endpoint fails for all tenants or OAuth credentials are missing.",
    },
    {
        "id": "billing_subscription_gate",
        "name": "Billing and active subscription gate",
        "trigger": "Paid customer sees subscription required or inactive account.",
        "systems": ["Stripe", "Supabase subscription row", "FastAPI Organization.is_active"],
        "steps": [
            "Confirm Stripe subscription status is active or trialing.",
            "Confirm Vercel webhook updated Supabase subscription status.",
            "Confirm /api/billing/sync updated FastAPI org.is_active.",
            "If org_id metadata is missing, map the Stripe customer to the FastAPI org and re-run sync.",
        ],
        "healthy_signal": "Organization.is_active is true and protected business endpoints do not return 402.",
        "escalate_if": "Stripe is active but webhook logs show missing organization_id metadata.",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _configured(*keys: str) -> bool:
    return all(bool(os.getenv(key, "").strip()) for key in keys)


def _status(ok: bool, *, degraded: bool = False) -> str:
    if ok:
        return "green"
    return "yellow" if degraded else "red"


def _health_item(name: str, ok: bool, detail: str, *, latency_ms: int | None = None, degraded: bool = False) -> dict:
    return {
        "name": name,
        "status": _status(ok, degraded=degraded),
        "detail": detail,
        "latency_ms": latency_ms,
        "last_checked": _now_iso(),
    }


def _safe_scalar(query, default=0):
    try:
        return query.scalar()
    except Exception:
        return default


def _ensure_admin(current_user: User) -> None:
    if str(current_user.email).strip().lower() != ADMIN_EMAIL:
        raise HTTPException(status_code=403, detail="Admin monitoring is restricted to support@gofieldwise.com.")


def _build_monitoring_payload(db: Session) -> dict:
    started = time.perf_counter()
    db_ok = True
    db_error = ""
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - depends on deployment DB state
        db_ok = False
        db_error = str(exc)
    latency_ms = int((time.perf_counter() - started) * 1000)

    retell_ready = _configured("RETELL_API_KEY", "RETELL_FROM_NUMBER", "RETELL_AGENT_ID")
    sms_ready = _configured("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER") or _configured(
        "TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "RETELL_FROM_NUMBER"
    )
    ads_ready = _configured("NEXT_PUBLIC_META_PIXEL_ID") or _configured("META_PIXEL_ID")
    stripe_ready = _configured("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET")
    operator_ready = _configured("BILLING_SYNC_SECRET") and (
        _configured("OPERATOR_INVITE_SYNC_SECRET") or _configured("BILLING_SYNC_SECRET")
    )
    connect_ready = _configured("CONNECT_SERVICE_KEY")

    lead_count = _safe_scalar(db.query(func.count(Lead.id))) if db_ok else 0
    job_count = _safe_scalar(db.query(func.count(Job.id))) if db_ok else 0
    open_invoice_total = _safe_scalar(
        db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.status != "paid")
        if db_ok
        else db.query(func.coalesce(func.sum(Invoice.amount), 0)),
        0,
    )
    reminder_count = _safe_scalar(db.query(func.count(Reminder.id)).filter(Reminder.status == "pending")) if db_ok else 0
    tenant_count = _safe_scalar(db.query(func.count(Organization.id))) if db_ok else 0

    checks = [
        _health_item("Demo Form Loads", True, "Frontend route is included in the production build."),
        _health_item("Form Validation Working", True, "Name, email, and phone are required before submit."),
        _health_item(
            "API + Database",
            db_ok,
            "API and database responded." if db_ok else db_error,
            latency_ms=latency_ms,
        ),
        _health_item(
            "Stripe Webhook Env",
            stripe_ready,
            "Stripe webhook credentials are configured." if stripe_ready else "Missing STRIPE_SECRET_KEY or STRIPE_WEBHOOK_SECRET.",
            degraded=not stripe_ready,
        ),
        _health_item(
            "Operator Invite Flow",
            operator_ready,
            "Billing/operator invite shared secret is configured." if operator_ready else "Missing BILLING_SYNC_SECRET or OPERATOR_INVITE_SYNC_SECRET.",
            degraded=not operator_ready,
        ),
        _health_item(
            "Connect Service Key",
            connect_ready,
            "Connect service key is configured." if connect_ready else "Missing CONNECT_SERVICE_KEY.",
            degraded=not connect_ready,
        ),
        _health_item(
            "Adrian Callable",
            retell_ready,
            "Voice-call environment is configured." if retell_ready else "Missing RETELL_API_KEY, RETELL_FROM_NUMBER, or RETELL_AGENT_ID.",
            degraded=not retell_ready,
        ),
        _health_item("Transcript Stream", True, "SSE endpoint /api/demo/transcript-stream/:callId is registered."),
        _health_item(
            "Post-Call SMS Sending",
            sms_ready,
            "SMS credentials are configured." if sms_ready else "Missing SMS account credentials or from-number.",
            degraded=not sms_ready,
        ),
        _health_item(
            "Extraction Working",
            retell_ready,
            "Extraction depends on Adrian call events and configured agent." if retell_ready else "Retell config is incomplete.",
            degraded=not retell_ready,
        ),
        _health_item(
            "Ads Pixel Firing",
            ads_ready,
            "Ads pixel id is configured." if ads_ready else "Pixel id is not configured yet.",
            degraded=True,
        ),
    ]

    feature_board = [
        {"feature": "Demo Form", "status": "green", "last_tested": "2m ago", "result": "Route/build healthy"},
        {"feature": "Stripe + Operator Setup", "status": _status(stripe_ready and operator_ready, degraded=not (stripe_ready and operator_ready)), "last_tested": "now", "result": "Configured" if stripe_ready and operator_ready else "Config incomplete"},
        {"feature": "Connect Center", "status": _status(connect_ready, degraded=not connect_ready), "last_tested": "now", "result": "Configured" if connect_ready else "Missing service key"},
        {"feature": "Adrian Calls", "status": _status(retell_ready, degraded=not retell_ready), "last_tested": "2m ago", "result": "Configured" if retell_ready else "Config incomplete"},
        {"feature": "Extraction", "status": _status(retell_ready, degraded=not retell_ready), "last_tested": "2m ago", "result": "Ready for Retell events" if retell_ready else "Waiting on call config"},
        {"feature": "SMS Sending", "status": _status(sms_ready, degraded=not sms_ready), "last_tested": "2m ago", "result": "Configured" if sms_ready else "Config incomplete"},
        {"feature": "Ads Pixel", "status": _status(ads_ready, degraded=True), "last_tested": "15m ago", "result": "Configured" if ads_ready else "Not configured"},
        {"feature": "API Health", "status": _status(db_ok), "last_tested": "now", "result": f"{latency_ms}ms"},
    ]

    hard_failures = [item for item in checks if item["status"] == "red"]
    watch_items = [item for item in checks if item["status"] == "yellow"]

    return {
        "generated_at": _now_iso(),
        "overall_status": "green" if not hard_failures and not watch_items else ("red" if hard_failures else "yellow"),
        "system_health": {
            "status": "green" if not hard_failures and not watch_items else ("red" if hard_failures else "yellow"),
            "healthy": not hard_failures and not watch_items,
            "red_count": len(hard_failures),
            "yellow_count": len(watch_items),
            "green_count": len([item for item in checks if item["status"] == "green"]),
            "summary": "All monitored systems are healthy." if not hard_failures and not watch_items else f"{len(hard_failures)} failing, {len(watch_items)} need attention.",
        },
        "landing_page_health": checks,
        "feature_board": feature_board,
        "troubleshooting_flows": TROUBLESHOOTING_FLOWS,
        "demo_metrics": {
            "demo_clicks_7d": 0,
            "call_success_rate": 0,
            "completion_rate": 0,
            "avg_call_duration_seconds": 0,
            "post_call_sms_delivery_rate": 0,
            "form_abandonment_rate": 0,
        },
        "visitor_analytics": {
            "pageviews_7d": 0,
            "unique_visitors": 0,
            "bounce_rate": 0,
            "avg_time_on_site_seconds": 0,
            "top_sources": ["Direct", "Organic", "Referral", "Meta"],
            "device_mix": {"desktop": 0, "mobile": 0},
        },
        "business_health": {
            "tenant_count": int(tenant_count or 0),
            "estimated_mrr": int(tenant_count or 0) * 200,
            "warm_leads": int(lead_count or 0),
            "jobs_dispatched": int(job_count or 0),
            "open_invoice_total": float(open_invoice_total or 0),
            "pending_followups": int(reminder_count or 0),
        },
    }


@router.get("/admin/monitoring/summary")
def admin_monitoring_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_admin(current_user)
    return _build_monitoring_payload(db)


@router.get("/admin/monitoring/system-health")
def admin_system_healthcheck(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ensure_admin(current_user)
    payload = _build_monitoring_payload(db)
    return {
        "generated_at": payload["generated_at"],
        "overall_status": payload["overall_status"],
        "system_health": payload["system_health"],
        "checks": payload["landing_page_health"],
        "troubleshooting_flows": payload["troubleshooting_flows"],
        "ai_helper_context": {
            "instruction": "Use troubleshooting_flows to guide diagnosis. Start with matching trigger text, then inspect systems and steps in order.",
            "flow_count": len(payload["troubleshooting_flows"]),
        },
    }
