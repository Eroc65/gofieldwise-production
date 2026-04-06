from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MarketingCampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="review_harvester")
    channel: str = Field(default="sms")
    template: Optional[str] = None
    lookback_days: int = Field(default=90, ge=7, le=730)


class MarketingCampaignOut(BaseModel):
    id: int
    name: str
    kind: str
    status: str
    channel: str
    template: Optional[str] = None
    lookback_days: int
    launched_at: Optional[datetime] = None
    organization_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MarketingCampaignLaunchOut(BaseModel):
    campaign_id: int
    status: str
    generated_recipients: int
