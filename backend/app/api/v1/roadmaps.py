"""
Static Skill Roadmap API Endpoints for SkillForge AI.
Phase 4: Static Roadmap API.

Exposes public and user-authenticated endpoints for the curated and canonical static roadmaps:
- GET /api/v1/roadmaps: List all 12 roadmap tracks
- GET /api/v1/roadmaps/{roadmap_id}: Full roadmap detail with stages, skills, resources, and practice problems
- GET /api/v1/roadmaps/{roadmap_id}/skills: Flat list of skills for a roadmap
- GET /api/v1/roadmaps/{roadmap_id}/skills/{skill_id}: Single roadmap skill detail
- GET /api/v1/users/me/roadmap-progress: Current user's roadmap learning progress map/summary
- PUT /api/v1/users/me/roadmap-progress/{skill_id}: Update user learning status for a skill
- PUT /api/v1/users/me/roadmap-progress/{skill_id}/problems/{problem_id}: Update user practice problem status

Strictly decoupled from P4 Personalized Roadmap (/api/v1/roadmap).
"""

from typing import Any, Dict, List, Optional, Union
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.v1.gaps import resolve_user_id, verify_user_exists
from app.api.v1.roadmap import get_roadmap_pdf
from app.db.database import get_db
from app.schemas.skill_roadmap import (
    RoadmapDetailResponse,
    RoadmapListResponse,
    RoadmapSkillItem,
    UserPracticeProgressResponse,
    UserPracticeProgressUpdateRequest,
    UserProgressResponse,
    UserProgressUpdateRequest,
    UserRoadmapProgressSummary,
)
from app.services.skill_roadmap_service import (
    InvalidProgressStatusError,
    PracticeProblemNotFoundError,
    PrerequisiteCycleError,
    RoadmapNotFoundError,
    RoadmapRelationshipError,
    RoadmapSkillNotFoundError,
    skill_roadmap_service,
)

# -----------------------------------------------------------------------------
# Identity Resolution Helper
# -----------------------------------------------------------------------------

def _resolve_effective_user_id(
    query_user_id: Optional[uuid.UUID],
    header_user_id: Optional[str],
) -> Optional[uuid.UUID]:
    """
    Resolves target user ID from query param or X-User-Id header for public endpoints.
    Re-maps 403 identity conflict to 400 Bad Request per main static roadmap convention.
    """
    try:
        return resolve_user_id(query_user_id, header_user_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=exc.detail,
            )
        raise exc


def _resolve_authenticated_user_id(
    query_user_id: Optional[uuid.UUID],
    header_user_id: Optional[str],
    db: Session,
) -> uuid.UUID:
    """
    Resolves and strictly authenticates candidate user identity for /users/me/* endpoints.
    Strictly requires the trusted X-User-Id header.
    Rejects missing header with 401 Unauthorized.
    Rejects malformed UUID in header with 422 Unprocessable Entity.
    Rejects conflicting query user_id with 400 Bad Request (IDOR protection).
    Verifies user exists in database (404 Not Found).
    """
    if not header_user_id or not header_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-User-Id header missing.",
        )

    try:
        authenticated_id = uuid.UUID(header_user_id.strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID format in X-User-Id header.",
        )

    if query_user_id is not None and query_user_id != authenticated_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cross-user access denied: target user_id does not match authenticated user context.",
        )

    verify_user_exists(db, authenticated_id)
    return authenticated_id


# -----------------------------------------------------------------------------
# Public Static Roadmaps Router
# -----------------------------------------------------------------------------

router = APIRouter(tags=["Static Skill Roadmaps"])


@router.get(
    "",
    response_model=RoadmapListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all static skill roadmaps in catalog",
    description=(
        "Retrieves all 12 static skill roadmaps across canonical and curated domains. "
        "Deterministic ordering: canonical tracks with market demand first, followed by curated tracks. "
        "Public endpoint: no authentication required."
    ),
)
def list_roadmaps(db: Session = Depends(get_db)) -> RoadmapListResponse:
    """Returns all 12 static roadmap domains with metadata and counts."""
    catalog_items = skill_roadmap_service.get_roadmap_catalog(db)
    return RoadmapListResponse(data=catalog_items, total=len(catalog_items))


