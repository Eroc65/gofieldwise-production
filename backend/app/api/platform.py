from datetime import datetime, timezone
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user, normalize_user_role
from ..core.db import get_db
from ..models.core import CoachingSnippet, CommunicationTenantProfile, HelpArticle, Organization, Reminder, SmsOptOut, User
from ..schemas.platform import (
    AIGuideSettingsOut,
    AIGuideSettingsUpdate,
    CoachingSnippetCreate,
    CoachingSnippetOut,
    HelpArticleCreate,
    HelpArticleOut,
    MarketingServicePackageOut,
    CommunicationTenantProfileOut,
    CommunicationTenantProfileUpdate,
    TwilioInboundMessageIn,
    TwilioStatusEventIn,
)

router = APIRouter()

_ALLOWED_ADMIN_ROLES = {"owner", "admin"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _ensure_admin(user: User) -> None:
    role = normalize_user_role(cast(str | None, user.role))
    if role not in _ALLOWED_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Role cannot manage platform settings")


@router.get("/status")
def public_status() -> dict:
    return {
        "service": "frontdesk-pro",
        "status": "ok",
        "features": {
            "ai_guide": True,
            "contextual_help": True,
            "tribal_coaching": True,
            "marketing_service_packages": True,
        },
    }


@router.get("/org/ai-guide", response_model=AIGuideSettingsOut)
def get_ai_guide_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return {
        "organization_id": int(cast(int, org.id)),
        "enabled": bool(int(cast(int, org.ai_guide_enabled))),
        "stage": str(cast(str, org.ai_guide_stage)),
    }


@router.patch("/org/ai-guide", response_model=AIGuideSettingsOut)
def update_ai_guide_settings(
    payload: AIGuideSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    org = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    setattr(org, "ai_guide_enabled", 1 if payload.enabled else 0)
    setattr(org, "ai_guide_stage", payload.stage.strip().lower())
    db.commit()
    db.refresh(org)

    return {
        "organization_id": int(cast(int, org.id)),
        "enabled": bool(int(cast(int, org.ai_guide_enabled))),
        "stage": str(cast(str, org.ai_guide_stage)),
    }


@router.get("/help/articles", response_model=list[HelpArticleOut])
def list_help_articles(
    context_key: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(HelpArticle).filter(HelpArticle.organization_id == current_user.organization_id)
    if context_key:
        q = q.filter(HelpArticle.context_key == context_key)
    return q.order_by(HelpArticle.updated_at.desc(), HelpArticle.id.desc()).all()


@router.post("/help/articles", response_model=HelpArticleOut, status_code=status.HTTP_201_CREATED)
def create_help_article(
    payload: HelpArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)

    slug = payload.slug.strip().lower()
    existing = (
        db.query(HelpArticle)
        .filter(
            HelpArticle.organization_id == current_user.organization_id,
            HelpArticle.slug == slug,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Help article slug already exists")

    article = HelpArticle(
        slug=slug,
        title=payload.title.strip(),
        category=payload.category.strip().lower(),
        context_key=payload.context_key.strip().lower(),
        body=payload.body.strip(),
        organization_id=int(cast(int, current_user.organization_id)),
    )
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@router.get("/coaching/snippets", response_model=list[CoachingSnippetOut])
def list_coaching_snippets(
    trade: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(CoachingSnippet).filter(CoachingSnippet.organization_id == current_user.organization_id)
    if trade:
        q = q.filter(CoachingSnippet.trade == trade.strip().lower())
    return q.order_by(CoachingSnippet.updated_at.desc(), CoachingSnippet.id.desc()).all()


@router.post("/coaching/snippets", response_model=CoachingSnippetOut, status_code=status.HTTP_201_CREATED)
def create_coaching_snippet(
    payload: CoachingSnippetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    snippet = CoachingSnippet(
        title=payload.title.strip(),
        trade=payload.trade.strip().lower(),
        issue_pattern=payload.issue_pattern.strip(),
        senior_tip=payload.senior_tip.strip(),
        checklist=(payload.checklist.strip() if payload.checklist else None),
        organization_id=int(cast(int, current_user.organization_id)),
    )
    db.add(snippet)
    db.commit()
    db.refresh(snippet)
    return snippet


@router.get("/marketing/service-packages", response_model=list[MarketingServicePackageOut])
def list_marketing_service_packages(
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    return [
        {
            "code": "phase_b_starter",
            "name": "Done-for-You Marketing Starter",
            "monthly_price_usd": 500,
            "summary": "Managed local campaign setup and weekly optimizations.",
            "includes": [
                "Meta ad account setup",
                "Lead form tracking with UTM attribution",
                "Weekly budget and CPL review",
            ],
        },
        {
            "code": "phase_b_growth",
            "name": "Done-for-You Marketing Growth",
            "monthly_price_usd": 750,
            "summary": "Managed campaign operations with multi-channel optimization.",
            "includes": [
                "Meta and search campaign management",
                "Lead quality review loop",
                "Biweekly performance reporting",
            ],
        },
    ]


@router.get("/org/comm-profile", response_model=CommunicationTenantProfileOut)
def get_comm_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = (
        db.query(CommunicationTenantProfile)
        .filter(CommunicationTenantProfile.organization_id == current_user.organization_id)
        .first()
    )
    if not profile:
        return {
            "organization_id": int(cast(int, current_user.organization_id)),
            "active": False,
            "twilio_account_sid": None,
            "twilio_messaging_service_sid": None,
            "twilio_phone_number": None,
            "retell_agent_id": None,
            "retell_phone_number": None,
        }
    return {
        "organization_id": int(cast(int, profile.organization_id)),
        "active": bool(int(cast(int, profile.active))),
        "twilio_account_sid": cast(str | None, profile.twilio_account_sid),
        "twilio_messaging_service_sid": cast(str | None, profile.twilio_messaging_service_sid),
        "twilio_phone_number": cast(str | None, profile.twilio_phone_number),
        "retell_agent_id": cast(str | None, profile.retell_agent_id),
        "retell_phone_number": cast(str | None, profile.retell_phone_number),
    }


@router.patch("/org/comm-profile", response_model=CommunicationTenantProfileOut)
def update_comm_profile(
    payload: CommunicationTenantProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    org_id = int(cast(int, current_user.organization_id))

    profile = (
        db.query(CommunicationTenantProfile)
        .filter(CommunicationTenantProfile.organization_id == org_id)
        .first()
    )
    if not profile:
        profile = CommunicationTenantProfile(organization_id=org_id)
        db.add(profile)
        db.flush()

    setattr(profile, "active", 1 if payload.active else 0)
    setattr(profile, "twilio_account_sid", payload.twilio_account_sid)
    setattr(profile, "twilio_auth_token", payload.twilio_auth_token)
    setattr(profile, "twilio_messaging_service_sid", payload.twilio_messaging_service_sid)
    setattr(profile, "twilio_phone_number", payload.twilio_phone_number)
    setattr(profile, "retell_agent_id", payload.retell_agent_id)
    setattr(profile, "retell_phone_number", payload.retell_phone_number)
    db.commit()
    db.refresh(profile)

    return {
        "organization_id": int(cast(int, profile.organization_id)),
        "active": bool(int(cast(int, profile.active))),
        "twilio_account_sid": cast(str | None, profile.twilio_account_sid),
        "twilio_messaging_service_sid": cast(str | None, profile.twilio_messaging_service_sid),
        "twilio_phone_number": cast(str | None, profile.twilio_phone_number),
        "retell_agent_id": cast(str | None, profile.retell_agent_id),
        "retell_phone_number": cast(str | None, profile.retell_phone_number),
    }


@router.post("/integrations/twilio/inbound/{org_id}")
def twilio_inbound_message(
    org_id: int,
    payload: TwilioInboundMessageIn,
    db: Session = Depends(get_db),
):
    normalized_phone = payload.from_phone.strip()
    text = payload.body.strip().upper()
    if text in {"STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}:
        existing = (
            db.query(SmsOptOut)
            .filter(SmsOptOut.organization_id == org_id, SmsOptOut.phone == normalized_phone)
            .first()
        )
        if not existing:
            db.add(SmsOptOut(organization_id=org_id, phone=normalized_phone, source="twilio_inbound_stop"))
            db.commit()
        return {"ok": True, "action": "opted_out"}

    if text == "HELP":
        return {"ok": True, "action": "help_requested"}

    return {"ok": True, "action": "message_received"}


@router.post("/integrations/twilio/status")
def twilio_message_status(
    payload: TwilioStatusEventIn,
    db: Session = Depends(get_db),
):
    reminder = (
        db.query(Reminder)
        .filter(Reminder.external_message_id == payload.message_sid)
        .first()
    )
    if not reminder:
        return {"ok": True, "matched": False}

    status = payload.message_status.strip().lower()
    if status in {"delivered", "sent"}:
        if cast(object, reminder.delivered_at) is None:
            setattr(reminder, "delivered_at", cast(object, reminder.sent_at) or _utcnow())
    if status in {"failed", "undelivered"}:
        setattr(reminder, "last_dispatch_error", f"delivery_status={status}")
        db.add(
            Reminder(
                message=(
                    f"ALERT: Twilio delivery failed for reminder #{int(cast(int, reminder.id))} "
                    f"with status={status}"
                ),
                channel="internal",
                status="pending",
                due_at=_utcnow(),
                organization_id=int(cast(int, reminder.organization_id)),
                customer_id=cast(int | None, reminder.customer_id),
            )
        )
    if status in {"received", "read"}:
        if cast(object, reminder.responded_at) is None:
            setattr(reminder, "responded_at", cast(object, reminder.sent_at) or _utcnow())
    db.commit()
    return {"ok": True, "matched": True}
