import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ProjectEvidence, Skill, GitHubRepository
from app.schemas.evidence import (
    ProjectEvidenceItem,
    ProjectEvidenceListResponse,
    ProjectEvidenceDetailResponse,
)
from app.schemas.skill import PaginationMeta

router = APIRouter(prefix="/evidence", tags=["Project Evidence"])


@router.get(
    "",
    response_model=ProjectEvidenceListResponse,
    summary="List Verified Project Evidence Items",
)
def list_evidence(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    repository_id: Optional[uuid.UUID] = Query(None, description="Filter by repository ID"),
    repo_id: Optional[uuid.UUID] = Query(None, description="Alias filter by repository ID"),
    skill_id: Optional[uuid.UUID] = Query(None, description="Filter by canonical skill ID"),
    evidence_type: Optional[str] = Query(None, description="Filter by evidence type"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db),
) -> ProjectEvidenceListResponse:
    """
    Returns auditable project evidence items linking codebase artifacts
    to demonstrated skills, with deterministic ordering.
    """
    target_repo_id = repository_id or repo_id

    query = (
        db.query(ProjectEvidence, Skill, GitHubRepository)
        .join(Skill, ProjectEvidence.skill_id == Skill.id)
        .outerjoin(GitHubRepository, ProjectEvidence.repo_id == GitHubRepository.id)
    )

    if target_repo_id:
        query = query.filter(ProjectEvidence.repo_id == target_repo_id)
    if skill_id:
        query = query.filter(ProjectEvidence.skill_id == skill_id)
    if evidence_type:
        query = query.filter(ProjectEvidence.evidence_type == evidence_type)
    if user_id:
        query = query.filter(ProjectEvidence.user_id == user_id)

    total = query.count()
    results = (
        query.order_by(
            ProjectEvidence.confidence_score.desc(),
            ProjectEvidence.created_at.desc(),
            Skill.name.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for ev, skill, repo in results:
        repo_name = repo.repo_name if repo else None
        items.append(
            ProjectEvidenceItem(
                evidence_id=ev.id,
                repository_id=ev.repo_id,
                repo_name=repo_name,
                skill_id=skill.id,
                skill_name=skill.name,
                canonical_slug=skill.slug,
                evidence_type=ev.evidence_type,
                artifact_path=ev.file_path,
                file_path=ev.file_path,
                artifact_name=ev.artifact_name,
                evidence_description=ev.evidence_description,
                matched_content=ev.matched_content,
                confidence_score=ev.confidence_score,
                evidence_metadata=ev.evidence_metadata or {},
                detected_at=ev.detected_at,
                created_at=ev.created_at,
            )
        )

    return ProjectEvidenceListResponse(
        data=items,
        meta=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.get(
    "/{evidence_id}",
    response_model=ProjectEvidenceDetailResponse,
    summary="Get Detailed Project Evidence Item by ID",
)
def get_evidence_detail(
    evidence_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = Query(None, description="Optional user ownership scope"),
    db: Session = Depends(get_db),
) -> ProjectEvidenceDetailResponse:
    """
    Retrieves full audit metadata and matched content for a specific evidence item.
    Returns 404 if not found.
    """
    query = (
        db.query(ProjectEvidence, Skill, GitHubRepository)
        .join(Skill, ProjectEvidence.skill_id == Skill.id)
        .outerjoin(GitHubRepository, ProjectEvidence.repo_id == GitHubRepository.id)
        .filter(ProjectEvidence.id == evidence_id)
    )
    if user_id:
        query = query.filter(ProjectEvidence.user_id == user_id)

    result = query.first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project evidence item with id '{evidence_id}' not found.",
        )

    ev, skill, repo = result
    repo_name = repo.repo_name if repo else None

    return ProjectEvidenceDetailResponse(
        data=ProjectEvidenceItem(
            evidence_id=ev.id,
            repository_id=ev.repo_id,
            repo_name=repo_name,
            skill_id=skill.id,
            skill_name=skill.name,
            canonical_slug=skill.slug,
            evidence_type=ev.evidence_type,
            artifact_path=ev.file_path,
            file_path=ev.file_path,
            artifact_name=ev.artifact_name,
            evidence_description=ev.evidence_description,
            matched_content=ev.matched_content,
            confidence_score=ev.confidence_score,
            evidence_metadata=ev.evidence_metadata or {},
            detected_at=ev.detected_at,
            created_at=ev.created_at,
        )
    )
