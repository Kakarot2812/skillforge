"""
Reciprocal Rank Fusion (RRF) over dense (vector) and sparse (FTS) candidate
lists.

Kept independent of retrieval/embedding/storage concerns so a future
reranker (e.g. a cross-encoder) can be slotted in without touching
``retriever.py``'s orchestration — it would simply re-score/re-order the
list this module returns.

RRF score for a chunk = sum over each ranked list it appears in of
``1 / (k + rank)``, where ``rank`` is 1-based. Chunks found by both dense and
sparse search naturally rank higher than chunks found by only one.
"""
from typing import Dict, List

from app.rag.schemas import RetrievedChunk


def reciprocal_rank_fusion(
    vector_results: List[RetrievedChunk],
    fts_results: List[RetrievedChunk],
    *,
    k: int = 60,
) -> List[RetrievedChunk]:
    """Fuse two ranked candidate lists into one, ordered by fused score (desc).

    Chunks are identified by ``chunk_id``. When a chunk appears in both
    lists, its ``vector_rank``/``fts_rank`` and content/provenance from the
    vector-list entry are kept (both carry identical provenance either way),
    but its score sums both contributions.
    """
    scores: Dict[object, float] = {}
    merged: Dict[object, RetrievedChunk] = {}
    vector_rank: Dict[object, int] = {}
    fts_rank: Dict[object, int] = {}

    for rank, chunk in enumerate(vector_results, start=1):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
        merged.setdefault(chunk.chunk_id, chunk)
        vector_rank[chunk.chunk_id] = rank

    for rank, chunk in enumerate(fts_results, start=1):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
        merged.setdefault(chunk.chunk_id, chunk)
        fts_rank[chunk.chunk_id] = rank

    fused: List[RetrievedChunk] = []
    for chunk_id, base_chunk in merged.items():
        fused.append(
            RetrievedChunk(
                chunk_id=base_chunk.chunk_id,
                document_id=base_chunk.document_id,
                source_type=base_chunk.source_type,
                source_id=base_chunk.source_id,
                title=base_chunk.title,
                content=base_chunk.content,
                source_url=base_chunk.source_url,
                user_id=base_chunk.user_id,
                metadata=base_chunk.metadata,
                vector_rank=vector_rank.get(chunk_id),
                fts_rank=fts_rank.get(chunk_id),
                fused_score=scores[chunk_id],
            )
        )

    fused.sort(key=lambda c: c.fused_score, reverse=True)
    return fused
