"""
LangChain Chat History Adapter for SkillForge AI.
Phase: Persistent AI Chat History (Checkpoint 3: LangChain Integration).

Adapts PostgreSQL conversation history via ConversationService into immutable
LangChain message objects (HumanMessage, AIMessage, SystemMessage).

Strict architectural boundaries:
- ConversationService is the SOLE component responsible for Conversation/Message
  persistence and ownership enforcement.
- This adapter NEVER queries or mutates SQLAlchemy models directly.
- Maps database role 'user' -> HumanMessage, 'assistant' -> AIMessage.
- Preserves strict chronological message ordering.
- Bounds LLM history context (default: last 20 messages).
- Translates LangChain message structures into Qwen provider format.
"""

from typing import Dict, List, Optional, Sequence
from uuid import UUID

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from sqlalchemy.orm import Session

from app.db.models import Message
from app.services.conversation_service import (
    ConversationService,
    conversation_service as default_conversation_service,
)

DEFAULT_HISTORY_MESSAGE_LIMIT: int = 20


# -----------------------------------------------------------------------------
# Message Translation Layer
# -----------------------------------------------------------------------------

def message_to_langchain(msg: Message) -> BaseMessage:
    """
    Converts a database Message record into a LangChain BaseMessage.
    - 'user' -> HumanMessage
    - 'assistant' -> AIMessage
    """
    if msg.role == "user":
        return HumanMessage(content=msg.content)
    elif msg.role == "assistant":
        return AIMessage(content=msg.content)
    else:
        raise ValueError(
            f"Unsupported message role for LangChain conversion: '{msg.role}'"
        )


def messages_to_langchain(messages: Sequence[Message]) -> List[BaseMessage]:
    """Converts a sequence of database Message records into LangChain messages."""
    return [message_to_langchain(m) for m in messages]


def langchain_to_provider_dict(msg: BaseMessage) -> Dict[str, str]:
    """
    Translates a LangChain message object into the dictionary format expected
    by the Qwen/Ollama provider: {"role": str, "content": str}.
    """
    if isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, AIMessage):
        role = "assistant"
    elif isinstance(msg, SystemMessage):
        role = "system"
    else:
        role = getattr(msg, "type", "user")

    return {"role": role, "content": str(msg.content)}


def langchain_messages_to_provider(messages: Sequence[BaseMessage]) -> List[Dict[str, str]]:
    """Translates an ordered sequence of LangChain messages into provider dicts."""
    return [langchain_to_provider_dict(m) for m in messages]


# -----------------------------------------------------------------------------
# History Loading & Windowing
# -----------------------------------------------------------------------------

def get_langchain_history(
    db: Session,
    conversation_id: UUID,
    user_id: UUID,
    conversation_service: Optional[ConversationService] = None,
    limit: int = DEFAULT_HISTORY_MESSAGE_LIMIT,
    exclude_message_id: Optional[UUID] = None,
) -> List[BaseMessage]:
    """
    Loads conversation history through ConversationService and converts it into
    LangChain message objects.
    - Delegates all persistence and ownership checks to ConversationService.
    - Does NOT query the database directly.
    - If exclude_message_id is provided, omits that message (e.g. current user message)
      to represent strictly previous dialogue history.
    - Bounds history to the latest `limit` messages in chronological order.
    """
    service = conversation_service or default_conversation_service
    db_messages = service.get_messages(
        db, conversation_id=conversation_id, user_id=user_id
    )

    if exclude_message_id is not None:
        db_messages = [m for m in db_messages if m.id != exclude_message_id]

    if limit and len(db_messages) > limit:
        db_messages = db_messages[-limit:]

    return messages_to_langchain(db_messages)


# -----------------------------------------------------------------------------
# LangChain Standard BaseChatMessageHistory Implementation
# -----------------------------------------------------------------------------

class SkillForgeChatMessageHistory(BaseChatMessageHistory):
    """
    LangChain BaseChatMessageHistory implementation backed by SkillForge's
    ConversationService and PostgreSQL.
    
    Strict invariant:
    Delegates ALL persistence, retrieval, and ownership validation exclusively to
    ConversationService. Never touches SQLAlchemy session/models directly.
    """

    def __init__(
        self,
        db: Session,
        conversation_id: UUID,
        user_id: UUID,
        conversation_service: Optional[ConversationService] = None,
    ):
        self.db = db
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.service = conversation_service or default_conversation_service

    @property
    def messages(self) -> List[BaseMessage]:
        """Loads all messages for the conversation via ConversationService."""
        db_messages = self.service.get_messages(
            self.db,
            conversation_id=self.conversation_id,
            user_id=self.user_id,
        )
        return messages_to_langchain(db_messages)

    def add_message(self, message: BaseMessage) -> None:
        """Persists a message via ConversationService."""
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            raise ValueError(
                f"Unsupported LangChain message type for persistence: {type(message)}"
            )

        self.service.add_message(
            self.db,
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            role=role,
            content=str(message.content),
        )

    def clear(self) -> None:
        """Deletes the conversation via ConversationService."""
        self.service.delete_conversation(
            self.db,
            conversation_id=self.conversation_id,
            user_id=self.user_id,
        )
