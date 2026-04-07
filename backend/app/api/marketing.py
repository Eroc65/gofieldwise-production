from typing import List, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..api.auth import get_current_user
from ..api.auth import normalize_user_role
from ..core.db import get_db
from ..crud.marketing import create_campaign
from ..crud.marketing import get_campaign
from ..crud.marketing import launch_campaign
from ..crud.marketing import list_campaigns
from ..crud.reminder import run_reactivation_engine
from ..models.core import User
from ..schemas.marketing import MarketingCampaignCreate
from ..schemas.marketing import MarketingCampaignLaunchOut
from ..schemas.marketing import MarketingCampaignOut
from ..schemas.marketing import MarketingImageGenerateOut
from ..schemas.marketing import MarketingImageGenerateRequest
from ..schemas.marketing import MarketingImageChannelOut
from ..schemas.marketing import MarketingImageTemplateOut
from ..schemas.marketing import MarketingImageTradeTemplateOut
from ..schemas.marketing import ReactivationRunOut
from ..schemas.marketing import ReactivationRunRequest
from ..services.ai_image_service import generate_marketing_image


router = APIRouter()


_ALLOWED_MARKETING_ROLES = {"owner", "admin", "dispatcher"}
_MARKETING_IMAGE_TEMPLATES: list[dict[str, str]] = [
    {
        "code": "social_promo",
        "name": "Social Promo",
        "recommended_size": "1024x1024",
        "description": "General social ad creative with offer headline and clear CTA",
    },
    {
        "code": "seasonal_offer",
        "name": "Seasonal Offer",
        "recommended_size": "1536x1024",
        "description": "Landscape campaign image for seasonal promotions and bundles",
    },
    {
        "code": "review_push",
        "name": "Review Push",
        "recommended_size": "1024x1024",
        "description": "Review and reputation campaign creative with trust cues",
    },
    {
        "code": "reactivation_offer",
        "name": "Reactivation Offer",
        "recommended_size": "1024x1536",
        "description": "Portrait creative for win-back and dormant customer outreach",
    },
]
_MARKETING_IMAGE_CHANNELS: list[dict[str, str]] = [
    {
        "code": "instagram_feed",
        "name": "Instagram Feed",
        "recommended_size": "1024x1024",
        "description": "Square layout optimized for social feed posts",
    },
    {
        "code": "facebook_landscape",
        "name": "Facebook Landscape",
        "recommended_size": "1536x1024",
        "description": "Landscape layout optimized for Facebook ads and boosted posts",
    },
    {
        "code": "story_vertical",
        "name": "Story Vertical",
        "recommended_size": "1024x1536",
        "description": "Vertical creative for stories and mobile-first placements",
    },
]
_MARKETING_IMAGE_TRADE_TEMPLATES: list[dict[str, str]] = [
    {
        "code": "general_home_services",
        "name": "General Home Services",
        "description": "Practical, trustworthy home service visual style with clean iconography",
    },
    {
        "code": "hvac",
        "name": "HVAC",
        "description": "Heating and cooling visuals, seasonal comfort messaging, reliability-first tone",
    },
    {
        "code": "plumbing",
        "name": "Plumbing",
        "description": "Fast-response plumbing visuals, urgency + trust, clear service promise",
    },
    {
        "code": "electrical",
        "name": "Electrical",
        "description": "Professional electrical service visuals with safety-focused messaging",
    },
]


def _ensure_marketing_access(current_user: User) -> None:
    role = normalize_user_role(cast(str | None, current_user.role))
    if role not in _ALLOWED_MARKETING_ROLES:
        raise HTTPException(status_code=403, detail="Role cannot manage marketing campaigns")


