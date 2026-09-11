"""
Typed exception hierarchy for SkillForge AI RAG Retrieval Layer.
Post-MVP Phase 2, Checkpoint P3.

Distinguishes between:
- Validation / boundary violations (empty documents, prohibited dumps)
- Embedding provider failures
- Embedding dimension mismatches
- Database storage / query failures
- Retrieval misses (which return empty sets rather than errors)

Infrastructure errors are NEVER converted into INSUFFICIENT_EVIDENCE.
"""

from typing import Optional


class RAGError(Exception):
    """Base exception for all RAG retrieval layer errors."""
    pass


class RAGValidationError(RAGError):
    """Raised when document content, metadata, or source type fails validation rules."""
    def __init__(self, message: str, field_name: Optional[str] = None):
        super().__init__(message)
        self.field_name = field_name


class RAGEmbeddingError(RAGError):
    """Raised when the local embedding provider encounters an inference or processing error."""
    pass


class RAGDimensionMismatchError(RAGEmbeddingError):
    """
    Raised when the embedding provider vector dimension does not match
    the authoritative configured / database vector dimension.
    """
    def __init__(self, expected: int, actual: int, model_name: Optional[str] = None):
        msg = (
            f"Embedding dimension mismatch: expected dimension {expected} "
            f"from configuration/database, but provider '{model_name or 'unknown'}' "
            f"produced dimension {actual}."
        )
        super().__init__(msg)
        self.expected = expected
        self.actual = actual
        self.model_name = model_name


class RAGStorageError(RAGError):
    """Raised when an error occurs during document or chunk persistence."""
    pass


class RAGRetrievalError(RAGError):
    """Raised when an error occurs during vector similarity query or retrieval execution."""
    pass


class RAGDocumentNotFoundError(RAGError):
    """Raised when a requested RAG document is not found in storage."""
    pass
