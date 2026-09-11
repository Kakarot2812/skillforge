"""
Evidence Retriever component for SkillForge AI RAG layer.
Post-MVP Phase 2, Checkpoint P3.

Coordinates vector generation for query text and delegates pgvector execution
to RAGRepository with authoritative metadata filters and bounded top_k.
"""

import logging
from typing import List, Optional

from app.config import settings
from app.rag.embeddings import EmbeddingProvider
from app.rag.exceptions import RAGValidationError
from app.rag.models import RAGRetrievalFilter, RAGRetrievalResult
from app.rag.repository import RAGRepository

logger = logging.getLogger(__name__)


class EvidenceRetriever:
    """
    Evidence retrieval coordinator combining embedding generation with database search.
    """

    def __init__(
        self,
        repository: RAGRepository,
        embedding_provider: EmbeddingProvider,
    ):
        self.repository = repository
        self.embedding_provider = embedding_provider

    def retrieve(
        self,
        query: str,
        top_k: int = settings.RAG_DEFAULT_TOP_K,
        filters: Optional[RAGRetrievalFilter] = None,
    ) -> List[RAGRetrievalResult]:
        """
        Retrieves top_k supporting evidence chunks relevant to the query text.

        Enforces:
        - Non-empty query validation
        - Dimension consistency
        - Authoritative metadata filtering
        - Bounded top_k limit
        - Clear separation between retrieval misses (returns []) and infrastructure errors
        """
        if not query or not query.strip():
            raise RAGValidationError("Retrieval query cannot be empty or whitespace only.")

        clean_query = query.strip()
        bounded_top_k = max(1, min(top_k, settings.RAG_MAX_TOP_K))

        # Generate query embedding
        query_vector = self.embedding_provider.embed_text(clean_query)

        # Execute similarity search with filters
        results = self.repository.search_similar(
            query_vector=query_vector,
            top_k=bounded_top_k,
            filters=filters,
        )

        logger.debug(
            "RAG retrieval executed for query '%s' (top_k=%d, filters=%s): found %d results",
            clean_query[:50],
            bounded_top_k,
            filters,
            len(results),
        )

        return results
