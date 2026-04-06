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
from ..models.core import User
from ..schemas.marketing import MarketingCampaignCreate
from ..schemas.marketing import MarketingCampaignLaunchOut
from ..schemas.marketing import MarketingCampaignOut


router = APIRouter()


_ALLOWED_MARKETING_ROLES = {"owner", "admin", "dispatcher"}


def _ensure_marketing_access(current_user: User) -> None:
    role = normalize_user_role(cast(str | None, current_user.role))
    if role not in _ALLOWED_MARKETING_ROLES:
        raise HTTPException(status_code=403, detail="Role cannot manage marketing campaigns")


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
