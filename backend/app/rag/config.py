"""
Centralised configuration for the SkillForge RAG subsystem.

Follows the same pattern as ``app/qwen_ai/config.py``: kept in its own
pydantic-settings class, loaded lazily via ``get_rag_settings()``, so a bad
``RAG_*`` value can never stop the rest of the backend (including the Qwen
chat endpoint) from booting. When ``RAG_ENABLED`` is false, or settings fail
to validate, callers are expected to skip retrieval rather than fail chat.
"""
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.rag.exceptions import RagConfigurationError


class RagSettings(BaseSettings):
    RAG_ENABLED: bool = True

    # Ollama model tag used ONLY for embeddings. Must never be the Qwen3 8B
    # generation model — a separate embedding-capable model is required.
    RAG_EMBEDDING_MODEL: str = Field(default="qwen3-embedding:8b", min_length=1, max_length=128)

    # Base URL of the local Ollama runtime serving the embedding model.
    # Deliberately independent from QWEN_BASE_URL (app/qwen_ai/config.py) so
    # the two modules never share mutable state, even though they usually
    # point at the same local Ollama instance.
    RAG_OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Vector width stored in the `rag_chunks.embedding` column (fixed at
    # migration time). pgvector's HNSW index on the plain `vector` type is
    # only reliably indexable up to ~2000 dimensions, so this defaults well
    # under that ceiling. The embedding client validates every real
    # embedding's length against this value and raises rather than silently
    # truncating/padding a mismatched vector.
    RAG_EMBEDDING_DIMENSIONS: int = Field(default=1024, ge=32, le=2000)

    RAG_EMBEDDING_TIMEOUT: float = Field(default=60.0, gt=0, le=600)
    RAG_EMBEDDING_CONNECT_TIMEOUT: float = Field(default=5.0, gt=0, le=60)
    RAG_EMBEDDING_BATCH_SIZE: int = Field(default=16, ge=1, le=256)

    # Retrieval budgets.
    RAG_TOP_K: int = Field(default=8, ge=1, le=50)
    RAG_CANDIDATE_K: int = Field(default=20, ge=1, le=200)
    RAG_RRF_K: int = Field(default=60, ge=1, le=1000, description="RRF smoothing constant.")

    # Chunking (character-based, consistent with app/qwen_ai's char budgets).
    RAG_CHUNK_SIZE: int = Field(default=1600, ge=200, le=20000)
    RAG_CHUNK_OVERLAP: int = Field(default=200, ge=0, le=5000)

    # Per-evidence-item excerpt cap handed to Qwen. Kept comfortably under
    # SkillForgeContext.EVIDENCE_RENDER_CHARS so evidence is never truncated
    # twice (once here, once in app/qwen_ai/context.py).
    RAG_MAX_EVIDENCE_CONTENT_CHARS: int = Field(default=1400, ge=100, le=4000)

    @field_validator("RAG_OLLAMA_BASE_URL")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("RAG_OLLAMA_BASE_URL must be an http(s) URL such as http://localhost:11434")
        if parsed.path not in {"", "/"}:
            raise ValueError("RAG_OLLAMA_BASE_URL must not include a path (use http://host:port)")
        return value

    @field_validator("RAG_EMBEDDING_MODEL")
    @classmethod
    def validate_model(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ch.isspace() for ch in value):
            raise ValueError("RAG_EMBEDDING_MODEL must be a non-empty Ollama model tag without spaces")
        return value

    @field_validator("RAG_CHUNK_OVERLAP")
    @classmethod
    def validate_overlap(cls, value: int, info) -> int:
        chunk_size = info.data.get("RAG_CHUNK_SIZE")
        if chunk_size is not None and value >= chunk_size:
            raise ValueError("RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE")
        return value

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_rag_settings() -> RagSettings:
    """Load and cache RAG settings, converting validation failures to a clean error."""
    try:
        return RagSettings()
    except ValidationError as exc:
        fields = ", ".join(str(err["loc"][0]) for err in exc.errors() if err.get("loc"))
        raise RagConfigurationError(detail=f"Invalid RAG settings: {fields or exc}") from exc
