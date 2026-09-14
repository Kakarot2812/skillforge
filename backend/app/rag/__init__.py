"""
SkillForge AI RAG / Evidence Retrieval Layer.
Post-MVP Phase 2, Checkpoint P3.

Provides isolated evidence ingestion, deterministic chunking, local embeddings,
pgvector storage, and metadata-filtered similarity retrieval.
"""

from app.rag.chunking import DeterministicChunker
from app.rag.embeddings import (
    EmbeddingProvider,
    LazySentenceTransformerProvider,
    LocalSentenceTransformerProvider,
    MockEmbeddingProvider,
    get_shared_embedding_provider,
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
from app.rag.ingestion import (
    EvidenceIngestionService,
    build_market_demand_rag_document,
    build_market_job_rag_document,
    build_resource_rag_document,
    compute_document_content_hash,
)
from app.rag.repository import RAGRepository
from app.rag.retriever import EvidenceRetriever
from app.rag.service import RAGService

__all__ = [
    "DeterministicChunker",
    "EmbeddingProvider",
    "EvidenceIngestionService",
    "EvidenceRetriever",
    "LazySentenceTransformerProvider",
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
    "build_market_demand_rag_document",
    "build_market_job_rag_document",
    "build_resource_rag_document",
    "compute_document_content_hash",
    "get_shared_embedding_provider",
]

