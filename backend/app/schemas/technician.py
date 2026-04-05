from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional


class TechnicianBase(BaseModel):
    name: str
    availability_start_hour_utc: int = 8
    availability_end_hour_utc: int = 19
    availability_weekdays: str = "0,1,2,3,4"

    @field_validator("availability_start_hour_utc")
    @classmethod
    def validate_start_hour(cls, value: int) -> int:
        if not 0 <= value <= 23:
            raise ValueError("availability_start_hour_utc must be between 0 and 23")
        return value

    @field_validator("availability_end_hour_utc")
    @classmethod
    def validate_end_hour(cls, value: int) -> int:
        if not 1 <= value <= 24:
            raise ValueError("availability_end_hour_utc must be between 1 and 24")
        return value

    @field_validator("availability_weekdays")
    @classmethod
    def validate_weekdays(cls, value: str) -> str:
        raw_parts = [part.strip() for part in value.split(",") if part.strip()]
        if not raw_parts:
            raise ValueError("availability_weekdays must include at least one day")

        parsed: list[int] = []
        for part in raw_parts:
            if not part.isdigit():
                raise ValueError("availability_weekdays must be comma-separated integers 0-6")
            day = int(part)
            if day < 0 or day > 6:
                raise ValueError("availability_weekdays values must be between 0 and 6")
            parsed.append(day)

        if len(set(parsed)) != len(parsed):
            raise ValueError("availability_weekdays cannot contain duplicates")

        return ",".join(str(day) for day in sorted(parsed))

    @model_validator(mode="after")
    def validate_hour_window(self):
        if self.availability_start_hour_utc >= self.availability_end_hour_utc:
            raise ValueError("availability_start_hour_utc must be less than availability_end_hour_utc")
        return self

class TechnicianCreate(TechnicianBase):
    pass

class TechnicianUpdate(TechnicianBase):
    name: Optional[str] = None
    availability_start_hour_utc: Optional[int] = None
    availability_end_hour_utc: Optional[int] = None
    availability_weekdays: Optional[str] = None

    @field_validator("availability_start_hour_utc")
    @classmethod
    def validate_optional_start_hour(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if not 0 <= value <= 23:
            raise ValueError("availability_start_hour_utc must be between 0 and 23")
        return value

    @field_validator("availability_end_hour_utc")
    @classmethod
    def validate_optional_end_hour(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if not 1 <= value <= 24:
            raise ValueError("availability_end_hour_utc must be between 1 and 24")
        return value

    @field_validator("availability_weekdays")
    @classmethod
    def validate_optional_weekdays(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        raw_parts = [part.strip() for part in value.split(",") if part.strip()]
        if not raw_parts:
            raise ValueError("availability_weekdays must include at least one day")

        parsed: list[int] = []
        for part in raw_parts:
            if not part.isdigit():
                raise ValueError("availability_weekdays must be comma-separated integers 0-6")
            day = int(part)
            if day < 0 or day > 6:
                raise ValueError("availability_weekdays values must be between 0 and 6")
            parsed.append(day)

        if len(set(parsed)) != len(parsed):
            raise ValueError("availability_weekdays cannot contain duplicates")

        return ",".join(str(day) for day in sorted(parsed))

    @model_validator(mode="after")
    def validate_optional_hour_window(self):
        if self.availability_start_hour_utc is None or self.availability_end_hour_utc is None:
            return self
        if self.availability_start_hour_utc >= self.availability_end_hour_utc:
            raise ValueError("availability_start_hour_utc must be less than availability_end_hour_utc")
        return self

class TechnicianOut(TechnicianBase):
    id: int
    organization_id: int
    model_config = ConfigDict(from_attributes=True)
