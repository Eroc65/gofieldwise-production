from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReminderCreate(BaseModel):
    message: str
    channel: str = "internal"          # sms | email | call | internal
    due_at: datetime
    lead_id: Optional[int] = None
    job_id: Optional[int] = None
    customer_id: Optional[int] = None


class ReminderStatusUpdate(BaseModel):
    status: str   # pending | sent | dismissed


class ReminderRunRequest(BaseModel):
    limit: int = 50
    dry_run: bool = False


class ReminderRunResult(BaseModel):
    organization_id: int
    dry_run: bool
    candidate_count: int
    sent_count: int
    failed_count: int
    sent_ids: list[int]
    failed: list[dict]


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message: str
    channel: str
    status: str
    due_at: datetime
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    external_message_id: Optional[str] = None
    dispatch_attempts: int
    last_dispatch_error: Optional[str] = None
    lead_id: Optional[int] = None
    job_id: Optional[int] = None
    customer_id: Optional[int] = None
    organization_id: int
    created_at: datetime
    updated_at: datetime
