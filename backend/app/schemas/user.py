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

class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    organization_id: Optional[int]
    model_config = ConfigDict(from_attributes=True)
