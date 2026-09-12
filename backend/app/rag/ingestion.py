"""
Idempotent ingestion pipeline.

    normalize (source adapter) -> content hash -> detect unchanged
        -> chunk -> embed -> upsert document -> replace chunks -> done

Re-ingesting a document whose normalized text is byte-for-byte (modulo
whitespace) unchanged is a pure no-op: no re-chunking, no embedding calls,
no chunk writes. A real content change bumps the document's version and
fully replaces its chunks in one transaction.
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.rag import repository
from app.rag.chunking import chunk_text, content_hash
from app.rag.embeddings import RagEmbeddingClient
from app.rag.exceptions import RagDocumentError
from app.rag.schemas import IngestResult, NormalizedDocument
from app.rag.sources.base import SourceAdapter

logger = logging.getLogger(__name__)


class Ingestor:
    def __init__(
        self,
        embedding_client: RagEmbeddingClient,
        *,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        self._embedding_client = embedding_client
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    async def ingest_document(self, db: Session, doc: NormalizedDocument) -> IngestResult:
        """Ingest one normalized document. Commits on success, rolls back on failure."""
        if not doc.text or not doc.text.strip():
            raise RagDocumentError(f"Document '{doc.source_type}:{doc.source_id}' has empty content.")

        logger.info("rag ingest start source=%s:%s", doc.source_type, doc.source_id)
        digest = content_hash(doc.text)

        try:
            record, changed = repository.upsert_document(db, doc, digest)
            if not changed:
                db.commit()
                existing_chunk_count = len(record.chunks)
                logger.info(
                    "rag ingest unchanged source=%s:%s version=%d chunks=%d",
                    doc.source_type, doc.source_id, record.version, existing_chunk_count,
                )
                return IngestResult(
                    document_id=record.id, source_type=doc.source_type, source_id=doc.source_id,
                    version=record.version, chunks_created=0, chunks_reused=existing_chunk_count,
                    changed=False,
                )

            chunks = chunk_text(doc.text, chunk_size=self._chunk_size, chunk_overlap=self._chunk_overlap)
            if not chunks:
                raise RagDocumentError(f"Document '{doc.source_type}:{doc.source_id}' produced no chunks.")

            embeddings = await self._embedding_client.embed([c.content for c in chunks])
            repository.replace_chunks(db, record.id, chunks, embeddings)
            db.commit()

            logger.info(
                "rag ingest changed source=%s:%s version=%d chunks=%d",
                doc.source_type, doc.source_id, record.version, len(chunks),
            )
            return IngestResult(
                document_id=record.id, source_type=doc.source_type, source_id=doc.source_id,
                version=record.version, chunks_created=len(chunks), chunks_reused=0, changed=True,
            )
        except Exception:
            db.rollback()
            logger.exception("rag ingest failed source=%s:%s", doc.source_type, doc.source_id)
            raise

    async def ingest_from_adapter(
        self, db: Session, adapter: SourceAdapter, *, source_id: Optional[str] = None,
    ) -> List[IngestResult]:
        """Ingest every document an adapter yields, or just ``source_id`` if given."""
        documents = list(adapter.fetch_one(db, source_id) if source_id else adapter.fetch(db))
        results: List[IngestResult] = []
        for doc in documents:
            results.append(await self.ingest_document(db, doc))
        logger.info(
            "rag ingest_from_adapter source_type=%s documents=%d changed=%d unchanged=%d",
            adapter.source_type, len(results),
            sum(1 for r in results if r.changed), sum(1 for r in results if not r.changed),
        )
        return results