def _compose_marketing_prompt(payload: MarketingImageGenerateRequest) -> str:
    template = next((item for item in _MARKETING_IMAGE_TEMPLATES if item["code"] == payload.template_code), None)
    if not template:
        allowed = ", ".join(item["code"] for item in _MARKETING_IMAGE_TEMPLATES)
        raise HTTPException(status_code=400, detail=f"template_code must be one of: {allowed}")

    channel = next((item for item in _MARKETING_IMAGE_CHANNELS if item["code"] == payload.channel_code), None)
    if not channel:
        allowed = ", ".join(item["code"] for item in _MARKETING_IMAGE_CHANNELS)
        raise HTTPException(status_code=400, detail=f"channel_code must be one of: {allowed}")

    trade_template = next((item for item in _MARKETING_IMAGE_TRADE_TEMPLATES if item["code"] == payload.trade_code), None)
    if not trade_template:
        allowed = ", ".join(item["code"] for item in _MARKETING_IMAGE_TRADE_TEMPLATES)
        raise HTTPException(status_code=400, detail=f"trade_code must be one of: {allowed}")

    service_type = (payload.service_type or "home service").strip()
    business_name = (payload.business_name or "local business").strip()
    offer_text = (payload.offer_text or "Limited-time savings").strip()
    cta_text = (payload.cta_text or "Book today").strip()
    primary_color = (payload.primary_color or "#0f172a").strip()

    guardrails = (
        "Design must be conversion-focused and mobile-friendly. "
        "Use bold, high-contrast typography. "
        "Do not include logos, trademarks, or copyrighted characters. "
        "Do not include photo-real likenesses of real people."
    )

    return (
        f"Template: {template['name']}. "
        f"Channel: {channel['name']} ({channel['recommended_size']}). "
        f"Trade style: {trade_template['name']} - {trade_template['description']}. "
        f"Create a marketing image for {business_name} in the {service_type} industry. "
        f"Primary offer text: {offer_text}. CTA text: {cta_text}. "
        f"Primary color: {primary_color}. "
        f"User prompt guidance: {payload.prompt.strip()}. "
        f"{guardrails}"
    )


@router.get("/marketing/ai-images/templates", response_model=List[MarketingImageTemplateOut])
def list_marketing_image_templates(
    current_user: User = Depends(get_current_user),
):
    _ensure_marketing_access(current_user)
    return _MARKETING_IMAGE_TEMPLATES


@router.get("/marketing/ai-images/channels", response_model=List[MarketingImageChannelOut])
def list_marketing_image_channels(
    current_user: User = Depends(get_current_user),
):
    _ensure_marketing_access(current_user)
    return _MARKETING_IMAGE_CHANNELS


@router.get("/marketing/ai-images/trade-templates", response_model=List[MarketingImageTradeTemplateOut])
def list_marketing_image_trade_templates(
    current_user: User = Depends(get_current_user),
):
    _ensure_marketing_access(current_user)
    return _MARKETING_IMAGE_TRADE_TEMPLATES


@router.get("/marketing/campaigns", response_model=List[MarketingCampaignOut])
def list_marketing_campaigns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_marketing_access(current_user)
    return list_campaigns(db, int(cast(int, current_user.organization_id)))


@router.post("/marketing/campaigns", response_model=MarketingCampaignOut, status_code=status.HTTP_201_CREATED)
def create_marketing_campaign(
    payload: MarketingCampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_marketing_access(current_user)
    return create_campaign(db, payload.model_dump(), int(cast(int, current_user.organization_id)))


@router.post("/marketing/campaigns/{campaign_id}/launch", response_model=MarketingCampaignLaunchOut)
def launch_marketing_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_marketing_access(current_user)
    campaign = get_campaign(db, campaign_id, int(cast(int, current_user.organization_id)))
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    generated = launch_campaign(db, campaign)
    return {
        "campaign_id": campaign.id,
        "status": campaign.status,
        "generated_recipients": generated,
    }


@router.post("/marketing/reactivation/run", response_model=ReactivationRunOut)
def run_reactivation_engine_api(
    payload: ReactivationRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_marketing_access(current_user)
    org_id = int(cast(int, current_user.organization_id))
    return run_reactivation_engine(
        db,
        organization_id=org_id,
        lookback_days=payload.lookback_days,
        limit=payload.limit,
        dry_run=payload.dry_run,
    )


@router.post("/marketing/ai-images/generate", response_model=MarketingImageGenerateOut)
def generate_marketing_image_api(
    payload: MarketingImageGenerateRequest,
    current_user: User = Depends(get_current_user),
):
    _ensure_marketing_access(current_user)
    composed_prompt = _compose_marketing_prompt(payload)
    try:
        image = generate_marketing_image(
            prompt=composed_prompt,
            size=payload.size,
            quality=payload.quality,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "model": image.model,
        "mime_type": image.mime_type,
        "image_base64": image.image_base64,
        "revised_prompt": image.revised_prompt,
    }
