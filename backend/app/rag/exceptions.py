"""
RAG-specific exceptions.

Every exception carries a ``public_message`` that is safe to show API users
and an optional internal ``detail`` that is only ever logged. Mirrors
``app/qwen_ai/exceptions.py`` so the two modules fail in a consistent,
recognisable shape. HTTP mapping lives in ``app/api/v1/rag_api.py``.
"""
from typing import Optional


class RagError(Exception):
    """Base class for all RAG errors."""

    default_message = "The evidence retrieval system encountered an error."

    def __init__(self, public_message: Optional[str] = None, *, detail: Optional[str] = None) -> None:
        self.public_message = public_message or self.default_message
        self.detail = detail
        super().__init__(self.public_message)


class RagConfigurationError(RagError):
    """The RAG module is misconfigured (invalid RAG_* environment values)."""

    default_message = "The evidence retrieval system is not configured correctly."


class RagDisabledError(RagError):
    """RAG was called while RAG_ENABLED is false."""

    default_message = "Evidence retrieval is currently disabled."


class RagEmbeddingUnavailableError(RagError):
    """The local Ollama runtime cannot be reached or cannot serve the embedding model."""

    default_message = (
        "The local embedding model is unavailable. Make sure Ollama is running and try again."
    )


class RagEmbeddingModelNotFoundError(RagEmbeddingUnavailableError):
    """Ollama is running but the configured embedding model has not been pulled."""

    default_message = (
        "The configured embedding model is not installed in the local runtime. "
        "Pull it with Ollama and try again."
    )


class RagEmbeddingTimeoutError(RagError):
    """The embedding call did not respond within RAG_EMBEDDING_TIMEOUT."""

    default_message = "The local embedding model took too long to respond."


class RagEmbeddingResponseError(RagError):
    """The runtime returned a malformed, empty or unexpected embedding response."""

    default_message = "The local embedding model returned an invalid response."


class RagEmbeddingDimensionError(RagError):
    """A returned embedding's length did not match RAG_EMBEDDING_DIMENSIONS."""

    default_message = "The embedding model returned a vector of an unexpected size."


class RagDocumentError(RagError):
    """A document could not be ingested (empty content, invalid metadata, etc.)."""

    default_message = "The document could not be ingested."


class RagNotFoundError(RagError):
    """A requested document/chunk does not exist (or is not visible to the caller)."""

    default_message = "The requested document was not found."
