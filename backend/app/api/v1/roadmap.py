"""
API router for SkillForge AI Personalized Roadmap + Resources.
Post-MVP Phase 4.

Endpoints:
- POST /api/v1/roadmap/generate — Generate canonical roadmap (in-memory if anonymous, persisted if authenticated).
- GET  /api/v1/roadmap/{id}     — Retrieve persisted roadmap by ID (strictly isolated to authenticated owner).
- GET  /api/v1/roadmap/active   — Retrieve candidate's active roadmap for target role.
- POST /api/v1/roadmap/{id}/explain — Non-authoritative Qwen explanation of canonical roadmap.
- GET  /api/v1/roadmap/resources/{skill_id} — Query approved curated learning resources for a skill.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.qwen.exceptions import (
    QwenAPIError,
    QwenConnectionError,
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
)
from app.ai.roadmap import AIRoadmapExplanationService
from app.api.v1.gaps import resolve_user_id
from app.db.database import get_db
from app.schemas.roadmap import (
    AIRoadmapExplainRequest,
    AIRoadmapExplainResponse,
    ApprovedResourceListResponse,
    RoadmapGenerateRequest,
    RoadmapResponse,
)
from app.services.resource_service import resource_service
from app.services.roadmap_engine import RoadmapDependencyCycleError, RoadmapError
from app.services.roadmap_service import roadmap_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Career Roadmaps"])


@router.post(
    "/generate",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Personalized Career Roadmap",
    description=(
        "Converts verified skill gaps, priority scores, and explicit prerequisite DAG constraints "
        "into a sequenced learning roadmap. Fully deterministic; no LLM call is made. "
        "Authenticated candidates have their roadmap persisted; anonymous requests execute in-memory."
    ),
)
def generate_roadmap(
    payload: RoadmapGenerateRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user context"),
    db: Session = Depends(get_db),
) -> RoadmapResponse:
    """Generates a deterministic career roadmap for the candidate and target role."""
    effective_user_id = resolve_user_id(payload.user_id, x_user_id)

    try:
        roadmap_data = roadmap_service.generate_candidate_roadmap(
            db=db,
            request=payload,
            resolved_user_id=effective_user_id,
        )
    except RoadmapDependencyCycleError as exc:
        logger.error("Dependency cycle detected during roadmap generation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except RoadmapError as exc:
        logger.error("Roadmap engine error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return RoadmapResponse(
        data=roadmap_data,
        meta={
            "persisted": roadmap_data.persisted,
            "deterministic": True,
            "roadmap_version": roadmap_data.roadmap_version,
        },
    )


@router.get(
    "/active",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Active Roadmap for Role",
    description="Retrieves the candidate's active persisted roadmap for a target career role. Requires authentication.",
)
def get_active_roadmap(
    role_id: UUID = Query(..., description="Target job role UUID"),
    user_id: Optional[UUID] = Query(None, description="Candidate user UUID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user context"),
    db: Session = Depends(get_db),
) -> RoadmapResponse:
    """Retrieves active persisted roadmap for target role."""
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to query persisted active roadmaps.",
        )

    roadmap_data = roadmap_service.get_active_roadmap(
        db=db,
        role_id=role_id,
        resolved_user_id=effective_user_id,
    )
    return RoadmapResponse(data=roadmap_data)


@router.get(
    "/{roadmap_id}",
    response_model=RoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Roadmap By ID",
    description="Retrieves a persisted canonical roadmap by ID. Enforces strict candidate ownership (IDOR defense).",
)
def get_roadmap_by_id(
    roadmap_id: UUID,
    user_id: Optional[UUID] = Query(None, description="Candidate user UUID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user context"),
    db: Session = Depends(get_db),
) -> RoadmapResponse:
    """Retrieves persisted roadmap by ID with candidate ownership verification."""
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to query persisted roadmaps by ID.",
        )

    roadmap_data = roadmap_service.get_roadmap_by_id(
        db=db,
        roadmap_id=roadmap_id,
        resolved_user_id=effective_user_id,
    )
    return RoadmapResponse(data=roadmap_data)


@router.post(
    "/{roadmap_id}/explain",
    response_model=AIRoadmapExplainResponse,
    status_code=status.HTTP_200_OK,
    summary="AI Roadmap Explanation & Guidance",
    description=(
        "Generates non-authoritative study guidance and milestone reasoning over the canonical roadmap using local Qwen 3 8B. "
        "Never alters milestone ordering, priority scores, or required skills."
    ),
)
def explain_roadmap(
    roadmap_id: UUID,
    payload: AIRoadmapExplainRequest = AIRoadmapExplainRequest(),
    user_id: Optional[UUID] = Query(None, description="Candidate user UUID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user context"),
    db: Session = Depends(get_db),
) -> AIRoadmapExplainResponse:
    """Explains a canonical roadmap using local Qwen 3 8B."""
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if not effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access roadmap AI coaching.",
        )

    roadmap_data = roadmap_service.get_roadmap_by_id(
        db=db,
        roadmap_id=roadmap_id,
        resolved_user_id=effective_user_id,
    )

    explainer = AIRoadmapExplanationService()
    try:
        return explainer.explain(
            roadmap=roadmap_data,
            user_query=payload.user_query,
            temperature=payload.temperature,
        )
    except (QwenConnectionError, QwenModelNotFoundError) as exc:
        logger.error("AI service offline for roadmap explanation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Local AI coaching service is currently offline: {str(exc)}. Your canonical roadmap remains unaffected.",
        )
    except QwenTimeoutError as exc:
        logger.error("AI service timed out for roadmap explanation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Local AI coaching request timed out. Your canonical roadmap remains unaffected.",
        )
    except (QwenAPIError, QwenResponseError) as exc:
        logger.error("AI service generation failure: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Local AI explanation generation failed: {str(exc)}.",
        )
    except Exception as exc:
        logger.error("Unexpected error in roadmap explanation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal roadmap explanation error: {str(exc)}",
        )
    finally:
        explainer.close()


@router.get(
    "/resources/{skill_id}",
    response_model=ApprovedResourceListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Approved Resources by Skill",
    description="Retrieves curated, approved learning materials for a canonical skill.",
)
def get_resources_by_skill(
    skill_id: UUID,
    db: Session = Depends(get_db),
) -> ApprovedResourceListResponse:
    """Retrieves approved learning resources for a skill."""
    return resource_service.get_resources_by_skill(db=db, skill_id=skill_id)
