"""
API router for Persistent Conversations & Messages.
Phase: Persistent AI Chat History (Checkpoint 6: Conversation API & Chat History UI).

Endpoints:
- GET    /api/v1/conversations — List conversations for authenticated user
- POST   /api/v1/conversations — Create a new conversation session
- GET    /api/v1/conversations/{conversation_id}/messages — Retrieve message history
- DELETE /api/v1/conversations/{conversation_id} — Delete conversation & cascade messages

Strict constraints:
- Router is a thin HTTP adapter delegating 100% of business logic to ConversationService.
- Authentication resolved strictly via trusted X-User-Id header.
- user_id is strictly forbidden in request bodies.
- Ownership is enforced strictly; unauthorized access returns 404.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
)
from app.services.conversation_service import (
    ConversationNotFoundError,
    UserNotFoundError,
    conversation_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Conversations"])


# -----------------------------------------------------------------------------
# Identity Resolution Dependency
# -----------------------------------------------------------------------------

def resolve_authenticated_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> UUID:
    """
    Resolves and verifies candidate user identity from the trusted X-User-Id header.
    Rejects missing header with 401.
    Rejects malformed UUID with 422.
    Rejects nonexistent user with 404.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-User-Id header missing.",
        )

    try:
        user_uuid = UUID(x_user_id.strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID format in X-User-Id header.",
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_uuid}' not found.",
        )

    return user_uuid


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.get(
    "",
    response_model=List[ConversationResponse],
    status_code=status.HTTP_200_OK,
    summary="List User Conversations",
    description=(
        "Retrieves all conversations belonging to the authenticated user. "
        "Ordered deterministically: updated_at DESC, created_at DESC, id DESC."
    ),
)
def list_conversations(
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max conversations to return"),
    offset: int = Query(0, ge=0, description="Number of conversations to skip"),
    user_id: UUID = Depends(resolve_authenticated_user_id),
    db: Session = Depends(get_db),
) -> List[ConversationResponse]:
    """Retrieves metadata-only conversations for the authenticated user."""
    try:
        conversations = conversation_service.list_conversations(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        return [ConversationResponse.model_validate(c) for c in conversations]
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Conversation",
    description="Creates a new conversation session for the authenticated user.",
)
def create_conversation(
    conversation_data: Optional[ConversationCreate] = None,
    user_id: UUID = Depends(resolve_authenticated_user_id),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """Creates an empty conversation session in PostgreSQL."""
    title = conversation_data.title if conversation_data else None
    try:
        conversation = conversation_service.create_conversation(
            db=db,
            user_id=user_id,
            title=title,
        )
        return ConversationResponse.model_validate(conversation)
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{conversation_id}/messages",
    response_model=List[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Conversation Messages",
    description=(
        "Retrieves messages for an owned conversation in chronological order (created_at ASC, id ASC). "
        "Returns 404 if conversation does not exist or belongs to another user."
    ),
)
def get_conversation_messages(
    conversation_id: UUID,
    limit: Optional[int] = Query(None, ge=1, le=100, description="Max messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip"),
    user_id: UUID = Depends(resolve_authenticated_user_id),
    db: Session = Depends(get_db),
) -> List[MessageResponse]:
    """Retrieves all messages for an owned conversation."""
    try:
        messages = conversation_service.get_messages(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )
        return [MessageResponse.model_validate(m) for m in messages]
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id '{conversation_id}' not found.",
        )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Conversation",
    description="Deletes an owned conversation and all associated messages via database CASCADE.",
)
def delete_conversation(
    conversation_id: UUID,
    user_id: UUID = Depends(resolve_authenticated_user_id),
    db: Session = Depends(get_db),
) -> None:
    """Deletes an owned conversation session."""
    try:
        conversation_service.delete_conversation(
            db=db,
            conversation_id=conversation_id,
            user_id=user_id,
        )
    except ConversationNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id '{conversation_id}' not found.",
        )
