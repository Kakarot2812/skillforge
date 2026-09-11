"""
Qwen-specific exceptions.

Every exception carries a ``public_message`` that is safe to show API users and
an optional internal ``detail`` that is only ever logged. HTTP mapping lives in
``app/api/v1/qwen_api.py``.
"""
from typing import Optional


class QwenError(Exception):
    """Base class for all local Qwen AI errors."""

    default_message = "The SkillForge AI assistant encountered an error."

    def __init__(self, public_message: Optional[str] = None, *, detail: Optional[str] = None) -> None:
        self.public_message = public_message or self.default_message
        self.detail = detail
        super().__init__(self.public_message)


class QwenConfigurationError(QwenError):
    """The Qwen module is misconfigured (invalid QWEN_* environment values)."""

    default_message = "The SkillForge AI assistant is not configured correctly."


class QwenUnavailableError(QwenError):
    """The local Ollama runtime cannot be reached or cannot serve the model."""

    default_message = (
        "The local SkillForge AI model is unavailable. Make sure Ollama is running and try again."
    )


class QwenModelNotFoundError(QwenUnavailableError):
    """Ollama is running but the configured model has not been pulled."""

    default_message = (
        "The configured AI model is not installed in the local runtime. "
        "Pull it with Ollama (see docs/qwen_ai.md) and try again."
    )


class QwenTimeoutError(QwenError):
    """The model did not respond within QWEN_TIMEOUT."""

    default_message = "The local SkillForge AI model took too long to respond. Please try again."


class QwenResponseError(QwenError):
    """The runtime returned a malformed, empty or unexpected response."""

    default_message = "The local SkillForge AI model returned an invalid response."