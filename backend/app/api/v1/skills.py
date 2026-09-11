import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.gaps import resolve_user_id

from app.db.database import get_db
from app.db.models import DemonstratedSkill, GitHubRepository, ProjectEvidence, Skill
from app.schemas.skill import ClaimedSkillsResponse, ClaimedSkillItem, PaginationMeta
from app.schemas.demonstrated_skill import (
    SupportingRepositoryItem,
    DemonstratedSkillSummaryItem,
    DemonstratedSkillListResponse,
    DemonstratedSkillDetailData,
    DemonstratedSkillDetailResponse,
)
from app.schemas.evidence import ProjectEvidenceItem
from app.services.skill_service import get_claimed_skills
from app.services.demonstrated_skill_service import demonstrated_skill_service

router = APIRouter(prefix="/skills", tags=["Skills"])


@router.get(
    "/claimed",
    response_model=ClaimedSkillsResponse,
    summary="List User Claimed Skills",
)
def list_claimed_skills(
    resume_id: Optional[uuid.UUID] = Query(None, description="Filter skills by specific resume ID"),
    limit: int = Query(20, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
) -> ClaimedSkillsResponse:
    """
    Retrieves candidate-claimed skills extracted from resumes or self-declared.
    Exposes canonical skill names, categories, raw mentions, and confidence scores.
    """
    claimed_records, total = get_claimed_skills(
        db=db,
        resume_id=resume_id,
        limit=limit,
        offset=offset,
    )

    items = [ClaimedSkillItem(**rec) for rec in claimed_records]

    return ClaimedSkillsResponse(
        data=items,
        meta=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
        ),
    )


@router.get(
    "/demonstrated",
    response_model=DemonstratedSkillListResponse,
    summary="List Aggregated Demonstrated Skills",
)
def list_demonstrated_skills(
    limit: int = Query(20, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    repository_id: Optional[uuid.UUID] = Query(None, description="Filter by supporting repository ID"),
    skill_id: Optional[uuid.UUID] = Query(None, description="Filter by canonical skill ID"),
    evidence_level: Optional[str] = Query(None, description="Filter by evidence tier (HIGH, MEDIUM, LOW)"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Candidate user context"),
    username: Optional[str] = Query(None, description="Filter by GitHub account username/owner"),
    db: Session = Depends(get_db),
) -> DemonstratedSkillListResponse:
    effective_user_id = resolve_user_id(user_id, x_user_id)

    if evidence_level:
        clean_level = evidence_level.strip().upper()
        if clean_level not in ("HIGH", "MEDIUM", "LOW"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid evidence_level '{evidence_level}'. Permitted values are 'HIGH', 'MEDIUM', 'LOW'.",
            )
        evidence_level = clean_level

    raw_items, total = demonstrated_skill_service.get_demonstrated_skills(
        db=db,
        user_id=effective_user_id,
        username=username,
        repository_id=repository_id,
        skill_id=skill_id,
        evidence_level=evidence_level,
        limit=limit,
        offset=offset,
    )

    items = []
    for it in raw_items:
        repos = [SupportingRepositoryItem(**r) for r in it.get("repositories", [])]
        items.append(
            DemonstratedSkillSummaryItem(
                skill_id=uuid.UUID(it["skill_id"]),
                skill_name=it["skill_name"],
                slug=it["slug"],
                category=it.get("category"),
                confidence_score=it["confidence_score"],
                evidence_level=it["evidence_level"],
                evidence_count=it["evidence_count"],
                repository_count=it["repository_count"],
                last_verified_at=it.get("last_verified_at"),
                repositories=repos,
                evidence_types=it.get("evidence_types", []),
            )
        )

    return DemonstratedSkillListResponse(
        data=items,
        meta=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.get(
    "/demonstrated/{skill_id}",
    response_model=DemonstratedSkillDetailResponse,
    summary="Get Detailed Demonstrated Skill with Auditable Evidence Trail",
)
def get_demonstrated_skill_detail(
    skill_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by user ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Candidate user context"),
    db: Session = Depends(get_db),
) -> DemonstratedSkillDetailResponse:
    """
    Returns the aggregated demonstrated skill details along with all supporting
    auditable project evidence items linking directly to source repository artifacts.
    """
    effective_user_id = resolve_user_id(user_id, x_user_id)

    # 1. Fetch demonstrated skill and canonical skill
    query = (
        db.query(DemonstratedSkill, Skill)
        .join(Skill, DemonstratedSkill.skill_id == Skill.id)
        .filter(DemonstratedSkill.skill_id == skill_id)
    )
    if effective_user_id:
        query = query.filter(DemonstratedSkill.user_id == effective_user_id)
    else:
        query = query.filter(DemonstratedSkill.user_id.is_(None))

    record = query.first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demonstrated skill with id '{skill_id}' not found.",
        )

    dem, skill = record
    meta = dem.skill_metadata or {}
    repos = [SupportingRepositoryItem(**r) for r in meta.get("repositories", [])]

    # 2. Fetch underlying auditable project evidence items
    ev_query = (
        db.query(ProjectEvidence, GitHubRepository)
        .outerjoin(GitHubRepository, ProjectEvidence.repo_id == GitHubRepository.id)
        .filter(ProjectEvidence.skill_id == skill_id)
    )
    if effective_user_id:
        ev_query = ev_query.filter(ProjectEvidence.user_id == effective_user_id)
    else:
        ev_query = ev_query.filter(ProjectEvidence.user_id.is_(None))

    ev_rows = ev_query.order_by(ProjectEvidence.confidence_score.desc()).all()
    if not ev_rows:
        db.delete(dem)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Demonstrated skill with id '{skill_id}' has no verified project evidence.",
        )

    evidence_items = []
    for ev, repo in ev_rows:
        repo_name = repo.repo_name if repo else None
        evidence_items.append(
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

    return DemonstratedSkillDetailResponse(
        data=DemonstratedSkillDetailData(
            skill_id=skill.id,
            skill_name=skill.name,
            slug=skill.slug,
            category=skill.category,
            description=skill.description,
            confidence_score=dem.confidence_score,
            evidence_level=dem.evidence_level,
            evidence_count=dem.evidence_count,
            repository_count=dem.repository_count,
            last_verified_at=dem.last_verified_at,
            repositories=repos,
            evidence_types=meta.get("evidence_types", []),
            evidence=evidence_items,
        )
    )
