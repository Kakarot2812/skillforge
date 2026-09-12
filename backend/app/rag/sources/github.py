"""
GitHub evidence adapter: turns real ``GitHubRepository``/``ProjectEvidence``
rows (see app/db/models.py) into RAG documents.

One document per repository (its description) and one document per
project-evidence artifact (its description + matched content) — both are
real, already-collected text, never fabricated.
"""
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.db.models import GitHubRepository, ProjectEvidence, Skill
from app.rag.schemas import NormalizedDocument
from app.rag.sources.base import SourceAdapter


def _repo_text(repo: GitHubRepository) -> Optional[str]:
    """Text worth retrieving: human-authored description + detected language.

    ``default_branch``/``visibility`` are deployment metadata, not evidence
    content, so they are deliberately excluded here.
    """
    parts = []
    if repo.description:
        parts.append(repo.description)
    if repo.primary_language:
        parts.append(f"Primary language: {repo.primary_language}.")
    return "\n\n".join(parts) if parts else None


class GitHubRepositorySourceAdapter(SourceAdapter):
    """One document per repository, built from its own description/metadata."""

    source_type = "github_repository"

    def fetch(self, db: Session) -> Iterable[NormalizedDocument]:
        for repo in db.query(GitHubRepository).all():
            text = _repo_text(repo)
            if not text:
                continue
            yield NormalizedDocument(
                source_type=self.source_type,
                source_id=str(repo.id),
                title=repo.full_name or repo.repo_name,
                text=text,
                user_id=repo.user_id,
                source_url=repo.repo_url,
                metadata={
                    "primary_language": repo.primary_language,
                    "stars_count": repo.stars_count,
                    "is_fork": repo.is_fork,
                },
            )

    def fetch_one(self, db: Session, source_id: str) -> Iterable[NormalizedDocument]:
        repo = db.query(GitHubRepository).filter(GitHubRepository.id == source_id).first()
        if repo is None:
            return
        text = _repo_text(repo)
        if not text:
            return
        yield NormalizedDocument(
            source_type=self.source_type,
            source_id=str(repo.id),
            title=repo.full_name or repo.repo_name,
            text=text,
            user_id=repo.user_id,
            source_url=repo.repo_url,
            metadata={
                "primary_language": repo.primary_language,
                "stars_count": repo.stars_count,
                "is_fork": repo.is_fork,
            },
        )


class ProjectEvidenceSourceAdapter(SourceAdapter):
    """One document per detected project-evidence artifact."""

    source_type = "project_evidence"

    def fetch(self, db: Session) -> Iterable[NormalizedDocument]:
        rows = (
            db.query(ProjectEvidence, Skill, GitHubRepository)
            .join(Skill, ProjectEvidence.skill_id == Skill.id)
            .outerjoin(GitHubRepository, ProjectEvidence.repo_id == GitHubRepository.id)
            .all()
        )
        for evidence, skill, repo in rows:
            doc = self._normalize(evidence, skill, repo)
            if doc:
                yield doc

    def fetch_one(self, db: Session, source_id: str) -> Iterable[NormalizedDocument]:
        row = (
            db.query(ProjectEvidence, Skill, GitHubRepository)
            .join(Skill, ProjectEvidence.skill_id == Skill.id)
            .outerjoin(GitHubRepository, ProjectEvidence.repo_id == GitHubRepository.id)
            .filter(ProjectEvidence.id == source_id)
            .first()
        )
        if row is None:
            return
        doc = self._normalize(*row)
        if doc:
            yield doc

    def _normalize(self, evidence: ProjectEvidence, skill: Skill, repo: Optional[GitHubRepository]):
        parts = []
        if evidence.evidence_description:
            parts.append(evidence.evidence_description)
        if evidence.matched_content:
            parts.append(evidence.matched_content)
        if not parts:
            return None
        text = "\n\n".join(parts)
        title = f"{skill.name} evidence in {repo.repo_name}" if repo else f"{skill.name} evidence"
        return NormalizedDocument(
            source_type=self.source_type,
            source_id=str(evidence.id),
            title=title,
            text=text,
            user_id=evidence.user_id,
            source_url=repo.repo_url if repo else None,
            metadata={
                "skill_id": str(skill.id),
                "skill_name": skill.name,
                "evidence_type": evidence.evidence_type,
                "file_path": evidence.file_path,
                "confidence_score": evidence.confidence_score,
            },
        )
