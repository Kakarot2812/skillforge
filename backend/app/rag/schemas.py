"""
Internal RAG data shapes.

These are plain dataclasses, not pydantic models: they flow between
``repository.py``, ``ranker.py``, ``retriever.py`` and ``service.py`` inside
the backend process only. The public request/response contract for the
``/rag`` API lives in ``app/api/v1/rag_api.py``; the contract with Qwen is
``app.qwen_ai.context.EvidenceItem`` (unchanged).
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass(frozen=True)
class NormalizedDocument:
    """A source-agnostic document ready for chunking, produced by a source adapter."""

    source_type: str
    source_id: str
    title: str
    text: str
    user_id: Optional[UUID] = None
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalFilters:
    """Metadata filters applied to every candidate query. Enforces user isolation."""

    user_id: Optional[UUID] = None
    source_types: Optional[List[str]] = None
    source_id: Optional[str] = None

    def include_global(self) -> bool:
        """Whether documents with user_id IS NULL (shared corpus) are eligible."""
        return True


@dataclass(frozen=True)
class RetrievedChunk:
    """One ranked chunk, with enough provenance for a Qwen citation."""

    chunk_id: UUID
    document_id: UUID
    source_type: str
    source_id: str
    title: str
    content: str
    source_url: Optional[str]
    user_id: Optional[UUID]
    metadata: Dict[str, Any]
    vector_rank: Optional[int] = None
    fts_rank: Optional[int] = None
    fused_score: float = 0.0


@dataclass(frozen=True)
class IngestResult:
    document_id: UUID
    source_type: str
    source_id: str
    version: int
    chunks_created: int
    chunks_reused: int
    changed: bool
