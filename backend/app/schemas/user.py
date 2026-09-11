from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    target_role: Optional[str] = None


class UserCreate(UserBase):
    model_config = ConfigDict(extra="forbid")


class UserRead(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    target_role: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
