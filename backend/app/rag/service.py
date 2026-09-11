"""
RAG Service facade for SkillForge AI.
Post-MVP Phase 2, Checkpoint P3.

Core architectural boundaries:
- "The LLM never decides what is true."
- Deterministic systems decide what is true.
- Retrieval finds relevant verified evidence.
- AI explains, reasons over, and personalizes verified evidence.
- RAGService coordinates ingestion of approved evidence, deterministic chunking,
  local embedding generation, pgvector persistence, and filtered vector retrieval.
- Strictly prohibited from calculating skill classifications, demand scores, or priorities.
"""

import logging
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from app.config import settings
from app.rag.chunking import DeterministicChunker
from app.rag.embeddings import EmbeddingProvider, LocalSentenceTransformerProvider
from app.rag.exceptions import RAGValidationError
from app.rag.models import (
    RAGChunk,
    RAGDocument,
    RAGRetrievalFilter,
    RAGRetrievalResult,
)
from app.rag.repository import RAGRepository
from app.rag.retriever import EvidenceRetriever

logger = logging.getLogger(__name__)


class RAGService:
    """
    Unified application service for approved evidence indexing and retrieval.
    """

    def __init__(
        self,
        session: Session,
        embedding_provider: Optional[EmbeddingProvider] = None,
        chunker: Optional[DeterministicChunker] = None,
    ):
        self.session = session
        self.embedding_provider = embedding_provider or LocalSentenceTransformerProvider()
        # Verify dimension consistency immediately
        self.embedding_provider.validate_dimension_consistency(settings.EMBEDDING_DIMENSION)

        self.chunker = chunker or DeterministicChunker()
        self.repository = RAGRepository(session=self.session)
        self.retriever = EvidenceRetriever(
            repository=self.repository,
            embedding_provider=self.embedding_provider,
        )

    def index_document(self, document: RAGDocument) -> Tuple[RAGDocument, List[RAGChunk]]:
        """
        Indexes an explicitly approved evidence document:
        1. Validates document boundary and metadata.
        2. Splits into deterministic chunks.
        3. Generates embedding vectors for all chunks.
        4. Persists document and chunks to PostgreSQL/pgvector.
        5. Commits transaction and returns typed entities.
        """
        if not isinstance(document, RAGDocument):
            raise RAGValidationError(f"Expected RAGDocument instance, got {type(document).__name__}")

        # Step 1: Deterministic chunking
        chunks = self.chunker.chunk_document(document)
        if not chunks:
            raise RAGValidationError(f"Chunker produced 0 chunks for document '{document.id}'.")

        # Step 2: Batch embedding generation
        chunk_texts = [c.content for c in chunks]
        embeddings = self.embedding_provider.embed_documents(chunk_texts)

        # Attach embeddings to chunks
        embedded_chunks: List[RAGChunk] = []
        for c, emb in zip(chunks, embeddings):
            embedded_chunks.append(
                RAGChunk(
                    id=c.id,
                    document_id=c.document_id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    embedding=tuple(emb),
                    skill_id=c.skill_id,
                    source_type=c.source_type,
                    source_reference=c.source_reference,
                    metadata=c.metadata,
                    created_at=c.created_at,
                )
            )

        # Step 3: Persistence
        self.repository.save_document(document)
        self.repository.save_chunks(embedded_chunks)
        self.session.commit()

        logger.info(
            "Successfully indexed approved RAG document '%s' (%s, %d chunks)",
            document.title,
            document.source_type.value,
            len(embedded_chunks),
        )

        return document, embedded_chunks

    def retrieve(
        self,
        query: str,
        top_k: int = settings.RAG_DEFAULT_TOP_K,
        filters: Optional[RAGRetrievalFilter] = None,
    ) -> List[RAGRetrievalResult]:
        """
        Retrieves relevant supporting evidence chunks matching query and filters.
        Enforces top_k bounds and typed return contract.
        """
        return self.retriever.retrieve(
            query=query,
            top_k=top_k,
            filters=filters,
        )

    def delete_document(self, document_id: UUID) -> bool:
        """Deletes an indexed document and its associated chunks."""
        result = self.repository.delete_document(document_id)
        self.session.commit()
        return result
