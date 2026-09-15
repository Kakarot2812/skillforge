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

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.ai.gemini.exceptions import GeminiTimeoutError
from app.ai.qwen.exceptions import (
    QwenAPIError,
    QwenConnectionError,
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
)
from app.ai.roadmap import AIRoadmapExplanationService, RoadmapPDFNarrativeService
from app.ai.roadmap.exceptions import (
    NarrativeGenerationError,
    NarrativeValidationError,
    ReferenceIntegrityError,
)
from app.api.v1.gaps import resolve_user_id, verify_user_exists
from app.db.database import get_db
from app.db.models import (
    CandidateRoadmap,
    GitHubRepository,
    MilestoneVerification,
    RoadmapMilestone,
)
from app.schemas.roadmap import (
    AIRoadmapExplainRequest,
    AIRoadmapExplainResponse,
    ApprovedResourceListResponse,
    RoadmapGenerateRequest,
    RoadmapResponse,
)
from app.services.demonstrated_skill_service import is_repo_owned_by_user
from app.services.resource_service import resource_service
from app.services.roadmap_engine import RoadmapDependencyCycleError, RoadmapError
from app.services.roadmap_pdf_context_service import roadmap_pdf_context_service
from app.services.roadmap_pdf_renderer import roadmap_pdf_renderer
from app.services.roadmap_service import roadmap_service
from app.services.verification_service import (
    ForkedRepositoryError,
    MilestoneRoadmapMismatchError,
    RepositoryOwnershipError,
    RoadmapOwnershipError,
    VerificationInfrastructureError,
    VerificationNotFoundError,
    VerificationSecurityError,
    verification_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Career Roadmaps"])


# -----------------------------------------------------------------------------
# P5-D Request & Response Schemas
# -----------------------------------------------------------------------------

class MilestoneVerifyRequest(BaseModel):
    repository_id: Optional[UUID] = Field(None, description="Candidate GitHub repository UUID")
    branch: Optional[str] = Field(None, description="Optional repository branch/ref (reserved)")

    model_config = ConfigDict(extra="forbid")


class RoadmapBatchVerifyRequest(BaseModel):
    repository_id: Optional[UUID] = Field(None, description="Optional repository UUID for batch verification")

    model_config = ConfigDict(extra="forbid")


class MilestoneVerificationResponse(BaseModel):
    id: UUID = Field(..., description="MilestoneVerification audit record UUID")
    milestone_id: UUID = Field(..., description="Roadmap milestone UUID")
    roadmap_id: UUID = Field(..., description="Candidate roadmap UUID")
    user_id: UUID = Field(..., description="Candidate user UUID")
    repository_id: UUID = Field(..., description="Verified GitHub repository UUID")
    commit_sha: str = Field(..., description="Server-resolved commit SHA")
    status: str = Field(..., description="Verification status: VERIFIED, PARTIAL, UNVERIFIED, or FAILED")
    confidence: Optional[float] = Field(None, description="Composite confidence score [0.0, 1.0]")
    details: Dict[str, Any] = Field(default_factory=dict, description="Bounded audit evaluation details")
    milestone_status: str = Field(..., description="Milestone status after verification")
    created_at: datetime = Field(..., description="Timestamp of verification")

    model_config = ConfigDict(extra="forbid")


class RoadmapBatchVerificationResponse(BaseModel):
    roadmap_id: UUID = Field(..., description="Candidate roadmap UUID")
    total_milestones: int = Field(..., description="Total milestones in roadmap")
    verified_count: int = Field(..., description="Count of VERIFIED milestones")
    partial_count: int = Field(..., description="Count of PARTIAL milestones")
    unverified_count: int = Field(..., description="Count of UNVERIFIED milestones")
    failed_count: int = Field(..., description="Count of FAILED milestones")
    results: List[MilestoneVerificationResponse] = Field(..., description="Ordered list of per-milestone verification results")

    model_config = ConfigDict(extra="forbid")


# -----------------------------------------------------------------------------
# Security & Token Helpers
# -----------------------------------------------------------------------------

FORBIDDEN_QUERY_KEYS = {
    "token",
    "pat",
    "access_token",
    "github_token",
    "bearer",
    "secret",
}


def validate_no_forbidden_query_params(request: Request) -> None:
    """Rejects requests containing prohibited sensitive token query parameters."""
    for key in request.query_params.keys():
        if key.lower() in FORBIDDEN_QUERY_KEYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sensitive token parameter '{key}' is prohibited in query parameters.",
            )


