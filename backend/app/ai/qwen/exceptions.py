"""
Exceptions for local Qwen 3 8B / Ollama client.
Post-MVP Phase 2, Checkpoint P2-A.

Provides typed exception classes for communicating with Ollama.
"""

from typing import Optional


class QwenError(Exception):
    """Base exception for all Qwen / Ollama communication errors."""
    pass


class QwenConfigurationError(QwenError):
    """Raised when Ollama configuration (base URL, model name, timeout) is invalid or blank."""
    pass


class QwenConnectionError(QwenError):
    """Raised when network connection to the local Ollama instance fails or is refused."""
    pass


class QwenTimeoutError(QwenConnectionError):
    """Raised when communication with Ollama exceeds the configured timeout threshold."""
    pass


class QwenAPIError(QwenError):
    """Raised when the Ollama HTTP API returns a non-2xx status code."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class QwenResponseError(QwenError):
    """Raised when Ollama returns a malformed, unparseable, or schema-invalid response."""

    def __init__(
        self,
        message: str,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.response_body = response_body


class QwenModelNotFoundError(QwenAPIError):
    """Raised when the configured model is not available or registered in the local Ollama instance."""

    def __init__(
        self,
        message: str,
        model_name: str,
        status_code: Optional[int] = 404,
        response_body: Optional[str] = None,
    ):
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.model_name = model_name
