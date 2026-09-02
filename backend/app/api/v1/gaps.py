import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schemas.demand import JobRoleItem
from app.schemas.skill_gap import (
    PrioritizedGapItem,
    PrioritizedGapsResponse,
    PrioritizedGapsResponseData,
    PrioritizedGapsSummary,
    SkillGapAnalyzeRequest,
    SkillGapItem,
    SkillGapMeta,
    SkillGapResponse,
    SkillGapResponseData,
    SkillGapSummary,
)
from app.schemas.skill_gap_evidence import SkillGapEvidenceResponse
from app.services.skill_gap_service import skill_gap_service
from app.services.skill_gap_evidence_service import skill_gap_evidence_service

router = APIRouter(tags=["Skill Gaps"])

VALID_GAP_STATUSES = {"STRONG", "PARTIAL", "MISSING"}
VALID_PRIORITY_LEVELS = {"HIGH", "MEDIUM", "LOW"}
VALID_ACTIONABLE_STATUSES = {"PARTIAL", "MISSING"}


def validate_location(location: str) -> str:
    """Validates that location is non-empty and within allowable length bounds."""
    if not location or not location.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Location cannot be blank or whitespace.",
        )
    stripped = location.strip()
    if len(stripped) > 64:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Location exceeds maximum length of 64 characters.",
        )
    return stripped


def resolve_user_id(
    query_user_id: Optional[uuid.UUID],
    header_user_id: Optional[str],
) -> Optional[uuid.UUID]:
    """
    Resolves target user ID from query param or X-User-Id header.
    Rejects conflicting IDs (IDOR protection).
    Validates UUID format.
    """
    header_uuid = None
    if header_user_id:
        try:
            header_uuid = uuid.UUID(header_user_id.strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid user ID format in X-User-Id header.",
            )

    if query_user_id and header_uuid:
        if query_user_id != header_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-user access denied: target user_id does not match authenticated user context.",
            )
        return query_user_id

    return query_user_id or header_uuid


def verify_user_exists(db: Session, user_id: Optional[uuid.UUID]) -> None:
    """
    If user_id is provided, verifies that the user exists in the database.
    Prevents foreign key violations and data leakage.
    """
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{user_id}' not found.",
            )


def validate_gap_status_filter(status_filter: Optional[str]) -> Optional[str]:
    """Validates optional gap status filter."""
    if status_filter is not None:
        norm = status_filter.strip().upper()
        if norm not in VALID_GAP_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status filter '{status_filter}'. Allowed: STRONG, PARTIAL, MISSING.",
            )
        return norm
    return None