def extract_bearer_pat(authorization: Optional[str]) -> str:
    """
    Extracts the volatile personal access token from the Authorization header.
    Requires 'Bearer <token>'. Rejects malformed or missing headers.
    """
    if not authorization or not authorization.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header with GitHub personal access token.",
        )
    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
        )
    return parts[1].strip()


def map_failed_status_code(error_msg: str) -> int:
    """Maps infrastructure verification failures to appropriate HTTP status codes."""
    err_lower = error_msg.lower()
    if "rate limit" in err_lower or "429" in err_lower:
        return status.HTTP_429_TOO_MANY_REQUESTS
    if "timeout" in err_lower or "timed out" in err_lower or "504" in err_lower:
        return status.HTTP_504_GATEWAY_TIMEOUT
    if any(k in err_lower for k in ("502", "503", "unavailable", "bad gateway", "network", "upstream")):
        return status.HTTP_502_BAD_GATEWAY
    return status.HTTP_502_BAD_GATEWAY


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


@router.get(
    "/{roadmap_id}/pdf",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Download Personalized Career Roadmap PDF",
    description=(
        "Assembles verified candidate evidence and deterministic roadmap milestones, "
        "synthesizes validated personalized career narratives via Gemini 2.5 Flash, "
        "and renders a publication-quality A4 PDF document. Strict candidate ownership enforced."
    ),
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
def get_roadmap_pdf(
    roadmap_id: UUID = Path(..., description="Canonical CandidateRoadmap UUID"),
    download: bool = Query(False, description="If true, sets Content-Disposition: attachment; if false, sets inline preview"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated candidate user UUID context"),
    db: Session = Depends(get_db),
) -> Response:
    """
    Generates and returns the personalized career roadmap PDF for an authenticated candidate.
    Enforces strict candidate ownership (IDOR protection). Fails closed on integrity or provider failures.
    """
    # 1. Authenticate Request & Resolve User
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-User-Id header missing.",
        )
    try:
        authenticated_user_id = UUID(x_user_id.strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID format in X-User-Id header.",
        )

    verify_user_exists(db, authenticated_user_id)

    # 2. Build Verified Context (enforces roadmap existence and candidate ownership)
    context = roadmap_pdf_context_service.build_verified_context(
        db=db,
        roadmap_id=roadmap_id,
        authenticated_user_id=authenticated_user_id,
    )

    # 3. Generate Validated Personalized Narrative via Gemini 2.5 Flash
    narrative_svc = RoadmapPDFNarrativeService()
    try:
        validated_content = narrative_svc.generate_validated_narrative(context)
    except (ReferenceIntegrityError, NarrativeValidationError) as exc:
        logger.error("Roadmap narrative validation failed closed for roadmap %s: %s", roadmap_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Roadmap integrity validation failed.",
        )
    except NarrativeGenerationError as exc:
        logger.error("AI narrative generation failed for roadmap %s: %s", roadmap_id, exc)
        if isinstance(exc.original_exception, GeminiTimeoutError):
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Roadmap narrative generation timed out.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI narrative generation service unavailable.",
        )
    except Exception as exc:
        logger.error("Unexpected failure during narrative generation for roadmap %s: %s", roadmap_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI narrative generation service unavailable.",
        )

    # 4. Render Exact ReportLab A4 PDF Bytes
    try:
        pdf_bytes = roadmap_pdf_renderer.render(validated_content)
    except Exception as exc:
        logger.error("PDF compilation failed for roadmap %s: %s", roadmap_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF document compilation failed.",
        )

    # 5. Assemble HTTP Response
    disposition_type = "attachment" if download else "inline"
    safe_filename = f"skillforge-roadmap-{roadmap_id}.pdf"
    content_disposition = f'{disposition_type}; filename="{safe_filename}"'

    headers = {
        "Content-Disposition": content_disposition,
        "Cache-Control": "no-store",
    }

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers=headers,
    )


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


