"""
Public facade for the RAG subsystem.

This is the only module other parts of the backend (``qwen_api.py``,
``rag_api.py``) should import from ``app.rag``. It wires together config,
the embedding client, the retriever, and the ingestion pipeline, and turns
retrieval results into ``app.qwen_ai.context.EvidenceItem`` objects — the
existing, unchanged contract Qwen already knows how to cite.

RAG never computes authoritative SkillForge facts here either: this module
only retrieves, ranks, and hands over text. Deterministic scores/gaps/
roadmap decisions remain the responsibility of their own services.
"""
import logging
from functools import lru_cache
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.qwen_ai.context import EvidenceItem
from app.rag.config import RagSettings, get_rag_settings
from app.rag.embeddings import RagEmbeddingClient
from app.rag.exceptions import RagConfigurationError, RagDisabledError, RagError
from app.rag.ingestion import Ingestor
from app.rag.repository import delete_by_source, delete_document
from app.rag.retriever import Retriever
from app.rag.schemas import IngestResult, NormalizedDocument, RetrievalFilters
from app.rag.sources import SOURCE_ADAPTERS
from app.rag.sources.base import SourceAdapter

logger = logging.getLogger(__name__)


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


class RagService:
    def __init__(self, settings: RagSettings) -> None:
        self._settings = settings
        self._embedding_client = RagEmbeddingClient(settings)
        self._retriever = Retriever(self._embedding_client)
        self._ingestor = Ingestor(
            self._embedding_client,
            chunk_size=settings.RAG_CHUNK_SIZE,
            chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        )

    @property
    def enabled(self) -> bool:
        return self._settings.RAG_ENABLED

    async def retrieve_evidence(
        self,
        db: Session,
        query: str,
        *,
        user_id: Optional[UUID] = None,
        source_types: Optional[List[str]] = None,
    ) -> List[EvidenceItem]:
        """Retrieve and rank evidence for ``query``, shaped for SkillForgeContext.evidence.

        Returns an empty list (never raises) when RAG is disabled or when
        retrieval fails for any reason — grounding is additive, so a broken
        embedding service must never break the Qwen chat endpoint itself.
        Callers that need to distinguish "disabled" from "failed" should use
        ``retrieve_evidence_or_raise``.
        """
        try:
            return await self.retrieve_evidence_or_raise(db, query, user_id=user_id, source_types=source_types)
        except RagError as exc:
            logger.warning("rag retrieval unavailable, continuing ungrounded: %s", exc.detail or exc.public_message)
            return []

    async def retrieve_evidence_or_raise(
        self,
        db: Session,
        query: str,
        *,
        user_id: Optional[UUID] = None,
        source_types: Optional[List[str]] = None,
    ) -> List[EvidenceItem]:
        if not self._settings.RAG_ENABLED:
            raise RagDisabledError()

        filters = RetrievalFilters(user_id=user_id, source_types=source_types)
        chunks = await self._retriever.retrieve(
            db, query,
            filters=filters,
            top_k=self._settings.RAG_TOP_K,
            candidate_k=self._settings.RAG_CANDIDATE_K,
            rrf_k=self._settings.RAG_RRF_K,
        )

        max_chars = self._settings.RAG_MAX_EVIDENCE_CONTENT_CHARS
        items = []
        for chunk in chunks:
            content = chunk.content
            if len(content) > max_chars:
                content = content[:max_chars].rstrip() + " [...]"
            source = chunk.source_url or f"{chunk.source_type}:{chunk.source_id}"
            items.append(
                EvidenceItem(
                    source=_truncate(source, 300),
                    title=_truncate(chunk.title, 200),
                    content=content,
                    evidence_type=chunk.source_type,
                    metadata={"fused_score": round(chunk.fused_score, 4)},
                )
            )
        logger.info("rag retrieve_evidence query_chars=%d evidence_selected=%d", len(query), len(items))
        return items

    async def check_health(self) -> bool:
        return await self._embedding_client.check_health()

    async def ingest_document(self, db: Session, doc: NormalizedDocument) -> IngestResult:
        return await self._ingestor.ingest_document(db, doc)

    async def ingest_source(
        self, db: Session, source_type: str, *, source_id: Optional[str] = None,
    ) -> List[IngestResult]:
        adapter = self._get_adapter(source_type)
        return await self._ingestor.ingest_from_adapter(db, adapter, source_id=source_id)

    def delete_document(self, db: Session, document_id: UUID) -> bool:
        deleted = delete_document(db, document_id)
        db.commit()
        return deleted

    def delete_by_source(self, db: Session, source_type: str, source_id: str) -> bool:
        deleted = delete_by_source(db, source_type, source_id)
        db.commit()
        return deleted

    @staticmethod
    def _get_adapter(source_type: str) -> SourceAdapter:
        adapter = SOURCE_ADAPTERS.get(source_type)
        if adapter is None:
            raise ValueError(
                f"Unknown RAG source_type '{source_type}'. Known types: {sorted(SOURCE_ADAPTERS)}"
            )
        return adapter


@lru_cache
def get_rag_service() -> RagService:
    """FastAPI dependency. Override in tests via app.dependency_overrides.

    A bad RAG_* value must never take down the Qwen chat endpoint: on a
    configuration error, RAG is force-disabled using hardcoded field
    defaults built via ``model_construct`` (bypassing validation AND all
    environment/dotenv reading entirely) — a value that is invalid because
    it's set as a real OS environment variable, not just in .env, would
    otherwise make even this fallback construction fail.
    """
    try:
        settings = get_rag_settings()
    except RagConfigurationError as exc:
        logger.error("RAG configuration error, disabling RAG: %s", exc.detail)
        settings = RagSettings.model_construct(RAG_ENABLED=False)
    return RagService(settings)
