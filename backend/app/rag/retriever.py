"""
Retrieval orchestration: embed the query, run dense + sparse candidate
searches against Postgres, fuse them with RRF, and return a small top-K list.

Async because it calls the async ``RagEmbeddingClient``; the synchronous
repository calls are pushed onto the thread pool via
``starlette.concurrency.run_in_threadpool`` so they never block the event
loop (the project's SQLAlchemy engine is sync, matching every other service
module — see app/rag/repository.py).
"""
import logging
import time
from typing import List

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.rag import repository
from app.rag.embeddings import RagEmbeddingClient
from app.rag.ranker import reciprocal_rank_fusion
from app.rag.schemas import RetrievalFilters, RetrievedChunk

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self, embedding_client: RagEmbeddingClient) -> None:
        self._embedding_client = embedding_client

    async def retrieve(
        self,
        db: Session,
        query: str,
        *,
        filters: RetrievalFilters,
        top_k: int,
        candidate_k: int,
        rrf_k: int,
    ) -> List[RetrievedChunk]:
        """Return up to ``top_k`` fused, ranked chunks visible under ``filters``."""
        started = time.perf_counter()

        query_vector = await self._embedding_client.embed_one(query)
        vector_candidates, fts_candidates = await run_in_threadpool(
            self._search_both, db, query, query_vector, filters, candidate_k
        )

        fused = reciprocal_rank_fusion(vector_candidates, fts_candidates, k=rrf_k)
        selected = fused[:top_k]

        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "rag retrieve query_chars=%d vector_candidates=%d fts_candidates=%d "
            "fused=%d selected=%d latency_ms=%d",
            len(query), len(vector_candidates), len(fts_candidates), len(fused), len(selected), latency_ms,
        )
        return selected

    @staticmethod
    def _search_both(db, query_text, query_vector, filters, candidate_k):
        vector_candidates = repository.vector_search(db, query_vector, filters, candidate_k)
        fts_candidates = repository.fts_search(db, query_text, filters, candidate_k)
        return vector_candidates, fts_candidates