# -----------------------------------------------------------------------------
# P5-D: Deterministic Project Verification Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/{roadmap_id}/milestones/{milestone_id}/verify",
    response_model=MilestoneVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Roadmap Milestone via Candidate GitHub Repository",
    description=(
        "Executes deterministic project verification for a roadmap milestone. "
        "Requires volatile GitHub personal access token via 'Authorization: Bearer <PAT>' header. "
        "Strictly candidate-isolated; tokens are never persisted, logged, or returned."
    ),
)
def verify_milestone(
    roadmap_id: UUID,
    milestone_id: UUID,
    request: Request,
    payload: Optional[MilestoneVerifyRequest] = None,
    authorization: Optional[str] = Header(None, alias="Authorization", description="Bearer GitHub personal access token"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user context"),
    x_github_username: Optional[str] = Header(None, alias="X-GitHub-Username", description="Connected GitHub account handle"),
    user_id: Optional[UUID] = Query(None, description="Candidate user UUID"),
    db: Session = Depends(get_db),
) -> MilestoneVerificationResponse:
    """
    Verifies a roadmap milestone against candidate-owned GitHub repository.
    Enforces strict IDOR defense, fork rejection, and server-authoritative scoring.
    """
    # 1. Prohibit forbidden token query parameters
    validate_no_forbidden_query_params(request)

    # 2. Authenticate user context
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if not effective_user_id or not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for milestone verification.",
        )

    # 3. Extract volatile PAT from Authorization header
    token = extract_bearer_pat(authorization)

    # 4. Authorize roadmap ownership (IDOR defense)
    roadmap = db.query(CandidateRoadmap).filter(CandidateRoadmap.id == roadmap_id).first()
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Roadmap '{roadmap_id}' not found.",
        )
    if roadmap.user_id != effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-user access denied: target roadmap does not belong to authenticated user.",
        )

    # 5. Validate milestone exists and belongs to specified roadmap
    milestone = db.query(RoadmapMilestone).filter(RoadmapMilestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Milestone '{milestone_id}' not found.",
        )
    if milestone.roadmap_id != roadmap.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Milestone '{milestone_id}' does not belong to roadmap '{roadmap_id}'.",
        )

    connected_username = (
        (x_github_username.strip() if x_github_username and x_github_username.strip() else None)
        or (roadmap.summary_metadata or {}).get("github_username")
    )

    # 6. If repository_id specified in payload, validate ownership and fork status
    repo_id = payload.repository_id if payload else None
    if repo_id:
        repo = db.query(GitHubRepository).filter(GitHubRepository.id == repo_id).first()
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GitHub repository '{repo_id}' not found.",
            )
        if repo.user_id != effective_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-user access denied: repository does not belong to authenticated user.",
            )
        if repo.is_fork:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Repository '{repo.full_name or repo.repo_name}' is a fork. Forked repositories cannot be verified.",
            )
        if connected_username:
            repo_dict = {
                "repo_url": repo.repo_url,
                "full_name": repo.full_name,
                "owner": (repo.repo_metadata or {}).get("owner"),
                "repo_name": repo.repo_name,
            }
            if not is_repo_owned_by_user(repo_dict, connected_username):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Repository '{repo.full_name or repo.repo_name}' owner does not match connected GitHub username '{connected_username}'.",
                )

    # 7. Execute deterministic verification service
    try:
        result = verification_service.verify_milestone(
            db=db,
            user_id=effective_user_id,
            roadmap_id=roadmap.id,
            milestone_id=milestone.id,
            repository_id=repo_id,
            token=token,
            github_username=connected_username,
        )
    except RoadmapOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except MilestoneRoadmapMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RepositoryOwnershipError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ForkedRepositoryError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except VerificationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except VerificationInfrastructureError as exc:
        status_code = map_failed_status_code(str(exc))
        raise HTTPException(status_code=status_code, detail=f"External verification failure: {str(exc)}")

    # 8. Map infrastructure FAILED status to 5xx/429
    if result.status == "FAILED":
        err_msg = str(result.details.get("error", "GitHub verification infrastructure failure"))
        status_code = map_failed_status_code(err_msg)
        raise HTTPException(
            status_code=status_code,
            detail=f"Verification failed due to external infrastructure issue: {err_msg}",
        )

    # 9. Return typed verification response
    return MilestoneVerificationResponse(
        id=result.id,
        milestone_id=result.milestone_id,
        roadmap_id=result.roadmap_id,
        user_id=result.user_id,
        repository_id=result.repository_id,
        commit_sha=result.commit_sha,
        status=result.status,
        confidence=result.confidence,
        details=result.details,
        milestone_status=result.milestone_status,
        created_at=result.created_at,
    )


