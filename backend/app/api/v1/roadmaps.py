import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schemas.roadmap import (
    RoadmapDetailResponse,
    RoadmapListItem,
    RoadmapListResponse,
    RoadmapSkillItem,
    UserProgressResponse,
    UserProgressUpdateRequest,
    UserPracticeProgressResponse,
    UserPracticeProgressUpdateRequest,
)
from app.services.roadmap_service import roadmap_service

router = APIRouter(tags=["Skill Roadmaps"])


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
    """Verifies that the user exists in the database if user_id is provided."""
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{user_id}' not found.",
            )


@router.get(
    "",
    response_model=RoadmapListResponse,
    summary="List all Skill Roadmaps catalog",
)
def list_roadmaps(db: Session = Depends(get_db)) -> RoadmapListResponse:
    """
    Lists all available skill roadmaps across canonical and curated tracks.
    Returns domain, stage count, skill count, and whether market demand is available.
    """
    items = roadmap_service.get_roadmaps_catalog(db)
    return RoadmapListResponse(data=items, total=len(items))


@router.get(
    "/{roadmap_id}",
    response_model=RoadmapDetailResponse,
    summary="Get full Skill Roadmap with Stages and Personalization",
)
def get_roadmap(
    roadmap_id: uuid.UUID,
    ordering: str = Query("curated", description="Ordering mode: curated or recommended"),
    user_id: Optional[uuid.UUID] = Query(None, description="Optional target user ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> RoadmapDetailResponse:
    """
    Retrieves full roadmap structure with stages, skills, prerequisites, and learning resources.
    Integrates candidate skill gap statuses (STRONG, PARTIAL, MISSING) and priority scores for canonical roles.
    Supports 'curated' stage-by-stage ordering or 'recommended' prerequisite-safe topological ordering.
    """
    effective_user_id = resolve_user_id(user_id, x_user_id)
    verify_user_exists(db, effective_user_id)

    clean_ordering = ordering.strip().lower()
    if clean_ordering not in {"curated", "recommended"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid ordering mode '{ordering}'. Allowed: curated, recommended.",
        )

    try:
        detail_data = roadmap_service.get_roadmap_detail(
            db=db,
            roadmap_id=roadmap_id,
            user_id=effective_user_id,
            ordering=clean_ordering,
        )
        return RoadmapDetailResponse(data=detail_data)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )


@router.get(
    "/{roadmap_id}/skills",
    response_model=List[RoadmapSkillItem],
    summary="List all skills in a Roadmap",
)
def get_roadmap_skills(
    roadmap_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> List[RoadmapSkillItem]:
    """
    Retrieves a flat list of all skills across all stages of a roadmap.
    """
    effective_user_id = resolve_user_id(user_id, x_user_id)
    verify_user_exists(db, effective_user_id)

    try:
        detail = roadmap_service.get_roadmap_detail(
            db=db,
            roadmap_id=roadmap_id,
            user_id=effective_user_id,
            ordering="curated",
        )
        all_skills = []
        for stage in detail.stages:
            all_skills.extend(stage.skills)
        return all_skills
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )


@router.get(
    "/{roadmap_id}/skills/{skill_id}",
    response_model=RoadmapSkillItem,
    summary="Get single skill detail and resources",
)
def get_roadmap_skill_detail(
    roadmap_id: uuid.UUID,
    skill_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> RoadmapSkillItem:
    """
    Retrieves single roadmap skill detail: key topics, prerequisites, official documentation,
    YouTube learning resource, practice exercise, role relevance, and user progress.
    """
    effective_user_id = resolve_user_id(user_id, x_user_id)
    verify_user_exists(db, effective_user_id)

    try:
        return roadmap_service.get_roadmap_skill(
            db=db,
            roadmap_id=roadmap_id,
            skill_id=skill_id,
            user_id=effective_user_id,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )


# -----------------------------------------------------------------------------
# User Roadmap Progress Endpoints
# -----------------------------------------------------------------------------

user_progress_router = APIRouter(prefix="/users/me/roadmap-progress", tags=["User Roadmap Progress"])


@user_progress_router.get(
    "",
    response_model=Dict[str, str],
    summary="Get all roadmap progress for current user",
)
def get_current_user_progress(
    user_id: Optional[uuid.UUID] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Returns a dictionary mapping {roadmap_skill_id: status} for the authenticated user context.
    """
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user identity required via user_id query param or X-User-Id header.",
        )
    verify_user_exists(db, effective_user_id)

    return roadmap_service.get_user_progress_map(db=db, user_id=effective_user_id)


@user_progress_router.put(
    "/{skill_id}",
    response_model=UserProgressResponse,
    summary="Update roadmap skill progress for current user",
)
def update_current_user_progress(
    skill_id: uuid.UUID,
    payload: UserProgressUpdateRequest,
    user_id: Optional[uuid.UUID] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> UserProgressResponse:
    """
    Updates the learning progress status (NOT_STARTED, LEARNING, DONE, SKIPPED) for a skill.
    Guarantees user ownership and cross-user isolation.
    """
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user identity required via user_id query param or X-User-Id header.",
        )
    verify_user_exists(db, effective_user_id)

    try:
        updated = roadmap_service.update_user_progress(
            db=db,
            user_id=effective_user_id,
            skill_id=skill_id,
            status=payload.status,
        )
        return UserProgressResponse(success=True, data=updated)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@user_progress_router.put(
    "/{skill_id}/problems/{problem_id}",
    response_model=UserPracticeProgressResponse,
    summary="Update practice problem progress for current user",
)
def update_current_user_practice_progress(
    skill_id: uuid.UUID,
    problem_id: str,
    payload: UserPracticeProgressUpdateRequest,
    user_id: Optional[uuid.UUID] = Query(None),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> UserPracticeProgressResponse:
    """
    Updates progress (NOT_STARTED, IN_PROGRESS, COMPLETED) for a specific practice problem.
    Guarantees user ownership and cross-user isolation.
    """
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user identity required via user_id query param or X-User-Id header.",
        )
    verify_user_exists(db, effective_user_id)

    try:
        updated = roadmap_service.update_user_practice_progress(
            db=db,
            user_id=effective_user_id,
            skill_id=skill_id,
            problem_id=problem_id,
            status=payload.status,
        )
        return UserPracticeProgressResponse(success=True, data=updated)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
