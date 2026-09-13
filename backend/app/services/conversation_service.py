"""
Conversation Service for SkillForge AI.
Phase: Persistent AI Chat History (Checkpoint 2: Conversation Service).

Provides application-level operations for persistent AI conversation management:
- Create conversation
- Get conversation (with strict user ownership enforcement)
- List user conversations (deterministic ordering, metadata-only)
- Add message (with role validation and updated_at tracking)
- Get messages / history (chronological ordering)
- Delete conversation (cascading removal of all associated messages)

Authority boundary:
- This service manages conversation state and chat persistence only.
- It does NOT determine SkillForge authoritative evidence or override VerifiedContext.
"""

from datetime import datetime, timezone
import logging
from typing import List, Optional
import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Conversation, Message, User

logger = logging.getLogger(__name__)

VALID_MESSAGE_ROLES = frozenset({"user", "assistant"})


# -----------------------------------------------------------------------------
# Domain Exceptions
# -----------------------------------------------------------------------------

class ConversationError(Exception):
    """Base exception for conversation service operations."""
    pass


class ConversationNotFoundError(ConversationError):
    """Raised when a conversation is not found or is inaccessible."""
    pass


class ConversationOwnershipError(ConversationNotFoundError):
    """
    Raised when a conversation belongs to a different user.
    Subclasses ConversationNotFoundError so unauthorized access is treated as
    not-found by default, preventing existence enumeration.
    """
    pass


class UserNotFoundError(ConversationError):
    """Raised when a user is not found."""
    pass


class InvalidMessageRoleError(ConversationError, ValueError):
    """Raised when an unsupported message role is provided."""
    pass


class InvalidMessageContentError(ConversationError, ValueError):
    """Raised when message content is null or invalid."""
    pass


# -----------------------------------------------------------------------------
# Service Implementation
# -----------------------------------------------------------------------------

class ConversationService:
    """Application-level persistence service for persistent AI conversations and messages."""

    def create_conversation(
        self,
        db: Session,
        user_id: UUID,
        title: Optional[str] = None,
    ) -> Conversation:
        """
        Creates and persists a new conversation session for an existing user.
        Does not automatically generate an AI title.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError(f"User with id '{user_id}' not found.")

        title_value = title.strip() if isinstance(title, str) and title.strip() else None

        conversation = Conversation(
            id=uuid.uuid4(),
            user_id=user_id,
            title=title_value,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        logger.info(
            "Created conversation '%s' for user '%s' (title=%r)",
            conversation.id,
            user_id,
            conversation.title,
        )
        return conversation

    def get_conversation(
        self,
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
    ) -> Conversation:
        """
        Retrieves a conversation only if it belongs to the supplied user.
        Raises ConversationNotFoundError (or ConversationOwnershipError) if not found
        or if it belongs to another user, preventing cross-user conversation access.
        """
        conversation = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
            .first()
        )
        if not conversation:
            # Check if conversation exists under another user to raise specialized ownership error
            exists_other = (
                db.query(Conversation.id)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if exists_other:
                raise ConversationOwnershipError(
                    f"Conversation with id '{conversation_id}' not found."
                )
            raise ConversationNotFoundError(
                f"Conversation with id '{conversation_id}' not found."
            )

        return conversation

    def list_conversations(
        self,
        db: Session,
        user_id: UUID,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Conversation]:
        """
        Retrieves conversations belonging exclusively to the supplied user.
        Ordered deterministically: most recently updated first, then newest created.
        Loads conversation metadata without eager-loading message bodies.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError(f"User with id '{user_id}' not found.")

        query = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(
                Conversation.updated_at.desc(),
                Conversation.created_at.desc(),
                Conversation.id.desc(),
            )
        )

        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def add_message(
        self,
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
    ) -> Message:
        """
        Adds a message to a conversation after verifying ownership and role validity.
        Explicitly updates conversation.updated_at to reflect latest activity.
        Does not alter or mutate message content.
        """
        conversation = self.get_conversation(
            db, conversation_id=conversation_id, user_id=user_id
        )

        if not role or role not in VALID_MESSAGE_ROLES:
            raise InvalidMessageRoleError(
                f"Invalid message role '{role}'. Supported roles: {sorted(VALID_MESSAGE_ROLES)}"
            )

        if content is None or not isinstance(content, str):
            raise InvalidMessageContentError("Message content must be a non-null string.")

        now = datetime.now(timezone.utc)
        conversation.updated_at = now

        message = Message(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role=role,
            content=content,
            created_at=now,
        )

        db.add(message)
        db.commit()
        db.refresh(message)
        db.refresh(conversation)

        logger.info(
            "Added message '%s' (role=%s) to conversation '%s'",
            message.id,
            message.role,
            conversation.id,
        )
        return message

    def get_messages(
        self,
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Message]:
        """
        Retrieves all messages for an owned conversation in chronological order (oldest to newest).
        Returns an empty list for conversations with no messages.
        """
        conversation = self.get_conversation(
            db, conversation_id=conversation_id, user_id=user_id
        )

        query = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )

        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def get_history(
        self,
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Message]:
        """Alias for get_messages."""
        return self.get_messages(
            db,
            conversation_id=conversation_id,
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    def delete_conversation(
        self,
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Deletes a conversation after verifying ownership.
        Relying on database CASCADE to delete associated messages cleanly.
        """
        conversation = self.get_conversation(
            db, conversation_id=conversation_id, user_id=user_id
        )

        db.delete(conversation)
        db.commit()

        logger.info(
            "Deleted conversation '%s' for user '%s'",
            conversation_id,
            user_id,
        )
        return True


conversation_service = ConversationService()