router.add_api_route(
    "/{roadmap_id}/pdf",
    get_roadmap_pdf,
    methods=["GET"],
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Download Personalized Career Roadmap PDF",
    description=(
        "Assembles verified candidate evidence and deterministic roadmap milestones, "
        "synthesizes validated personalized career narratives via Gemini 2.5 Flash, "
        "and renders a publication-quality A4 PDF document. Strict candidate ownership enforced."
    ),
    tags=["Career Roadmaps"],
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Publication-quality personalized career roadmap PDF document.",
        },
        401: {"description": "Authentication required: missing or invalid X-User-Id header."},
        403: {"description": "Cross-user access denied (candidate ownership protection)."},
        404: {"description": "Roadmap or user not found."},
        422: {"description": "Validation error on roadmap UUID or X-User-Id format."},
        500: {"description": "Narrative reference integrity failure or PDF document compilation failure."},
        502: {"description": "Upstream AI narrative generation service failure."},
        504: {"description": "Upstream AI narrative generation gateway timeout."},
    },
)


@router.get(
    "/{roadmap_id}",
    response_model=RoadmapDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full static roadmap detail with stages and skills",
    description=(
        "Retrieves complete roadmap detail including stages, skills, prerequisites, resources, and practice problems. "
        "Supports 'curated' (stage hierarchy) or 'recommended' (prerequisite topological sort) ordering. "
        "Attaches user learning and practice progress when valid user context is provided. "
        "Public endpoint: browsing works without authentication."
    ),
)
def get_roadmap(
    roadmap_id: str,
    ordering: str = Query("curated", description="Ordering mode: curated or recommended"),
    user_id: Optional[uuid.UUID] = Query(None, description="Optional target user ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Optional authenticated user ID header"),
    db: Session = Depends(get_db),
) -> RoadmapDetailResponse:
    """Retrieves full roadmap hierarchy by slug or UUID."""
    clean_ordering = ordering.strip().lower()
    if clean_ordering not in {"curated", "recommended"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid ordering '{ordering}'. Allowed values: 'curated', 'recommended'.",
        )

    effective_user_id = _resolve_effective_user_id(user_id, x_user_id)
    if effective_user_id:
        verify_user_exists(db, effective_user_id)

    try:
        detail_data = skill_roadmap_service.get_roadmap_detail(
            db=db,
            roadmap_identifier=roadmap_id,
            user_id=effective_user_id,
            ordering=clean_ordering,
        )
        return RoadmapDetailResponse(data=detail_data)
    except RoadmapNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PrerequisiteCycleError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{roadmap_id}/skills",
    response_model=List[RoadmapSkillItem],
    status_code=status.HTTP_200_OK,
    summary="List all skills for a static roadmap",
    description=(
        "Retrieves a flat list of skills belonging to the specified roadmap. "
        "Preserves curated stage/skill order or recommended topological order. "
        "Public endpoint: browsing works without authentication."
    ),
)
def get_roadmap_skills(
    roadmap_id: str,
    ordering: str = Query("curated", description="Ordering mode: curated or recommended"),
    user_id: Optional[uuid.UUID] = Query(None, description="Optional target user ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> List[RoadmapSkillItem]:
    """Returns all skills belonging to the specified roadmap."""
    clean_ordering = ordering.strip().lower()
    if clean_ordering not in {"curated", "recommended"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid ordering '{ordering}'. Allowed values: 'curated', 'recommended'.",
        )

    effective_user_id = _resolve_effective_user_id(user_id, x_user_id)
    if effective_user_id:
        verify_user_exists(db, effective_user_id)

    try:
        detail = skill_roadmap_service.get_roadmap_detail(
            db=db,
            roadmap_identifier=roadmap_id,
            user_id=effective_user_id,
            ordering=clean_ordering,
        )
        if clean_ordering == "recommended" and detail.recommended_skills is not None:
            return detail.recommended_skills
        # Curated: flatten stages in order
        skills: List[RoadmapSkillItem] = []
        for stage in detail.stages:
            skills.extend(stage.skills)
        return skills
    except RoadmapNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PrerequisiteCycleError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{roadmap_id}/skills/{skill_id}",
    response_model=RoadmapSkillItem,
    status_code=status.HTTP_200_OK,
    summary="Get single static roadmap skill detail",
    description=(
        "Retrieves detailed information for a single roadmap skill, including prerequisites, "
        "learning resources, practice problems, and canonical skill references. "
        "Strictly verifies that the skill belongs to the requested roadmap. "
        "Public endpoint: browsing works without authentication."
    ),
)
def get_roadmap_skill_detail(
    roadmap_id: str,
    skill_id: str,
    user_id: Optional[uuid.UUID] = Query(None, description="Optional target user ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> RoadmapSkillItem:
    """Retrieves single roadmap skill detail and resources."""
    effective_user_id = _resolve_effective_user_id(user_id, x_user_id)
    if effective_user_id:
        verify_user_exists(db, effective_user_id)

    try:
        return skill_roadmap_service.get_roadmap_skill(
            db=db,
            roadmap_identifier=roadmap_id,
            skill_identifier=skill_id,
            user_id=effective_user_id,
        )
    except RoadmapNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RoadmapSkillNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RoadmapRelationshipError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# -----------------------------------------------------------------------------
# User Roadmap Progress Router
# -----------------------------------------------------------------------------

user_progress_router = APIRouter(prefix="/users/me/roadmap-progress", tags=["User Roadmap Progress"])


@user_progress_router.get(
    "",
    response_model=Union[UserRoadmapProgressSummary, Dict[str, str]],
    status_code=status.HTTP_200_OK,
    summary="Get current user's roadmap learning progress",
    description=(
        "Retrieves a mapping of {roadmap_skill_id: status} for the authenticated user. "
        "If 'roadmap_id' is supplied, optionally filters by roadmap. "
        "If 'summary=true' and 'roadmap_id' is supplied, returns domain progress metrics. "
        "Requires authenticated user identity via X-User-Id header or user_id query param."
    ),
)
def get_current_user_progress(
    roadmap_id: Optional[str] = Query(None, description="Optional roadmap ID or slug to filter progress or compute summary"),
    summary: bool = Query(False, description="If True and roadmap_id is provided, returns domain progress summary"),
    user_id: Optional[uuid.UUID] = Query(None, description="Optional target user ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user ID header"),
    db: Session = Depends(get_db),
) -> Any:
    """Returns progress mapping or summary for the authenticated user."""
    effective_user_id = _resolve_authenticated_user_id(user_id, x_user_id, db)

    if summary and roadmap_id:
        try:
            return skill_roadmap_service.get_user_roadmap_summary(
                db=db,
                user_id=effective_user_id,
                roadmap_identifier=roadmap_id,
            )
        except RoadmapNotFoundError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    try:
        progress_map = skill_roadmap_service.get_user_roadmap_progress(
            db=db,
            user_id=effective_user_id,
            roadmap_id=roadmap_id,
        )
        return {str(k): v for k, v in progress_map.items()}
    except RoadmapNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@user_progress_router.put(
    "/{skill_id}",
    response_model=UserProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user's learning status for a roadmap skill",
    description=(
        "Updates or creates the user's learning status (NOT_STARTED, LEARNING, DONE, SKIPPED) for a skill. "
        "Enforces user ownership, prevents duplicate records, and guarantees cross-user isolation. "
        "Requires authenticated user identity via X-User-Id header or user_id query param."
    ),
)
def update_current_user_progress(
    skill_id: str,
    payload: UserProgressUpdateRequest,
    user_id: Optional[uuid.UUID] = Query(None, description="Optional target user ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user ID header"),
    db: Session = Depends(get_db),
) -> UserProgressResponse:
    """Updates skill learning progress for authenticated user."""
    effective_user_id = _resolve_authenticated_user_id(user_id, x_user_id, db)

    try:
        updated = skill_roadmap_service.update_user_progress(
            db=db,
            user_id=effective_user_id,
            skill_id=skill_id,
            status=payload.status,
        )
        return UserProgressResponse(success=True, data=updated)
    except RoadmapSkillNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidProgressStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RoadmapRelationshipError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@user_progress_router.put(
    "/{skill_id}/problems/{problem_id}",
    response_model=UserPracticeProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user's practice problem progress",
    description=(
        "Updates or creates the user's status (NOT_STARTED, IN_PROGRESS, COMPLETED) for a practice problem. "
        "Sets completed_at timestamp on COMPLETED and clears it on transition away. "
        "Scopes duplicate problem IDs by roadmap_skill_id and guarantees cross-user isolation. "
        "Requires authenticated user identity via X-User-Id header or user_id query param."
    ),
)
def update_current_user_practice_progress(
    skill_id: str,
    problem_id: str,
    payload: UserPracticeProgressUpdateRequest,
    user_id: Optional[uuid.UUID] = Query(None, description="Optional target user ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user ID header"),
    db: Session = Depends(get_db),
) -> UserPracticeProgressResponse:
    """Updates practice problem progress for authenticated user."""
    effective_user_id = _resolve_authenticated_user_id(user_id, x_user_id, db)

    try:
        updated = skill_roadmap_service.update_user_practice_progress(
            db=db,
            user_id=effective_user_id,
            skill_id=skill_id,
            problem_id=problem_id,
            status=payload.status,
        )
        return UserPracticeProgressResponse(success=True, data=updated)
    except RoadmapSkillNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PracticeProblemNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidProgressStatusError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RoadmapRelationshipError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
