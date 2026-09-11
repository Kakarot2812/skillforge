"""
Centralised configuration for the SkillForge local Qwen AI module.

Follows the same pydantic-settings pattern as ``app/config.py`` (UPPERCASE,
case-sensitive fields read from environment variables or ``.env``), but is kept
in its own class so a bad QWEN_* value can never stop the rest of the backend
from booting. Settings are loaded lazily via ``get_qwen_settings()``.
"""
from functools import lru_cache
from urllib.parse import urlparse

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.qwen_ai.exceptions import QwenConfigurationError


class QwenSettings(BaseSettings):
    # Ollama model tag. See https://ollama.com/library/qwen3:8b
    QWEN_MODEL: str = Field(default="qwen3:8b", min_length=1, max_length=128)

    # Base URL of the local Ollama runtime (no trailing slash, no /api suffix).
    QWEN_BASE_URL: str = "http://localhost:11434"

    # Total seconds to wait for a generation. Local CPU inference can be slow.
    QWEN_TIMEOUT: float = Field(default=120.0, gt=0, le=900)

    # Seconds to wait for a TCP connection. Kept short so "Ollama is not
    # running" is reported quickly instead of after QWEN_TIMEOUT.
    QWEN_CONNECT_TIMEOUT: float = Field(default=5.0, gt=0, le=60)

    QWEN_TEMPERATURE: float = Field(default=0.6, ge=0.0, le=2.0)

    # Context window requested from Ollama. Ollama's default is small and
    # silently truncates long prompts, so we set it explicitly.
    QWEN_NUM_CTX: int = Field(default=8192, ge=2048, le=40960)

    # Qwen 3 "thinking" mode. Off by default for faster chat responses.
    # Thinking text is never returned to API users either way.
    QWEN_THINK: bool = False

    # How long Ollama keeps the model loaded in memory after a request.
    QWEN_KEEP_ALIVE: str = Field(default="10m", max_length=16)

    # Prompt-size budgets (characters) applied by the service layer.
    QWEN_MAX_HISTORY_MESSAGES: int = Field(default=12, ge=0, le=50)
    QWEN_MAX_HISTORY_CHARS: int = Field(default=12000, ge=0, le=100000)
    QWEN_MAX_CONTEXT_CHARS: int = Field(default=12000, ge=1000, le=100000)

    @field_validator("QWEN_BASE_URL")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("QWEN_BASE_URL must be an http(s) URL such as http://localhost:11434")
        if parsed.path not in {"", "/"}:
            raise ValueError("QWEN_BASE_URL must not include a path (use http://host:port, not .../api)")
        return value

    @field_validator("QWEN_MODEL")
    @classmethod
    def validate_model(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ch.isspace() for ch in value):
            raise ValueError("QWEN_MODEL must be a non-empty Ollama model tag without spaces")
        return value

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_qwen_settings() -> QwenSettings:
    """Load and cache Qwen settings, converting validation failures to a clean error."""
    try:
        return QwenSettings()
    except ValidationError as exc:
        fields = ", ".join(str(err["loc"][0]) for err in exc.errors() if err.get("loc"))
        raise QwenConfigurationError(detail=f"Invalid Qwen settings: {fields or exc}") from exc