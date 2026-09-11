"""
PostgreSQL / pgvector persistence and query repository for SkillForge AI RAG.
Post-MVP Phase 2, Checkpoint P3.

Guarantees:
- Enforces typed metadata conversions (Pydantic <-> JSONB storage)
- Exact cosine distance search via pgvector
- Stable deterministic ordering: similarity DESC, chunk_id ASC
- Strict metadata filtering (source_type, skill_id, source_reference)
- Strict top_k clamping
- Never exposes internal embedding vectors in retrieval results
- Typed exception translation
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import RAGChunk as DBRAGChunk
from app.db.models import RAGDocument as DBRAGDocument
from app.db.models import Skill
from app.rag.exceptions import RAGDocumentNotFoundError, RAGRetrievalError, RAGStorageError
from app.rag.models import (
    RAGChunk,
    RAGChunkMetadata,
    RAGDocument,
    RAGDocumentMetadata,
    RAGRetrievalFilter,
    RAGRetrievalResult,
    RAGSourceType,
)


class RAGRepository:
    """
    Repository handling database transactions for RAG documents and pgvector chunks.
    """

    def __init__(self, session: Session):
        self.session = session

    def save_document(self, document: RAGDocument) -> DBRAGDocument:
        """
        Persists an approved RAGDocument.
        Converts typed RAGDocumentMetadata to JSONB storage.
        """
        try:
            db_doc = DBRAGDocument(
                id=document.id,
                source_type=document.source_type.value,
                source_reference=document.source_reference,
                title=document.title,
                content=document.content,
                document_metadata=document.metadata.model_dump(mode="json"),
            )
            self.session.add(db_doc)
            self.session.flush()
            return db_doc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RAGStorageError(f"Failed to persist RAG document '{document.id}': {str(exc)}") from exc

    def save_chunks(self, chunks: List[RAGChunk]) -> List[DBRAGChunk]:
        """
        Persists a list of deterministically generated RAGChunks with embedding vectors.
        """
        if not chunks:
            return []

        db_chunks: List[DBRAGChunk] = []
        try:
            for c in chunks:
                if c.embedding is None:
                    raise RAGStorageError(f"Cannot save chunk {c.id} without an embedding vector.")

                db_chunk = DBRAGChunk(
                    id=c.id,
                    document_id=c.document_id,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    embedding=list(c.embedding),
                    skill_id=c.skill_id,
                    source_type=c.source_type.value,
                    source_reference=c.source_reference,
                    chunk_metadata=c.metadata.model_dump(mode="json"),
                )
                self.session.add(db_chunk)
                db_chunks.append(db_chunk)

            self.session.flush()
            return db_chunks
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RAGStorageError(f"Failed to persist RAG chunks: {str(exc)}") from exc

    def search_similar(
        self,
        query_vector: List[float],
        top_k: int = settings.RAG_DEFAULT_TOP_K,
        filters: Optional[RAGRetrievalFilter] = None,
    ) -> List[RAGRetrievalResult]:
        """
        Executes a vector similarity search in pgvector using cosine distance.
        Enforces deterministic tie-breaking: similarity DESC (distance ASC), chunk_id ASC.
        Returns typed RAGRetrievalResult instances; embedding vectors are NEVER exposed.
        """
        bounded_top_k = max(1, min(top_k, settings.RAG_MAX_TOP_K))

        try:
            # Cosine distance expression: 0 = identical, 2 = opposite
            distance_expr = DBRAGChunk.embedding.cosine_distance(query_vector)

            # Query join with Skill to get canonical skill_name if linked
            stmt = (
                select(
                    DBRAGChunk,
                    Skill.name.label("skill_name"),
                    (1.0 - distance_expr).label("similarity"),
                )
                .outerjoin(Skill, DBRAGChunk.skill_id == Skill.id)
            )

            # Apply deterministic metadata filters
            if filters:
                if filters.source_type is not None:
                    stmt = stmt.where(DBRAGChunk.source_type == filters.source_type.value)
                if filters.skill_id is not None:
                    stmt = stmt.where(DBRAGChunk.skill_id == filters.skill_id)
                if filters.source_reference is not None:
                    stmt = stmt.where(DBRAGChunk.source_reference == filters.source_reference)

            # Deterministic ordering: primary distance ASC (similarity DESC), secondary ID ASC
            stmt = stmt.order_by(distance_expr.asc(), DBRAGChunk.id.asc()).limit(bounded_top_k)

            rows = self.session.execute(stmt).all()

            results: List[RAGRetrievalResult] = []
            for row in rows:
                db_chunk: DBRAGChunk = row[0]
                skill_name: Optional[str] = row[1]
                similarity: float = float(row[2])

                # Clamp similarity score to [0.0, 1.0]
                clamped_similarity = max(0.0, min(1.0, similarity))

                # Deserialize metadata strictly into typed RAGChunkMetadata
                metadata = RAGChunkMetadata.model_validate(db_chunk.chunk_metadata)
                source_type_enum = RAGSourceType(db_chunk.source_type)

                results.append(
                    RAGRetrievalResult(
                        chunk_id=db_chunk.id,
                        document_id=db_chunk.document_id,
                        content=db_chunk.content,
                        similarity_score=round(clamped_similarity, 4),
                        source_type=source_type_enum,
                        source_reference=db_chunk.source_reference,
                        skill_id=db_chunk.skill_id,
                        skill_name=skill_name or metadata.skill_name,
                        provenance=source_type_enum,
                        source_timestamp=metadata.observed_at or db_chunk.created_at,
                        metadata=metadata,
                    )
                )

            return results
        except SQLAlchemyError as exc:
            raise RAGRetrievalError(f"Database vector similarity query failed: {str(exc)}") from exc

    def get_document(self, document_id: UUID) -> RAGDocument:
        """Fetches a single document and validates it into typed RAGDocument."""
        try:
            db_doc = self.session.get(DBRAGDocument, document_id)
            if not db_doc:
                raise RAGDocumentNotFoundError(f"RAG document '{document_id}' not found.")

            metadata = RAGDocumentMetadata.model_validate(db_doc.document_metadata)
            return RAGDocument(
                id=db_doc.id,
                source_type=RAGSourceType(db_doc.source_type),
                source_reference=db_doc.source_reference,
                title=db_doc.title,
                content=db_doc.content,
                metadata=metadata,
                created_at=db_doc.created_at,
            )
        except SQLAlchemyError as exc:
            raise RAGStorageError(f"Database error fetching document '{document_id}': {str(exc)}") from exc

    def delete_document(self, document_id: UUID) -> bool:
        """Deletes a document and its cascading chunks."""
        try:
            stmt = delete(DBRAGDocument).where(DBRAGDocument.id == document_id)
            result = self.session.execute(stmt)
            self.session.flush()
            return result.rowcount > 0
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RAGStorageError(f"Failed to delete RAG document '{document_id}': {str(exc)}") from exc
