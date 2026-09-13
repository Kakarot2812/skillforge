"""
Pydantic Schemas for Persistent Conversations and Messages.
Phase: Persistent AI Chat History (Checkpoint 6: Conversation API & Chat History UI).

Defines minimal, strictly typed request and response schemas:
- ConversationCreate: optional title, extra='forbid' to reject client-injected user_id.
- ConversationResponse: id, user_id, title, created_at, updated_at.
- MessageResponse: id, conversation_id, role, content, created_at.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversationCreate(BaseModel):
    """
    Schema for creating a new conversation.
    user_id is strictly forbidden in the request body to enforce trusted header auth.
    """
    title: Optional[str] = Field(None, max_length=255, description="Optional conversation title")

    model_config = ConfigDict(extra="forbid")

    @field_validator("title", mode="before")
    @classmethod
    def sanitize_title(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("title must be a string.")
        cleaned = v.strip()
        return cleaned if cleaned else None


class ConversationResponse(BaseModel):
    """Schema for returning conversation metadata."""
    id: UUID
    user_id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Schema for returning message history items."""
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