@router.get(
    "/{roadmap_id}/milestones/{milestone_id}/verification",
    response_model=MilestoneVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Milestone Verification",
    description=(
        "Retrieves the candidate's latest verification record for a milestone. "
        "Strictly candidate-isolated; does not require GitHub PAT and does not execute verification."
    ),
)
def get_latest_milestone_verification(
    roadmap_id: UUID,
    milestone_id: UUID,
    request: Request,
    user_id: Optional[UUID] = Query(None, description="Candidate user UUID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user context"),
    db: Session = Depends(get_db),
) -> MilestoneVerificationResponse:
    """
    Retrieves the most recent verification record for a roadmap milestone.
    Enforces strict candidate ownership (IDOR defense).
    """
    # 1. Prohibit forbidden token query parameters
    validate_no_forbidden_query_params(request)

    # 2. Authenticate user context
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if not effective_user_id or not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to query milestone verification.",
        )

    # 3. Authorize roadmap ownership
    roadmap = db.query(CandidateRoadmap).filter(CandidateRoadmap.id == roadmap_id).first()
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Roadmap '{roadmap_id}' not found.",
        )
    if roadmap.user_id != effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-user access denied: target roadmap does not belong to authenticated user.",
        )

    # 4. Verify milestone belongs to roadmap
    milestone = db.query(RoadmapMilestone).filter(RoadmapMilestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Milestone '{milestone_id}' not found.",
        )
    if milestone.roadmap_id != roadmap.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Milestone '{milestone_id}' does not belong to roadmap '{roadmap_id}'.",
        )

    # 5. Query latest verification for this candidate & milestone
    verification = (
        db.query(MilestoneVerification)
        .filter(
            MilestoneVerification.milestone_id == milestone.id,
            MilestoneVerification.roadmap_id == roadmap.id,
            MilestoneVerification.user_id == effective_user_id,
        )
        .order_by(MilestoneVerification.created_at.desc())
        .first()
    )

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No verification record found for milestone '{milestone_id}'.",
        )

    return MilestoneVerificationResponse(
        id=verification.id,
        milestone_id=verification.milestone_id,
        roadmap_id=verification.roadmap_id,
        user_id=verification.user_id,
        repository_id=verification.repository_id,
        commit_sha=verification.commit_sha,
        status=verification.status,
        confidence=verification.confidence,
        details=verification.details or {},
        milestone_status=milestone.status,
        created_at=verification.created_at,
    )


