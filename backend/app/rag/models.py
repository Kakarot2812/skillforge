"""
Strictly-typed models and contracts for SkillForge AI RAG Retrieval Layer.
Post-MVP Phase 2, Checkpoint P3.

Core architectural boundaries:
- "The LLM never decides what is true."
- Deterministic systems decide what is true.
- Retrieval finds relevant verified evidence.
- AI explains, reasons over, and personalizes verified evidence.
- RAG is strictly a retrieval mechanism, NOT an authority mechanism.
- Embedding models, vector similarity scores, and retrieved chunks NEVER determine
  skill possession, classifications, demand scores, or priorities.
- Application layer strictly forbids arbitrary Dict[str, Any]. All metadata is
  strongly typed with deep immutability (frozen=True, extra="forbid").
"""

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Optional, Tuple
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import settings
from app.rag.exceptions import RAGValidationError

# Prohibited patterns indicating raw dump attempts
PROHIBITED_PATTERNS = [
    re.compile(r"BEGIN\s+PG_DUMP", re.IGNORECASE),
    re.compile(r"COPY\s+\w+\s+\(.*?\)\s+FROM\s+stdin", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", re.IGNORECASE),
    re.compile(r"diff\s+--git\s+a\/.*?b\/", re.IGNORECASE),  # Raw git diff dump
]


class RAGSourceType(str, Enum):
    """
    Categorical origin of approved RAG evidence documents.
    Strictly isolated from P2-B FactProvenance.
    """
    MARKET = "MARKET"
    RESUME = "RESUME"
    GITHUB = "GITHUB"
    DETERMINISTIC_ANALYSIS = "DETERMINISTIC_ANALYSIS"
    APPROVED_RESOURCE = "APPROVED_RESOURCE"
    APPROVED_PROJECT = "APPROVED_PROJECT"


# ---------------------------------------------------------------------------
# Strongly Typed Metadata Models (JSONB is Storage Only)
# ---------------------------------------------------------------------------

class RAGDocumentMetadata(BaseModel):
    """
    Strongly typed metadata container for an approved RAG document.
    Disallows arbitrary untyped dictionary containers (extra='forbid').
    """
    skill_id: Optional[UUID] = Field(None, description="Associated canonical skill UUID if applicable")
    skill_name: Optional[str] = Field(None, description="Associated canonical skill name if applicable")
    source_reference: str = Field(..., min_length=1, max_length=512, description="Specific reference identifier")
    observed_at: Optional[datetime] = Field(None, description="Timestamp when evidence/document was observed")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Evidence extraction confidence")
    approved_by: str = Field("deterministic_pipeline", description="Approval authority identifying this as approved evidence")
    content_hash: Optional[str] = Field(None, description="SHA-256 hash of normalized document content and metadata")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("source_reference")
    @classmethod
    def validate_source_ref(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("source_reference cannot be empty or whitespace only.")
        return v.strip()


class RAGChunkMetadata(BaseModel):
    """
    Strongly typed metadata container for an indexed chunk.
    Preserves provenance and document lineage.
    """
    skill_id: Optional[UUID] = Field(None, description="Associated canonical skill UUID if applicable")
    skill_name: Optional[str] = Field(None, description="Associated canonical skill name if applicable")
    source_reference: str = Field(..., min_length=1, max_length=512, description="Specific reference identifier")
    chunk_index: int = Field(..., ge=0, description="0-indexed position of the chunk in document")
    observed_at: Optional[datetime] = Field(None, description="Timestamp when evidence was observed")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# RAG Document & Chunk Entities
# ---------------------------------------------------------------------------

class RAGDocument(BaseModel):
    """
    Strongly-typed representation of an approved evidence document.
    Enforces strict ingestion boundaries: bounded length, no raw database dumps,
    no whole repository dumps, no secrets.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique document UUID")
    source_type: RAGSourceType = Field(..., description="Approved evidence source category")
    source_reference: str = Field(..., min_length=1, max_length=512, description="Originating source reference")
    title: str = Field(..., min_length=1, max_length=255, description="Human-readable title")
    content: str = Field(..., min_length=1, description="Bounded text content of approved evidence")
    metadata: RAGDocumentMetadata = Field(..., description="Strongly typed document metadata")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Ingestion timestamp",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title cannot be empty or whitespace only.")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content cannot be empty or whitespace only.")
        v_stripped = v.strip()

        # Enforce bounded maximum document length
        max_len = settings.RAG_MAX_DOCUMENT_CONTENT_LENGTH
        if len(v_stripped) > max_len:
            raise ValueError(
                f"Document content length ({len(v_stripped)}) exceeds maximum allowed bound of {max_len} characters."
            )

        # Enforce ingestion boundary: reject raw dumps and secrets
        for pattern in PROHIBITED_PATTERNS:
            if pattern.search(v_stripped):
                raise ValueError("Content contains prohibited raw dump or secret signature.")

        return v_stripped


class RAGChunk(BaseModel):
    """
    Strongly-typed representation of an evidence chunk produced by deterministic chunking.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique chunk UUID")
    document_id: UUID = Field(..., description="Parent document UUID")
    chunk_index: int = Field(..., ge=0, description="Zero-based sequence index")
    content: str = Field(..., min_length=1, description="Chunk text content")
    embedding: Optional[Tuple[float, ...]] = Field(None, description="Embedding vector tuple")
    skill_id: Optional[UUID] = Field(None, description="Associated canonical skill UUID")
    source_type: RAGSourceType = Field(..., description="Inherited source type")
    source_reference: str = Field(..., description="Inherited source reference")
    metadata: RAGChunkMetadata = Field(..., description="Strongly typed chunk metadata")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Chunk creation timestamp",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Retrieval Contracts
# ---------------------------------------------------------------------------

class RAGRetrievalFilter(BaseModel):
    """
    Deterministic metadata constraints applied during vector similarity retrieval.
    Filters are authoritative constraints: similarity never bypasses metadata filters.
    """
    source_type: Optional[RAGSourceType] = Field(None, description="Restrict retrieval to specific source type")
    skill_id: Optional[UUID] = Field(None, description="Restrict retrieval to specific canonical skill UUID")
    skill_ids: Optional[Tuple[UUID, ...]] = Field(None, description="Restrict retrieval to one or more canonical skill UUIDs")
    source_reference: Optional[str] = Field(None, description="Restrict retrieval to exact source reference")
    min_similarity: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum cosine similarity threshold [0.0, 1.0]")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_filter_consistency(self) -> "RAGRetrievalFilter":
        if self.skill_id is not None and self.skill_ids is not None:
            raise ValueError("Cannot specify both 'skill_id' and 'skill_ids' in RAGRetrievalFilter.")
        return self


class RAGRetrievalResult(BaseModel):
    """
    Typed retrieval result returned by the RAG layer.
    Strictly decoupled from internal database rows and embedding vectors.
    Vectors are NEVER returned in this contract.
    """
    chunk_id: UUID = Field(..., description="Retrieved chunk UUID")
    document_id: UUID = Field(..., description="Parent document UUID")
    content: str = Field(..., description="Chunk text content")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score [0.0, 1.0]")
    source_type: RAGSourceType = Field(..., description="Originating source type")
    source_reference: str = Field(..., description="Originating source reference")
    skill_id: Optional[UUID] = Field(None, description="Associated canonical skill UUID if present")
    skill_name: Optional[str] = Field(None, description="Canonical skill name if present")
    provenance: RAGSourceType = Field(..., description="Source provenance marker")
    source_timestamp: Optional[datetime] = Field(None, description="Observation timestamp if known")
    metadata: RAGChunkMetadata = Field(..., description="Strongly typed chunk metadata")

    model_config = ConfigDict(frozen=True, extra="forbid")
