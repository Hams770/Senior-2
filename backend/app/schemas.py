import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Register(BaseModel):
    email: str
    password: str = Field(min_length=8)
    full_name: str = ""

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        if not EMAIL.match(v):
            raise ValueError("Invalid email")
        return v.lower()


class StaffCreate(Register):
    role: str = "hr"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: str


class JobIn(BaseModel):
    title: str = Field(min_length=2)
    description: str = Field(min_length=10)
    required_skills: list[str] = []
    level: str = ""
    deadline: datetime | None = None


class JobUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    required_skills: list[str] | None = None
    level: str | None = None
    deadline: datetime | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    title: str
    description: str
    required_skills: list[str]
    level: str
    deadline: datetime | None
    status: str


class PolicyIn(BaseModel):
    weights: dict[str, float]


class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    version: int
    weights: dict[str, float]
    created_at: datetime


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    candidate_id: int
    status: str
    created_at: datetime


class ScoreIn(BaseModel):
    components: dict[str, float | None]
    weights: dict[str, float]


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int | None
    action: str
    entity: str
    entity_id: int | None
    detail: dict
    created_at: datetime
