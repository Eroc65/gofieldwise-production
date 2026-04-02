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

class JobOut(JobBase):
    id: int
    organization_id: int
    completed_at: Optional[datetime] = None
    completion_notes: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
