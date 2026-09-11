"""
SkillForge AI RAG / Evidence Retrieval Layer.
Post-MVP Phase 2, Checkpoint P3.

Provides isolated evidence ingestion, deterministic chunking, local embeddings,
pgvector storage, and metadata-filtered similarity retrieval.
"""

from app.rag.chunking import DeterministicChunker
from app.rag.embeddings import (
    EmbeddingProvider,
    LocalSentenceTransformerProvider,
    MockEmbeddingProvider,
)
from app.rag.exceptions import (
    RAGDimensionMismatchError,
    RAGDocumentNotFoundError,
    RAGEmbeddingError,
    RAGError,
    RAGRetrievalError,
    RAGStorageError,
    RAGValidationError,
)
from app.rag.models import (
    RAGChunk,
    RAGChunkMetadata,
    RAGDocument,
    RAGDocumentMetadata,
    RAGRetrievalFilter,
    RAGRetrievalResult,
    RAGSourceType,
)
from app.rag.repository import RAGRepository
from app.rag.retriever import EvidenceRetriever
from app.rag.service import RAGService

__all__ = [
    "DeterministicChunker",
    "EmbeddingProvider",
    "LocalSentenceTransformerProvider",
    "MockEmbeddingProvider",
    "RAGChunk",
    "RAGChunkMetadata",
    "RAGDimensionMismatchError",
    "RAGDocument",
    "RAGDocumentMetadata",
    "RAGDocumentNotFoundError",
    "RAGEmbeddingError",
    "RAGError",
    "RAGRepository",
    "RAGRetrievalError",
    "RAGRetrievalFilter",
    "RAGRetrievalResult",
    "RAGRetriever",
    "RAGService",
    "RAGSourceType",
    "RAGStorageError",
    "RAGValidationError",
]
