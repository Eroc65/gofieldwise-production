from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AIGuideSettingsUpdate(BaseModel):
    enabled: bool
    stage: str = Field(default="onboarding", min_length=2, max_length=40)


class AIGuideSettingsOut(BaseModel):
    organization_id: int
    enabled: bool
    stage: str


class HelpArticleCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=140)
    category: str = Field(default="general", min_length=2, max_length=40)
    context_key: str = Field(default="general", min_length=2, max_length=60)
    body: str = Field(min_length=10)


class HelpArticleOut(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    context_key: str
    body: str
    organization_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CoachingSnippetCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    trade: str = Field(default="general", min_length=2, max_length=40)
    issue_pattern: str = Field(min_length=4, max_length=200)
    senior_tip: str = Field(min_length=10)
    checklist: Optional[str] = None


class CoachingSnippetOut(BaseModel):
    id: int
    title: str
    trade: str
    issue_pattern: str
    senior_tip: str
    checklist: Optional[str] = None
    organization_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MarketingServicePackageOut(BaseModel):
    code: str
    name: str
    monthly_price_usd: int
    summary: str
    includes: list[str]
