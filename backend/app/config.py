from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "SkillForge AI API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database connection URL
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/skillforge"
    
    # Upload settings
    UPLOAD_DIR: str = "uploads/resumes"
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB
    
    # CORS Origins
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Adzuna API Settings (Post-MVP P1 Market Ingestion Foundation)
    ADZUNA_APP_ID: Optional[str] = None
    ADZUNA_APP_KEY: Optional[str] = None
    ADZUNA_API_BASE_URL: str = "https://api.adzuna.com/v1/api"

    # Local Ollama / Qwen 3 8B Settings (Post-MVP P2 AI Foundation)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    OLLAMA_TIMEOUT_SECONDS: float = 60.0
    OLLAMA_THINK: bool = False

    # Google Gemini API Settings (Post-MVP Career Roadmap PDF Foundation)
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        repr=False,
        description="Google Gemini API key (backend-only secret)",
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Configured Google Gemini model identifier",
    )
    GEMINI_TIMEOUT_SECONDS: float = Field(
        default=30.0,
        gt=0.0,
        description="Gemini API request timeout threshold in seconds",
    )

    # RAG / Local Embedding Settings (Post-MVP P3 RAG Foundation)
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    RAG_DEFAULT_TOP_K: int = 5
    RAG_MAX_TOP_K: int = 10
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    RAG_MAX_DOCUMENT_CONTENT_LENGTH: int = 50000
    RAG_MIN_SIMILARITY_THRESHOLD: float = 0.30

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
