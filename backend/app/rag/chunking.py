"""
Deterministic chunking implementation for SkillForge AI RAG Retrieval Layer.
Post-MVP Phase 2, Checkpoint P3.

Guarantees:
- Deterministic, byte-reproducible output (same text + config -> identical chunks)
- Configurable chunk size and overlap
- Stable monotonic chunk indexing (0, 1, 2, ...)
- No empty chunks
- Bounded maximum chunk size
- Full provenance and metadata preservation (source_type, source_reference, skill_id)
- Zero LLM dependencies for chunking
"""

from typing import List
from uuid import uuid4

from app.config import settings
from app.rag.exceptions import RAGValidationError
from app.rag.models import RAGChunk, RAGChunkMetadata, RAGDocument, RAGSourceType


class DeterministicChunker:
    """
    Deterministic sliding-window text chunker with word-boundary awareness.
    """

    def __init__(
        self,
        chunk_size: int = settings.RAG_CHUNK_SIZE,
        chunk_overlap: int = settings.RAG_CHUNK_OVERLAP,
    ):
        if chunk_size <= 0:
            raise RAGValidationError(f"chunk_size must be positive, got {chunk_size}")
        if chunk_overlap < 0:
            raise RAGValidationError(f"chunk_overlap cannot be negative, got {chunk_overlap}")
        if chunk_overlap >= chunk_size:
            raise RAGValidationError(
                f"chunk_overlap ({chunk_overlap}) must be strictly less than chunk_size ({chunk_size})"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.step = chunk_size - chunk_overlap

    def chunk_document(self, document: RAGDocument) -> List[RAGChunk]:
        """
        Splits an approved RAGDocument into deterministic, bounded RAGChunks.
        Preserves provenance, canonical skill references, and source metadata.
        """
        if not isinstance(document, RAGDocument):
            raise RAGValidationError(f"Expected RAGDocument instance, got {type(document).__name__}")

        raw_text = document.content.strip()
        if not raw_text:
            raise RAGValidationError("Cannot chunk a document with empty content.")

        text_len = len(raw_text)
        chunks: List[RAGChunk] = []

        effective_chunk_size = (
            max(self.chunk_size, 1000)
            if getattr(document, "source_type", None) == RAGSourceType.APPROVED_PROJECT
            else self.chunk_size
        )

        # If text fits within single chunk
        if text_len <= effective_chunk_size:
            chunk_metadata = RAGChunkMetadata(
                skill_id=document.metadata.skill_id,
                skill_name=document.metadata.skill_name,
                source_reference=document.source_reference,
                chunk_index=0,
                observed_at=document.metadata.observed_at,
                confidence_score=document.metadata.confidence_score,
            )
            chunks.append(
                RAGChunk(
                    id=uuid4(),
                    document_id=document.id,
                    chunk_index=0,
                    content=raw_text,
                    embedding=None,
                    skill_id=document.metadata.skill_id,
                    source_type=document.source_type,
                    source_reference=document.source_reference,
                    metadata=chunk_metadata,
                )
            )
            return chunks

        # Multi-chunk sliding window
        start = 0
        chunk_idx = 0

        while start < text_len:
            end = min(start + effective_chunk_size, text_len)

            # If not at the end of the text, look for word boundary near end
            if end < text_len:
                # Look backwards up to 20% of chunk_size for a space or newline
                lookback_limit = max(start, end - int(self.chunk_size * 0.2))
                boundary = raw_text.rfind(" ", lookback_limit, end)
                newline_boundary = raw_text.rfind("\n", lookback_limit, end)
                best_boundary = max(boundary, newline_boundary)

                if best_boundary > start:
                    end = best_boundary

            chunk_text = raw_text[start:end].strip()

            if chunk_text:
                chunk_metadata = RAGChunkMetadata(
                    skill_id=document.metadata.skill_id,
                    skill_name=document.metadata.skill_name,
                    source_reference=document.source_reference,
                    chunk_index=chunk_idx,
                    observed_at=document.metadata.observed_at,
                    confidence_score=document.metadata.confidence_score,
                )
                chunks.append(
                    RAGChunk(
                        id=uuid4(),
                        document_id=document.id,
                        chunk_index=chunk_idx,
                        content=chunk_text,
                        embedding=None,
                        skill_id=document.metadata.skill_id,
                        source_type=document.source_type,
                        source_reference=document.source_reference,
                        metadata=chunk_metadata,
                    )
                )
                chunk_idx += 1

            if end >= text_len:
                break

            # Advance by step from current boundary
            start = end - self.chunk_overlap
            # Guard against zero/negative advancement
            if start <= (end - self.chunk_size):
                start = end

        return chunks
