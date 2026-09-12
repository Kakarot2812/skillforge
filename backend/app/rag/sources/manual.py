"""
Manual/curated-document adapter.

Covers evidence with no dedicated SkillForge table — learning resources,
industry reports, official documentation summaries, admin-pasted job
postings (see docs/ai/RAG_DESIGN.md's original corpora, which were always
just text blobs, never separate relational tables). Unlike ``github.py``/
``resume.py``, there is nothing to enumerate from a database: the caller
(an internal ingestion script or ``POST /rag/ingest``) supplies the text
directly, and re-supplying identical text on a later call is what makes
ingestion idempotent for this source (see app/rag/ingestion.py).

``fetch()``/``fetch_one()`` therefore intentionally yield nothing — this
adapter is driven by ``normalize()``, not by scanning a table.
"""
from typing import Any, Dict, Iterable, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.rag.schemas import NormalizedDocument
from app.rag.sources.base import SourceAdapter


class ManualSourceAdapter(SourceAdapter):
    source_type = "manual"

    def fetch(self, db: Session) -> Iterable[NormalizedDocument]:
        return iter(())

    def fetch_one(self, db: Session, source_id: str) -> Iterable[NormalizedDocument]:
        return iter(())

    @staticmethod
    def normalize(
        *,
        source_id: str,
        title: str,
        text: str,
        user_id: Optional[UUID] = None,
        source_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NormalizedDocument:
        return NormalizedDocument(
            source_type=ManualSourceAdapter.source_type,
            source_id=source_id,
            title=title,
            text=text,
            user_id=user_id,
            source_url=source_url,
            metadata=metadata or {},
        )
