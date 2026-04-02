from typing import Optional
from pydantic import BaseModel

class Organization(BaseModel):
    id: int
    name: str
