"""
SkillForge AI Career Chatbot module.
Post-MVP Phase 2, Checkpoint P2-C.

Evidence-grounded explanation layer over deterministic SkillForge intelligence.
"""

from app.ai.chatbot.exceptions import (
    CareerChatError,
    CareerChatGenerationError,
    CareerChatServiceUnavailableError,
    CareerChatTimeoutError,
    CareerChatValidationError,
)
from app.ai.chatbot.models import (
    CareerChatRequest,
    CareerChatResponse,
    ChatResponseStatus,
    ChatUsageStats,
)
from app.ai.chatbot.prompts import (
    CAREER_CHATBOT_SYSTEM_PROMPT,
    build_career_chat_langchain_messages,
    build_career_chat_messages,
    serialize_verified_context,
)
from app.ai.chatbot.personalization import (
    PersonalizationContext,
    ProfileContext,
    assemble_personalization_context,
)
from app.ai.chatbot.langchain_history import (
    SkillForgeChatMessageHistory,
    get_langchain_history,
    message_to_langchain,
    messages_to_langchain,
)
from app.ai.chatbot.service import CareerChatService

__all__ = [
    "CareerChatService",
    "CareerChatRequest",
    "CareerChatResponse",
    "ChatResponseStatus",
    "ChatUsageStats",
    "CAREER_CHATBOT_SYSTEM_PROMPT",
    "serialize_verified_context",
    "build_career_chat_messages",
    "build_career_chat_langchain_messages",
    "ProfileContext",
    "PersonalizationContext",
    "assemble_personalization_context",
    "CareerChatError",
    "CareerChatValidationError",
    "CareerChatServiceUnavailableError",
    "CareerChatTimeoutError",
    "CareerChatGenerationError",
    "SkillForgeChatMessageHistory",
    "get_langchain_history",
    "message_to_langchain",
    "messages_to_langchain",
]

