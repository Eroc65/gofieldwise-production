from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    organization_name: Optional[str] = None
    role: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRoleUpdate(BaseModel):
    role: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    organization_id: Optional[int]
    model_config = ConfigDict(from_attributes=True)


class UserRoleAuditEventOut(BaseModel):
    id: int
    actor_user_id: int
    actor_email: Optional[EmailStr] = None
    target_user_id: int
    target_email: Optional[EmailStr] = None
    from_role: str
    to_role: str
    note: Optional[str] = None
    organization_id: int
    created_at: datetime


class UserRoleAuditListOut(BaseModel):
    organization_id: int
    total: int
    events: list[UserRoleAuditEventOut]
