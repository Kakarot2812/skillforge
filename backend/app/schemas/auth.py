import re
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupRequest(BaseModel):
    email: str = Field(..., max_length=255, description="Candidate email address")
    password: str = Field(..., min_length=8, max_length=128, description="Password (8-128 characters)")
    full_name: Optional[str] = Field(None, max_length=128, description="Candidate full name")
    target_role: Optional[str] = Field(None, max_length=128, description="Candidate target career role")

    model_config = ConfigDict(extra="forbid")

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        clean = str(v).strip().lower()
        if not clean or not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean

    @field_validator("full_name", "target_role", mode="after")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return None


class LoginRequest(BaseModel):
    email: str = Field(..., description="Candidate account email")
    password: str = Field(..., description="Plain-text password")
    remember_me: bool = Field(False, description="Extend session duration to 30 days")

    model_config = ConfigDict(extra="forbid")

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return str(v).strip().lower()


class UserAuthResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    target_role: Optional[str] = None
    auth_provider: str
    is_active: bool
    active_resume_id: Optional[UUID] = None
    connected_github_username: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LogoutResponse(BaseModel):
    message: str = "Logged out successfully"

    model_config = ConfigDict(extra="forbid")
