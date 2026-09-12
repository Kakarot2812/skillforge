"""
SQLAlchemy persistence for the RAG evidence layer.

Owns all direct access to ``rag_documents``/``rag_chunks`` (see
``app/db/models.py``). Every read here enforces user isolation via
``RetrievalFilters`` — callers (retriever.py, ingestion.py) never build raw
queries against these tables themselves.

Functions ``flush()`` but do not ``commit()``; the caller that owns the unit
of work (``app/rag/ingestion.py`` for writes) controls the transaction
boundary so a failed embed/chunk step can be rolled back cleanly.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.models import RagChunk, RagDocument
from app.rag.chunking import Chunk
from app.rag.schemas import NormalizedDocument, RetrievalFilters, RetrievedChunk

logger = logging.getLogger(__name__)


def get_document_by_source(db: Session, source_type: str, source_id: str) -> Optional[RagDocument]:
    return (
        db.query(RagDocument)
        .filter(RagDocument.source_type == source_type, RagDocument.source_id == source_id)
        .first()
    )


def get_document(db: Session, document_id: UUID) -> Optional[RagDocument]:
    return db.query(RagDocument).filter(RagDocument.id == document_id).first()


def upsert_document(db: Session, doc: NormalizedDocument, content_hash: str) -> Tuple[RagDocument, bool]:
    """Insert or update the document row for ``doc``.

    Returns ``(record, changed)``. ``changed`` is False when an existing
    document already has this exact ``content_hash`` (idempotent re-ingest:
    cosmetic fields are refreshed but the version is not bumped and no
    re-chunk/re-embed is needed). ``changed`` is True for a brand new
    document or one whose content actually differs, in which case the
    caller is expected to replace its chunks and bump nothing else itself
    (version bump happens here).
    """
    existing = get_document_by_source(db, doc.source_type, doc.source_id)

    if existing is None:
        record = RagDocument(
            source_type=doc.source_type,
            source_id=doc.source_id,
            user_id=doc.user_id,
            title=doc.title,
            source_url=doc.source_url,
            content_hash=content_hash,
            version=1,
            document_metadata=doc.metadata,
        )
        db.add(record)
        db.flush()
        return record, True

    unchanged_content = existing.content_hash == content_hash
    existing.title = doc.title
    existing.source_url = doc.source_url
    existing.user_id = doc.user_id
    existing.document_metadata = doc.metadata
    if not unchanged_content:
        existing.content_hash = content_hash
        existing.version = (existing.version or 1) + 1
    db.flush()
    return existing, (not unchanged_content)


def replace_chunks(
    db: Session,
    document_id: UUID,
    chunks: List[Chunk],
    embeddings: List[List[float]],
) -> int:
    """Atomically replace all chunks for a document (simple, reliable full-replace).

    Idempotency of the parent pipeline is enforced one level up (see
    ``app/rag/ingestion.py``): this is only called when the document's
    content actually changed, so re-ingesting identical content never
    reaches here and never regenerates embeddings.
    """
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings must be the same length")

    db.query(RagChunk).filter(RagChunk.document_id == document_id).delete(synchronize_session=False)
    db.flush()

    for chunk, vector in zip(chunks, embeddings):
        db.add(
            RagChunk(
                document_id=document_id,
                chunk_index=chunk.index,
                content=chunk.content,
                content_hash=chunk.content_hash,
                embedding=vector,
                chunk_metadata=chunk.metadata,
            )
        )
    db.flush()
    return len(chunks)


def delete_document(db: Session, document_id: UUID) -> bool:
    doc = get_document(db, document_id)
    if doc is None:
        return False
    db.delete(doc)
    db.flush()
    return True


def delete_by_source(db: Session, source_type: str, source_id: str) -> bool:
    doc = get_document_by_source(db, source_type, source_id)
    if doc is None:
        return False
    db.delete(doc)
    db.flush()
    return True


def _apply_isolation_and_filters(query, filters: RetrievalFilters):
    """Restrict candidates to documents visible to the caller.

    A supplied ``user_id`` may see that user's own documents plus the
    global/shared corpus (``user_id IS NULL``). No ``user_id`` at all means
    only the global corpus is visible — an anonymous or unscoped caller must
    never see another user's private resume/GitHub evidence.
    """
    if filters.user_id is not None:
        query = query.filter(or_(RagDocument.user_id == filters.user_id, RagDocument.user_id.is_(None)))
    else:
        query = query.filter(RagDocument.user_id.is_(None))
    if filters.source_types:
        query = query.filter(RagDocument.source_type.in_(filters.source_types))
    if filters.source_id:
        query = query.filter(RagDocument.source_id == filters.source_id)
    return query


def _to_retrieved_chunk(chunk: RagChunk, doc: RagDocument, *, rank: int, is_vector: bool) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk.id,
        document_id=doc.id,
        source_type=doc.source_type,
        source_id=doc.source_id,
        title=doc.title,
        content=chunk.content,
        source_url=doc.source_url,
        user_id=doc.user_id,
        metadata={**(doc.document_metadata or {}), **(chunk.chunk_metadata or {})},
        vector_rank=rank if is_vector else None,
        fts_rank=rank if not is_vector else None,
    )


def vector_search(
    db: Session,
    query_embedding: List[float],
    filters: RetrievalFilters,
    limit: int,
) -> List[RetrievedChunk]:
    """Dense retrieval: nearest chunks by cosine distance, most similar first."""
    distance = RagChunk.embedding.cosine_distance(query_embedding)
    query = (
        db.query(RagChunk, RagDocument)
        .join(RagDocument, RagChunk.document_id == RagDocument.id)
        .filter(RagChunk.embedding.isnot(None))
    )
    query = _apply_isolation_and_filters(query, filters)
    rows = query.order_by(distance.asc()).limit(limit).all()
    return [_to_retrieved_chunk(chunk, doc, rank=i + 1, is_vector=True) for i, (chunk, doc) in enumerate(rows)]


def fts_search(
    db: Session,
    query_text: str,
    filters: RetrievalFilters,
    limit: int,
) -> List[RetrievedChunk]:
    """Sparse/keyword retrieval via PostgreSQL full-text search, best match first."""
    tsquery = func.plainto_tsquery("english", query_text)
    rank = func.ts_rank(RagChunk.search_vector, tsquery)
    query = (
        db.query(RagChunk, RagDocument)
        .join(RagDocument, RagChunk.document_id == RagDocument.id)
        .filter(RagChunk.search_vector.op("@@")(tsquery))
    )
    query = _apply_isolation_and_filters(query, filters)
    rows = query.order_by(rank.desc()).limit(limit).all()
    return [_to_retrieved_chunk(chunk, doc, rank=i + 1, is_vector=False) for i, (chunk, doc) in enumerate(rows)]
