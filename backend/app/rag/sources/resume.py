"""
Resume evidence adapter: turns a real ``Resume.raw_text`` row into a RAG
document, scoped to that resume's owning user so it can never leak to
another user's retrieval (see RetrievalFilters / repository isolation).
"""
from typing import Iterable

from sqlalchemy.orm import Session

from app.db.models import Resume
from app.rag.schemas import NormalizedDocument
from app.rag.sources.base import SourceAdapter


class ResumeSourceAdapter(SourceAdapter):
    source_type = "resume"

    def fetch(self, db: Session) -> Iterable[NormalizedDocument]:
        for resume in db.query(Resume).filter(Resume.raw_text.isnot(None)).all():
            doc = self._normalize(resume)
            if doc:
                yield doc

    def fetch_one(self, db: Session, source_id: str) -> Iterable[NormalizedDocument]:
        resume = db.query(Resume).filter(Resume.id == source_id).first()
        if resume is None:
            return
        doc = self._normalize(resume)
        if doc:
            yield doc

    def _normalize(self, resume: Resume):
        if not resume.raw_text or not resume.raw_text.strip():
            return None
        return NormalizedDocument(
            source_type=self.source_type,
            source_id=str(resume.id),
            title=f"Resume: {resume.file_name}",
            text=resume.raw_text,
            user_id=resume.user_id,
            source_url=None,
            metadata={"file_type": resume.file_type, "detected_sections": resume.parsed_data.get("detected_sections")
                      if isinstance(resume.parsed_data, dict) else None},
        )