@router.post(
    "/{roadmap_id}/verify",
    response_model=RoadmapBatchVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Verify Roadmap Milestones",
    description=(
        "Sequentially and deterministically verifies all milestones for a candidate roadmap. "
        "Requires volatile GitHub PAT via 'Authorization: Bearer <PAT>' header. "
        "Strictly candidate-isolated; preserves independent audit records per milestone."
    ),
)
def batch_verify_roadmap(
    roadmap_id: UUID,
    request: Request,
    payload: Optional[RoadmapBatchVerifyRequest] = None,
    authorization: Optional[str] = Header(None, alias="Authorization", description="Bearer GitHub personal access token"),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id", description="Authenticated user context"),
    x_github_username: Optional[str] = Header(None, alias="X-GitHub-Username", description="Connected GitHub account handle"),
    user_id: Optional[UUID] = Query(None, description="Candidate user UUID"),
    db: Session = Depends(get_db),
) -> RoadmapBatchVerificationResponse:
    """
    Batch verifies all roadmap milestones sequentially in deterministic order.
    Preserves independent MilestoneVerification history records.
    """
    # 1. Prohibit forbidden token query parameters
    validate_no_forbidden_query_params(request)

    # 2. Authenticate user context
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if not effective_user_id or not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for batch roadmap verification.",
        )

    # 3. Extract volatile PAT from Authorization header
    token = extract_bearer_pat(authorization)

    # 4. Authorize roadmap ownership
    roadmap = db.query(CandidateRoadmap).filter(CandidateRoadmap.id == roadmap_id).first()
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Roadmap '{roadmap_id}' not found.",
        )
    if roadmap.user_id != effective_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-user access denied: target roadmap does not belong to authenticated user.",
        )

    connected_username = (
        (x_github_username.strip() if x_github_username and x_github_username.strip() else None)
        or (roadmap.summary_metadata or {}).get("github_username")
    )

    # 5. If specific repo requested, authorize repo ownership and fork rejection
    repo_id = payload.repository_id if payload else None
    if repo_id:
        repo = db.query(GitHubRepository).filter(GitHubRepository.id == repo_id).first()
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GitHub repository '{repo_id}' not found.",
            )
        if repo.user_id != effective_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-user access denied: repository does not belong to authenticated user.",
            )
        if repo.is_fork:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Repository '{repo.full_name or repo.repo_name}' is a fork. Forked repositories cannot be verified.",
            )
        if connected_username:
            repo_dict = {
                "repo_url": repo.repo_url,
                "full_name": repo.full_name,
                "owner": (repo.repo_metadata or {}).get("owner"),
                "repo_name": repo.repo_name,
            }
            if not is_repo_owned_by_user(repo_dict, connected_username):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Repository '{repo.full_name or repo.repo_name}' owner does not match connected GitHub username '{connected_username}'.",
                )

    # 6. Retrieve milestones in deterministic order
    milestones = (
        db.query(RoadmapMilestone)
        .filter(RoadmapMilestone.roadmap_id == roadmap.id)
        .order_by(RoadmapMilestone.order_index.asc())
        .all()
    )

    results: List[MilestoneVerificationResponse] = []
    verified_count = 0
    partial_count = 0
    unverified_count = 0
    failed_count = 0

    for milestone in milestones:
        try:
            res = verification_service.verify_milestone(
                db=db,
                user_id=effective_user_id,
                roadmap_id=roadmap.id,
                milestone_id=milestone.id,
                repository_id=repo_id,
                token=token,
                github_username=connected_username,
            )
            item = MilestoneVerificationResponse(
                id=res.id,
                milestone_id=res.milestone_id,
                roadmap_id=res.roadmap_id,
                user_id=res.user_id,
                repository_id=res.repository_id,
                commit_sha=res.commit_sha,
                status=res.status,
                confidence=res.confidence,
                details=res.details,
                milestone_status=res.milestone_status,
                created_at=res.created_at,
            )
            results.append(item)
            if res.status == "VERIFIED":
                verified_count += 1
            elif res.status == "PARTIAL":
                partial_count += 1
            elif res.status == "UNVERIFIED":
                unverified_count += 1
            elif res.status == "FAILED":
                failed_count += 1
        except (ForkedRepositoryError, RepositoryOwnershipError, RoadmapOwnershipError, VerificationSecurityError) as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
        except Exception as exc:
            failed_count += 1

    return RoadmapBatchVerificationResponse(
        roadmap_id=roadmap.id,
        total_milestones=len(milestones),
        verified_count=verified_count,
        partial_count=partial_count,
        unverified_count=unverified_count,
        failed_count=failed_count,
        results=results,
    )
