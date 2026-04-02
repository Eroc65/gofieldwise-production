from pydantic import BaseModel, ConfigDict
from typing import Optional

class TechnicianBase(BaseModel):
    name: str

class TechnicianCreate(TechnicianBase):
    pass

class TechnicianUpdate(TechnicianBase):
    pass

class TechnicianOut(TechnicianBase):
    id: int
    organization_id: int
    model_config = ConfigDict(from_attributes=True)
