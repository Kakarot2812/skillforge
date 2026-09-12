"""
Common interface for RAG source adapters.

Adding a new evidence source means writing one adapter that yields
``NormalizedDocument`` objects — no retrieval, ranking, or ingestion code
changes. See ``github.py``/``resume.py`` for adapters over real SkillForge
tables, and ``manual.py`` for arbitrary curated text (learning resources,
industry reports, admin-pasted job postings) that has no dedicated table.
"""
from abc import ABC, abstractmethod
from typing import Iterable

from sqlalchemy.orm import Session

from app.rag.schemas import NormalizedDocument


class SourceAdapter(ABC):
    """Yields normalized documents ready for chunking + embedding.

    Implementations must be read-only with respect to SkillForge's
    deterministic tables — an adapter observes existing data, it never
    computes or mutates scores/gaps/roadmap state.
    """

    source_type: str

    @abstractmethod
    def fetch(self, db: Session) -> Iterable[NormalizedDocument]:
        """Yield every document this adapter currently knows about."""
        raise NotImplementedError

    def fetch_one(self, db: Session, source_id: str) -> Iterable[NormalizedDocument]:
        """Yield the single document matching ``source_id``, if any.

        Default implementation filters ``fetch()`` in Python; adapters over
        large tables should override this with a targeted query.
        """
        return (doc for doc in self.fetch(db) if doc.source_id == source_id)
