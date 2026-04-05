from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional

class CustomerBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerUpdate(CustomerBase):
    pass

class CustomerOut(CustomerBase):
    id: int
    organization_id: int
    model_config = ConfigDict(from_attributes=True)