def validate_priority_filters(
    priority_level: Optional[str],
    status_filter: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Validates optional priority level and actionable status filters."""
    norm_level = None
    if priority_level is not None:
        norm_level = priority_level.strip().upper()
        if norm_level not in VALID_PRIORITY_LEVELS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid priority_level filter '{priority_level}'. Allowed: HIGH, MEDIUM, LOW.",
            )
    norm_status = None
    if status_filter is not None:
        norm_status = status_filter.strip().upper()
        if norm_status not in VALID_ACTIONABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status filter '{status_filter}' for priorities. Allowed: MISSING, PARTIAL.",
            )
    return norm_level, norm_status


@router.get(
    "/{role_id}",
    response_model=SkillGapResponse,
    summary="Get Deterministic Skill Gap Analysis for Target Role",
)
def get_skill_gaps_for_role(
    role_id: uuid.UUID,
    location: str = Query("India", description="Geographic market location"),
    status_filter: Optional[str] = Query(None, alias="status", description="Optional status filter: STRONG, PARTIAL, MISSING"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Optional page size limit (1-100)"),
    offset: int = Query(0, ge=0, description="Pagination offset (>= 0)"),
    user_id: Optional[uuid.UUID] = Query(None, description="Optional user ID scope"),
    include_resume: bool = Query(True, description="Whether to include resume claims"),
    include_github: bool = Query(True, description="Whether to include GitHub demonstrated evidence"),
    username: Optional[str] = Query(None, description="Optional GitHub username scope"),
    resume_id: Optional[uuid.UUID] = Query(None, description="Optional specific resume ID scope"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> SkillGapResponse:
    """
    Computes and returns the candidate's deterministic skill gap analysis against a canonical target role.
    Combines:
    - Industry demand requirements for the role
    - Candidate resume claims
    - Candidate GitHub demonstrated evidence
    Classifies each skill into STRONG, PARTIAL, or MISSING.
    Supports optional status filtering and pagination.
    """
    clean_location = validate_location(location)
    clean_status = validate_gap_status_filter(status_filter)
    effective_user_id = resolve_user_id(user_id, x_user_id)
    verify_user_exists(db, effective_user_id)

    try:
        role, summary, items = skill_gap_service.compute_and_persist_skill_gaps(
            db=db,
            role_id=role_id,
            user_id=effective_user_id,
            location=clean_location,
            include_resume=include_resume,
            include_github=include_github,
            github_username=username,
            resume_id=resume_id,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )

    # Apply status filter if requested
    if clean_status:
        items = [s for s in items if s.status == clean_status]

    # Apply pagination if limit is specified
    if limit is not None:
        items = items[offset : offset + limit]

    role_item = JobRoleItem(
        role_id=role.id,
        title=role.title,
        slug=role.slug,
        category=role.category,
        description=role.description,
    )

    return SkillGapResponse(
        data=SkillGapResponseData(
            role=role_item,
            location=clean_location,
            summary=summary,
            skills=items,
        ),
        meta=SkillGapMeta(
            user_id=effective_user_id,
            location=clean_location,
            calculated_at=datetime.now(timezone.utc).isoformat(),
            data_freshness="2026-09-01",
            scoring_version="v1",
        ),
    )


@router.get(
    "/{role_id}/priorities",
    response_model=PrioritizedGapsResponse,
    summary="Get Deterministic Prioritized Skill Gaps for Target Role",
)
def get_prioritized_gaps_for_role(
    role_id: uuid.UUID,
    location: str = Query("India", description="Geographic market location"),
    priority_level: Optional[str] = Query(None, description="Filter by priority tier: HIGH, MEDIUM, LOW"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by gap severity: MISSING, PARTIAL"),
    limit: Optional[int] = Query(None, ge=1, le=100, description="Optional page size limit (1-100)"),
    offset: int = Query(0, ge=0, description="Pagination offset (>= 0)"),
    user_id: Optional[uuid.UUID] = Query(None, description="Optional user ID scope"),
    include_resume: bool = Query(True, description="Whether to include resume claims"),
    include_github: bool = Query(True, description="Whether to include GitHub demonstrated evidence"),
    username: Optional[str] = Query(None, description="Optional GitHub username scope"),
    resume_id: Optional[uuid.UUID] = Query(None, description="Optional specific resume ID scope"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> PrioritizedGapsResponse:
    """
    Retrieves candidate's deterministically prioritized actionable skill gaps (MISSING and PARTIAL only).
    STRONG skills are excluded.
    Prioritization combines:
    - Gap severity (MISSING = 1.0, PARTIAL = 0.5)
    - Normalized market growth signal
    - Database-derived industry demand score (70% demand, 30% growth signal)
    Supports optional priority_level and status filtering as well as pagination.
    """
    clean_location = validate_location(location)
    norm_prio, norm_status = validate_priority_filters(priority_level, status_filter)
    effective_user_id = resolve_user_id(user_id, x_user_id)
    verify_user_exists(db, effective_user_id)

    try:
        role, summary, items = skill_gap_service.get_prioritized_gaps(
            db=db,
            role_id=role_id,
            user_id=effective_user_id,
            location=clean_location,
            include_resume=include_resume,
            include_github=include_github,
            github_username=username,
            resume_id=resume_id,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )

    # Apply priority_level filter if requested
    if norm_prio:
        items = [g for g in items if g.priority_level == norm_prio]

    # Apply status filter if requested
    if norm_status:
        items = [g for g in items if g.status == norm_status]

    # Apply pagination if limit is specified
    if limit is not None:
        items = items[offset : offset + limit]

    role_item = JobRoleItem(
        role_id=role.id,
        title=role.title,
        slug=role.slug,
        category=role.category,
        description=role.description,
    )

    return PrioritizedGapsResponse(
        data=PrioritizedGapsResponseData(
            role=role_item,
            location=clean_location,
            summary=summary,
            gaps=items,
        ),
        meta=SkillGapMeta(
            user_id=effective_user_id,
            location=clean_location,
            calculated_at=datetime.now(timezone.utc).isoformat(),
            data_freshness="2026-09-01",
            scoring_version="v1",
        ),
    )


@router.post(
    "/analyze",
    response_model=SkillGapResponse,
    summary="Execute Deterministic Skill Gap Analysis",
)
def analyze_skill_gaps(
    payload: SkillGapAnalyzeRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> SkillGapResponse:
    """
    Executes skill gap analysis for a target canonical role and candidate evidence profile.
    Deterministic, auditable, and idempotent.
    """
    effective_user_id = resolve_user_id(payload.user_id, x_user_id)
    verify_user_exists(db, effective_user_id)
    clean_location = validate_location(payload.location)

    try:
        role, summary, items = skill_gap_service.compute_and_persist_skill_gaps(
            db=db,
            role_id=payload.target_role_id,
            user_id=effective_user_id,
            location=clean_location,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )

    role_item = JobRoleItem(
        role_id=role.id,
        title=role.title,
        slug=role.slug,
        category=role.category,
        description=role.description,
    )

    return SkillGapResponse(
        data=SkillGapResponseData(
            role=role_item,
            location=clean_location,
            summary=summary,
            skills=items,
        ),
        meta=SkillGapMeta(
            user_id=effective_user_id,
            location=clean_location,
            calculated_at=datetime.now(timezone.utc).isoformat(),
            data_freshness="2026-09-01",
            scoring_version="v1",
        ),
    )


@router.get(
    "/{role_id}/skills/{skill_id}/evidence",
    response_model=SkillGapEvidenceResponse,
    summary="Get Detailed Audit Evidence Chain for Specific Skill Gap",
)
def get_gap_evidence_for_skill(
    role_id: uuid.UUID,
    skill_id: uuid.UUID,
    location: str = Query("India", description="Geographic market location"),
    user_id: Optional[uuid.UUID] = Query(None, description="Optional user ID scope"),
    include_resume: bool = Query(True, description="Whether to include resume claims"),
    include_github: bool = Query(True, description="Whether to include GitHub demonstrated evidence"),
    username: Optional[str] = Query(None, description="Optional GitHub username scope"),
    resume_id: Optional[uuid.UUID] = Query(None, description="Optional specific resume ID scope"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> SkillGapEvidenceResponse:
    """
    Retrieves the complete auditable evidence chain for a specific skill gap:
    1. Candidate Resume Claims (from user_claimed_skills and resumes)
    2. Candidate GitHub Demonstrated Code Artifacts (from demonstrated_skills and project_evidence)
    3. Canonical Market Demand & YoY Growth (from skill_demand)
    4. Deterministic Reasoning explaining why the status and priority were assigned.
    """
    clean_location = validate_location(location)
    effective_user_id = resolve_user_id(user_id, x_user_id)
    verify_user_exists(db, effective_user_id)

    try:
        evidence_data = skill_gap_evidence_service.get_gap_evidence(
            db=db,
            role_id=role_id,
            skill_id=skill_id,
            user_id=effective_user_id,
            location=clean_location,
            include_resume=include_resume,
            include_github=include_github,
            github_username=username,
            resume_id=resume_id,
        )
    except (KeyError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )

    return SkillGapEvidenceResponse(
        data=evidence_data,
        meta=SkillGapMeta(
            user_id=effective_user_id,
            location=clean_location,
            calculated_at=datetime.now(timezone.utc).isoformat(),
            data_freshness="2026-09-01",
            scoring_version="v1",
        ),
    )
