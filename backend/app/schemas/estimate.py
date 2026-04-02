from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EstimateCreate(BaseModel):
    amount: float
    description: Optional[str] = None
    job_id: int


class EstimateStatusUpdate(BaseModel):
    status: str  # sent | approved | rejected


class EstimateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: float
    description: Optional[str] = None
    status: str
    issued_at: datetime
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    job_id: int
    organization_id: int
