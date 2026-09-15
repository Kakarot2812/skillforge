"""
Exceptions for Google Gemini 2.5 Flash LangChain client.
Post-MVP Career Roadmap PDF Foundation (Phase 1).

Provides typed, domain-isolated exception classes for communicating with Gemini.
Ensures provider details and credentials are never leaked.
"""

import re
from typing import Optional


def sanitize_gemini_message(message: str, api_key: Optional[str] = None) -> str:
    """
    Sanitizes error and log messages to guarantee that API keys, tokens,
    or sensitive authentication credentials are never exposed in logs,
    traces, or API responses.
    """
    if not message:
        return ""

    sanitized = message

    # Redact explicit passed API key
    if api_key and isinstance(api_key, str) and api_key.strip():
        sanitized = sanitized.replace(api_key.strip(), "[REDACTED_API_KEY]")

    # Redact Google API key patterns (AIzaSy...)
    sanitized = re.sub(r"AIza[0-9A-Za-z_-]{35}", "[REDACTED_API_KEY]", sanitized)

    # Redact common key=value query string or header patterns
    sanitized = re.sub(r"(?i)(key|token|authorization|bearer)=([^\s&]+)", r"\1=[REDACTED]", sanitized)

    return sanitized


class GeminiError(Exception):
    """Base exception for all Gemini provider communication errors in SkillForge."""

    def __init__(self, message: str, api_key: Optional[str] = None):
        sanitized = sanitize_gemini_message(message, api_key)
        super().__init__(sanitized)
        self.message = sanitized


class GeminiConfigurationError(GeminiError):
    """Raised when Gemini configuration (API key, model name, timeout, temperature) is invalid or missing."""
    pass


class GeminiAuthenticationError(GeminiError):
    """Raised when Gemini authentication fails due to invalid credentials, unauthorized access, or quota prohibition."""
    pass


class GeminiConnectionError(GeminiError):
    """Raised when network connection to the Gemini API fails or is refused."""
    pass


class GeminiTimeoutError(GeminiConnectionError):
    """Raised when communication with Gemini exceeds the configured timeout threshold."""
    pass


class GeminiAPIError(GeminiError):
    """Raised when the Gemini API returns an upstream error status code."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(message, api_key=api_key)
        self.status_code = status_code


class GeminiResponseError(GeminiError):
    """Raised when Gemini returns a malformed, unparseable, or schema-invalid response."""
    pass
