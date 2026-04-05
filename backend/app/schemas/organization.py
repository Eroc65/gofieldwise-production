from pydantic import BaseModel, ConfigDict

class OrganizationOut(BaseModel):
    id: int
    name: str
    intake_key: str
    model_config = ConfigDict(from_attributes=True)
