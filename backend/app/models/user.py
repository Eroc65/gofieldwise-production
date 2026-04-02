from typing import Optional
from pydantic import BaseModel

class User(BaseModel):
    id: int
    email: str
    hashed_password: str
    organization_id: Optional[int]
