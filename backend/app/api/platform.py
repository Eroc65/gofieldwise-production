from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user, normalize_user_role
from ..core.db import get_db
from ..models.core import CoachingSnippet, HelpArticle, Organization, User
from ..schemas.platform import (
    AIGuideSettingsOut,
    AIGuideSettingsUpdate,
    CoachingSnippetCreate,
    CoachingSnippetOut,
    HelpArticleCreate,
    HelpArticleOut,
    MarketingServicePackageOut,
)

router = APIRouter()

_ALLOWED_ADMIN_ROLES = {"owner", "admin"}


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
