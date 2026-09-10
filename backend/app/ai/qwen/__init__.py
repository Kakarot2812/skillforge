"""
Local Qwen 3 8B / Ollama integration module for SkillForge AI.
Post-MVP Phase 2, Checkpoint P2-A.
"""

from app.ai.qwen.client import QwenClient
from app.ai.qwen.exceptions import (
    QwenAPIError,
    QwenConfigurationError,
    QwenConnectionError,
    QwenError,
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
)
from app.ai.qwen.models import (
    QwenChatResponse,
    QwenGenerateResponse,
    QwenHealthStatus,
    QwenMessage,
)

__all__ = [
    # Client
    "QwenClient",
    # Models
    "QwenMessage",
    "QwenChatResponse",
    "QwenGenerateResponse",
    "QwenHealthStatus",
    # Exceptions
    "QwenError",
    "QwenConfigurationError",
    "QwenConnectionError",
    "QwenTimeoutError",
    "QwenAPIError",
    "QwenResponseError",
    "QwenModelNotFoundError",
]
