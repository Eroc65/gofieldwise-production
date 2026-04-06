from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

class JobBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "pending"
    scheduled_time: Optional[datetime] = None
    customer_id: int
    technician_id: Optional[int] = None

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    scheduled_time: Optional[datetime] = None
    technician_id: Optional[int] = None


class JobDispatchUpdate(BaseModel):
    scheduled_time: datetime
    technician_id: int


class JobCompletionUpdate(BaseModel):
    completion_notes: Optional[str] = None


class JobActivityOut(BaseModel):
    id: int
    action: str
    from_status: Optional[str] = None
    to_status: str
    note: Optional[str] = None
    actor_user_id: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class JobDispatchConflictOut(BaseModel):
    conflict: bool
    conflicting_job_id: Optional[int] = None
    message: str


class JobNextSlotOut(BaseModel):
    technician_id: int
    requested_time: datetime
    search_hours: int
    step_minutes: int
    next_available_time: Optional[datetime] = None
    conflicting_job_ids: list[int]

class JobOut(JobBase):
    id: int
    organization_id: int
    on_my_way_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
