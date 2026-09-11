"""
Exceptions for SkillForge AI Career Chatbot module.
Post-MVP Phase 2, Checkpoint P2-C.

Provides typed exceptions for validation, service connectivity, timeouts,
and AI generation failures. Prohibits masking infrastructure errors as
insufficient evidence.
"""


class CareerChatError(Exception):
    """Base exception for all career chatbot errors."""


class CareerChatValidationError(CareerChatError):
    """Raised when user query, parameters, or context fail deterministic validation."""


class CareerChatServiceUnavailableError(CareerChatError):
    """Raised when the local Ollama daemon is unreachable or the model is missing."""


class CareerChatTimeoutError(CareerChatError):
    """Raised when the local Ollama generation exceeds the configured timeout."""


class CareerChatGenerationError(CareerChatError):
    """Raised when Ollama returns an API error or malformed response."""
