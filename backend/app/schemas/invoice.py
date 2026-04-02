from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class InvoiceCreate(BaseModel):
    amount: float
    job_id: int
    due_at: Optional[datetime] = None
    due_in_days: int = 7


class InvoiceStatusUpdate(BaseModel):
    status: str  # unpaid | paid | void


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: float
    status: str
    issued_at: datetime
    due_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    payment_reminder_stage: str
    job_id: int
    organization_id: int
