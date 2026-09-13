"""
Pydantic Schemas for Candidate User Profile.
Phase: Persistent Personalization Architecture (Checkpoint 4: User Profile Foundation).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator


class UserProfileBase(BaseModel):
    """Base schema for candidate profile fields."""
    name: Optional[str] = None
    education: Optional[str] = None
    college: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None

    @field_validator(
        "name",
        "education",
        "college",
        "degree",
        "branch",
        "target_role",
        "experience_level",
        mode="before",
    )
    @classmethod
    def validate_and_strip_string(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Field must be a string.")
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace only if provided.")
        return cleaned

    @field_validator("semester")
    @classmethod
    def validate_positive_semester(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if v <= 0:
            raise ValueError("semester must be a positive integer (greater than 0).")
        return v


class UserProfileCreate(UserProfileBase):
    """
    Schema for creating a candidate user profile.
    user_id is strictly forbidden in the request body to enforce trusted header auth.
    """
    model_config = ConfigDict(extra="forbid")


class UserProfileUpdate(BaseModel):
    """
    Schema for updating an existing candidate user profile (partial update semantics).
    All fields are optional; fields omitted will remain untouched.
    """
    name: Optional[str] = None
    education: Optional[str] = None
    college: Optional[str] = None
    degree: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None

    @field_validator(
        "name",
        "education",
        "college",
        "degree",
        "branch",
        "target_role",
        "experience_level",
        mode="before",
    )
    @classmethod
    def validate_and_strip_string(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("Field must be a string.")
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or whitespace only if provided.")
        return cleaned

    @field_validator("semester")
    @classmethod
    def validate_positive_semester(cls, v: Optional[int]) -> Optional[int]:
        if v is None:
            return None
        if v <= 0:
            raise ValueError("semester must be a positive integer (greater than 0).")
        return v

    model_config = ConfigDict(extra="forbid")


class UserProfileResponse(UserProfileBase):
    """
    Public response representation of a UserProfile.
    """
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="forbid")
