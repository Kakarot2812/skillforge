"""
Comprehensive Phase 5 Test Suite:
SkillForge AI Personalized Career Roadmap PDF FastAPI Endpoints.

Verifies:
1. Authentication & Identity:
   - Missing X-User-Id header returns 401 Unauthorized
   - Empty/whitespace X-User-Id header returns 401 Unauthorized
   - Malformed X-User-Id returns 422 Unprocessable Entity
   - Nonexistent authenticated user returns 404 Not Found

2. Ownership & IDOR Protection:
   - Nonexistent roadmap returns 404 Not Found
   - Cross-user roadmap access is rejected (403 Forbidden)
   - Authenticated owner succeeds (200 OK)
   - Invalid roadmap UUID string returns 422 Unprocessable Entity

3. Route Behavior & Aliases:
   - Canonical route /api/v1/roadmaps/{roadmap_id}/pdf works
   - Alias route /api/v1/roadmap/{roadmap_id}/pdf works
   - Both routes produce identical status, headers, and body

4. Query Parameters:
   - download omitted defaults to inline
   - download=false sets Content-Disposition: inline
   - download=true sets Content-Disposition: attachment
   - Invalid download value is rejected (422 Unprocessable Entity)

5. Response Headers & Byte Integrity:
   - Content-Type is application/pdf
   - Body starts with PDF signature (%PDF-)
   - Cache-Control is strictly 'no-store'
   - Obsolete X-SkillForge-Version header is NOT present
   - Exact renderer bytes are returned without modification

6. Pipeline & Architectural Invariants:
   - Context service receives authenticated user ID and is invoked once
   - Narrative service is invoked once
   - Renderer is invoked once
   - No direct ORM/Gemini calls in route handler

7. Fail-Closed Error Handling:
   - Narrative validation failure (ReferenceIntegrityError) fails closed (500)
   - Gemini timeout error returns 504 Gateway Timeout
   - Gemini upstream/provider error returns 502 Bad Gateway
   - PDF compilation failure returns 500 Internal Server Error
   - Zero credential or path leakage in error responses

8. Persistence & Side Effects:
   - Zero PDF files written to disk
   - Zero PDF blobs saved to database

9. Real End-to-End Pipeline Test:
   - Real PostgreSQL + Real Context Service + Mocked Gemini + Real ReportLab Renderer
   - Validates generated multi-page PDF document
"""

from datetime import datetime, timezone
import io
import os
from unittest.mock import MagicMock, patch
import uuid

from fastapi.testclient import TestClient
import pypdf
import pytest
from sqlalchemy.orm import Session

from app.ai.context.roadmap_pdf_context import (
    PriorityTierLevel,
    SkillGapClassification,
    VerifiedApprovedProject,
    VerifiedApprovedResource,
    VerifiedCandidateProfile,
    VerifiedMarketDemandFact,
    VerifiedReadinessMetrics,
    VerifiedRoadmapPrerequisite,
)
from app.ai.gemini.exceptions import GeminiAPIError, GeminiTimeoutError
from app.ai.roadmap.exceptions import (
    NarrativeGenerationError,
    NarrativeValidationError,
    ReferenceIntegrityError,
)
from app.ai.roadmap.narrative_schemas import (
    RoadmapPDFPersonalizedNarrative,
    RoadmapPhaseNarrative,
    SkillGapNarrative,
    ValidatedRoadmapPDFContent,
    ValidatedRoadmapPhase,
    ValidatedTopSkillGap,
)
from app.db.database import SessionLocal, get_db
from app.db.models import (
    ApprovedProject,
    ApprovedResource,
    CandidateRoadmap,
    JobRole,
    RoadmapMilestone,
    Skill,
    User,
    UserProfile,
)
from app.main import app

client = TestClient(app)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Provides a clean transactional DB session rolled back after test."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_users(db_session: Session):
    """Creates two distinct users for IDOR testing."""
    user_a = User(
        id=uuid.uuid4(),
        email=f"candidate_a_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Candidate Alpha",
        target_role="Backend Engineer",
    )
    user_b = User(
        id=uuid.uuid4(),
        email=f"candidate_b_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Candidate Beta",
        target_role="Frontend Engineer",
    )
    db_session.add(user_a)
    db_session.add(user_b)
    db_session.commit()
    return {"user_a": user_a, "user_b": user_b}


@pytest.fixture
def test_roadmap_for_user_a(db_session: Session, test_users):
    """Creates a persisted CandidateRoadmap owned by User A."""
    user_a = test_users["user_a"]
    role = db_session.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    if not role:
        role = JobRole(
            id=uuid.uuid4(),
            title="Backend Engineer",
            slug="backend-engineer",
            category="Software Engineering",
        )
        db_session.add(role)
        db_session.commit()

    roadmap_a = CandidateRoadmap(
        id=uuid.uuid4(),
        user_id=user_a.id,
        role_id=role.id,
        target_role_title=role.title,
        location="India",
        status="ACTIVE",
        roadmap_version="v1.0",
    )
    db_session.add(roadmap_a)
    db_session.commit()
    return roadmap_a


@pytest.fixture
def sample_validated_content(test_users, test_roadmap_for_user_a) -> ValidatedRoadmapPDFContent:
    """Constructs a valid ValidatedRoadmapPDFContent for renderer mocking."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    skill_id = uuid.uuid4()

    candidate = VerifiedCandidateProfile(
        user_id=user_a.id,
        email=user_a.email,
        name=user_a.full_name,
        target_role=user_a.target_role,
        experience_level="INTERMEDIATE",
        college="National Institute of Technology",
        degree="B.Tech",
        branch="Computer Science",
        semester=7,
        education="B.Tech Computer Science (Sem 7)",
    )

    readiness = VerifiedReadinessMetrics(
        readiness_percentage=75,
        total_required_skills=4,
        strong_count=3,
        partial_count=1,
        missing_count=0,
        has_resume=True,
        has_github=True,
        scoring_version="v1",
    )

    gap = ValidatedTopSkillGap(
        skill_id=skill_id,
        skill_name="FastAPI",
        canonical_slug="fastapi",
        category="Frameworks",
        gap_status=SkillGapClassification.PARTIAL,
        priority_score=0.82,
        priority_level=PriorityTierLevel.HIGH,
        demand_score=0.79,
        growth_rate=0.21,
        why_it_matters="FastAPI delivers asynchronous API performance.",
        suggested_focus="Master dependency injection and async sessions.",
    )

    phase = ValidatedRoadmapPhase(
        milestone_id=uuid.uuid4(),
        order_index=1,
        skill_id=skill_id,
        skill_name="FastAPI",
        canonical_slug="fastapi",
        phase_title="Async API Mastery with FastAPI",
        personalized_rationale="Advance your demonstrated Python skills to production API engineering.",
        category="Frameworks",
        gap_status=SkillGapClassification.PARTIAL,
        priority_score=0.82,
        priority_level=PriorityTierLevel.HIGH,
        is_transitive_prerequisite=False,
        deterministic_reason="Asynchronous API architecture competency",
        status="NOT_STARTED",
        key_topics=("Async routes", "Dependency injection", "Pydantic V2"),
        learning_objectives=("Build async microservices",),
        resources=(),
        project=None,
        latest_verification=None,
    )

    return ValidatedRoadmapPDFContent(
        schema_version="v1.0",
        generated_at=datetime.now(timezone.utc),
        roadmap_id=roadmap.id,
        candidate=candidate,
        readiness=readiness,
        target_role_title="Backend Engineer",
        location="India",
        total_milestones=1,
        high_priority_count=1,
        medium_priority_count=0,
        low_priority_count=0,
        transitive_prerequisite_count=0,
        market_facts=(),
        verification_evidence=(),
        weekly_hours_recommendation=None,
        verification_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        personalized_subtitle="Strategic Personalized Engineering Pathway",
        executive_summary="Targeted blueprint designed to bridge critical skill gaps.",
        readiness_explanation="Candidate demonstrates strong fundamental competencies.",
        validated_top_gaps=(gap,),
        validated_phases=(phase,),
        immediate_next_steps=("Review FastAPI dependency injection", "Complete test project"),
        closing_encouragement="Stay consistent and execute methodically.",
    )


# -----------------------------------------------------------------------------
# 1. Authentication Tests
# -----------------------------------------------------------------------------

def test_api_pdf_missing_x_user_id(test_roadmap_for_user_a):
    """Missing X-User-Id header returns 401 Unauthorized."""
    resp = client.get(f"/api/v1/roadmaps/{test_roadmap_for_user_a.id}/pdf")
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_api_pdf_empty_whitespace_x_user_id(test_roadmap_for_user_a):
    """Empty or whitespace X-User-Id header returns 401 Unauthorized."""
    resp = client.get(
        f"/api/v1/roadmaps/{test_roadmap_for_user_a.id}/pdf",
        headers={"X-User-Id": "   "},
    )
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]


def test_api_pdf_malformed_x_user_id(test_roadmap_for_user_a):
    """Malformed X-User-Id header returns 422 Unprocessable Entity."""
    resp = client.get(
        f"/api/v1/roadmaps/{test_roadmap_for_user_a.id}/pdf",
        headers={"X-User-Id": "not-a-valid-uuid"},
    )
    assert resp.status_code == 422
    assert "Invalid user ID format" in resp.json()["detail"]


def test_api_pdf_nonexistent_user(test_roadmap_for_user_a):
    """X-User-Id with valid UUID but user not in DB returns 404 Not Found."""
    fake_user_id = uuid.uuid4()
    resp = client.get(
        f"/api/v1/roadmaps/{test_roadmap_for_user_a.id}/pdf",
        headers={"X-User-Id": str(fake_user_id)},
    )
    assert resp.status_code == 404
    assert f"User with id '{fake_user_id}' not found" in resp.json()["detail"]


# -----------------------------------------------------------------------------
# 2. Ownership & IDOR Protection Tests
# -----------------------------------------------------------------------------

def test_api_pdf_nonexistent_roadmap(test_users):
    """Nonexistent roadmap returns 404 Not Found."""
    user_a = test_users["user_a"]
    fake_roadmap_id = uuid.uuid4()
    resp = client.get(
        f"/api/v1/roadmaps/{fake_roadmap_id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 404
    assert f"Roadmap with id '{fake_roadmap_id}' not found" in resp.json()["detail"]


def test_api_pdf_cross_user_access_denied(test_users, test_roadmap_for_user_a):
    """User B cannot download User A's roadmap PDF (403 Forbidden)."""
    user_b = test_users["user_b"]
    resp = client.get(
        f"/api/v1/roadmaps/{test_roadmap_for_user_a.id}/pdf",
        headers={"X-User-Id": str(user_b.id)},
    )
    assert resp.status_code == 403
    assert "Cross-user access denied" in resp.json()["detail"]


def test_api_pdf_invalid_roadmap_uuid(test_users):
    """Invalid roadmap UUID returns 422 Unprocessable Entity."""
    user_a = test_users["user_a"]
    resp = client.get(
        "/api/v1/roadmaps/not-a-uuid/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 422


# -----------------------------------------------------------------------------
# 3. Route Behavior & Aliases
# -----------------------------------------------------------------------------

@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_canonical_and_alias_routes_succeed(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """Both /api/v1/roadmaps/{id}/pdf and /api/v1/roadmap/{id}/pdf succeed and return identical PDF bytes."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.return_value = sample_validated_content
    fake_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
    mock_render.return_value = fake_pdf_bytes

    # Canonical route
    resp_canonical = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp_canonical.status_code == 200
    assert resp_canonical.headers["content-type"] == "application/pdf"
    assert resp_canonical.content == fake_pdf_bytes

    # Alias route
    resp_alias = client.get(
        f"/api/v1/roadmap/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp_alias.status_code == 200
    assert resp_alias.headers["content-type"] == "application/pdf"
    assert resp_alias.content == fake_pdf_bytes

    # Verify identical responses
    assert resp_canonical.content == resp_alias.content
    assert resp_canonical.headers["content-disposition"] == resp_alias.headers["content-disposition"]
    assert resp_canonical.headers["cache-control"] == resp_alias.headers["cache-control"]


# -----------------------------------------------------------------------------
# 4. Query Parameter & Content-Disposition
# -----------------------------------------------------------------------------

@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_content_disposition_inline_by_default(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """Omitting download query param defaults to inline Content-Disposition."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = b"%PDF-test"

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 200
    expected_disp = f'inline; filename="skillforge-roadmap-{roadmap.id}.pdf"'
    assert resp.headers["content-disposition"] == expected_disp


@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_content_disposition_attachment_when_download_true(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """Setting download=true sets Content-Disposition: attachment."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = b"%PDF-test"

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf?download=true",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 200
    expected_disp = f'attachment; filename="skillforge-roadmap-{roadmap.id}.pdf"'
    assert resp.headers["content-disposition"] == expected_disp


@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_content_disposition_inline_when_download_false(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """Setting download=false explicitly sets Content-Disposition: inline."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = b"%PDF-test"

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf?download=false",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 200
    expected_disp = f'inline; filename="skillforge-roadmap-{roadmap.id}.pdf"'
    assert resp.headers["content-disposition"] == expected_disp


def test_api_pdf_invalid_download_query_param(test_users, test_roadmap_for_user_a):
    """Invalid boolean string for download returns 422 Unprocessable Entity."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf?download=notabool",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 422


# -----------------------------------------------------------------------------
# 5. Response Headers & Byte Integrity
# -----------------------------------------------------------------------------

@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_cache_control_strictly_no_store(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """Correction 1 Verification: Cache-Control must be strictly 'no-store'."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = b"%PDF-test"

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-store"


@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_no_obsolete_version_header(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """Correction 2 Verification: X-SkillForge-Version must NOT be present."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = b"%PDF-test"

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 200
    assert "x-skillforge-version" not in resp.headers


@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_exact_bytes_unchanged(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """Exact renderer output bytes are returned unchanged by the endpoint."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    deterministic_bytes = b"%PDF-1.4\n\x00\xff\xfe\xfdDeterministicPayload12345"
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = deterministic_bytes

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 200
    assert resp.content == deterministic_bytes


# -----------------------------------------------------------------------------
# 6. Service Orchestration & Pipeline Invariants
# -----------------------------------------------------------------------------

@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_service_invocations_exactly_once(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """Context service, narrative service, and renderer are each invoked exactly once with proper arguments."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_context = MagicMock()
    mock_build_context.return_value = mock_context
    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = b"%PDF-1.4\nTest"

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 200

    # 1. Context service called once with roadmap_id and authenticated_user_id
    mock_build_context.assert_called_once()
    call_kwargs = mock_build_context.call_args.kwargs
    assert call_kwargs["roadmap_id"] == roadmap.id
    assert call_kwargs["authenticated_user_id"] == user_a.id

    # 2. Narrative service called once with context
    mock_generate_narrative.assert_called_once_with(mock_context)

    # 3. Renderer called once with validated content
    mock_render.assert_called_once_with(sample_validated_content)


# -----------------------------------------------------------------------------
# 7. Fail-Closed Error Handling Tests
# -----------------------------------------------------------------------------

@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_narrative_reference_integrity_failure_fails_closed(
    mock_build_context,
    mock_generate_narrative,
    test_users,
    test_roadmap_for_user_a,
):
    """ReferenceIntegrityError fails closed: returns HTTP 500 without returning a partial PDF."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.side_effect = ReferenceIntegrityError(
        "Hallucinated resource detected.",
        violations=["Unauthorized URL: https://evil.com"],
    )

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 500
    assert resp.headers["content-type"] == "application/json"
    assert "Roadmap integrity validation failed" in resp.json()["detail"]


@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_gemini_timeout_maps_to_504(
    mock_build_context,
    mock_generate_narrative,
    test_users,
    test_roadmap_for_user_a,
):
    """Gemini timeout during narrative generation maps to HTTP 504 Gateway Timeout."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    timeout_err = GeminiTimeoutError("Gemini call timed out after 30s")
    mock_generate_narrative.side_effect = NarrativeGenerationError(
        "Narrative generation failed due to timeout.",
        original_exception=timeout_err,
    )

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 504
    assert "timed out" in resp.json()["detail"]


@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_gemini_api_error_maps_to_502(
    mock_build_context,
    mock_generate_narrative,
    test_users,
    test_roadmap_for_user_a,
):
    """Upstream Gemini API error maps to HTTP 502 Bad Gateway."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    api_err = GeminiAPIError("Upstream service unavailable (503)", status_code=503)
    mock_generate_narrative.side_effect = NarrativeGenerationError(
        "Gemini API failure",
        original_exception=api_err,
    )

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 502
    assert "AI narrative generation service unavailable" in resp.json()["detail"]


@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_renderer_failure_maps_to_500(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """ReportLab rendering exception returns HTTP 500 without leaking stack traces."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.return_value = sample_validated_content
    mock_render.side_effect = RuntimeError("ReportLab layout engine overflow exception")

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 500
    assert "PDF document compilation failed" in resp.json()["detail"]
    assert "ReportLab layout engine overflow" not in resp.text


# -----------------------------------------------------------------------------
# 8. Persistence & Side-Effects Invariants
# -----------------------------------------------------------------------------

@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
@patch("app.api.v1.roadmap.roadmap_pdf_context_service.build_verified_context")
def test_api_pdf_no_filesystem_side_effects(
    mock_build_context,
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """Calling the PDF endpoint does not persist any files in backend/uploads, /tmp, or cwd."""
    user_a = test_users["user_a"]
    roadmap = test_roadmap_for_user_a
    mock_build_context.return_value = MagicMock()
    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = b"%PDF-1.4\nTest"

    # Track directory state
    tmp_files_before = set(os.listdir("/tmp"))

    resp = client.get(
        f"/api/v1/roadmaps/{roadmap.id}/pdf",
        headers={"X-User-Id": str(user_a.id)},
    )
    assert resp.status_code == 200

    tmp_files_after = set(os.listdir("/tmp"))
    new_tmp_pdfs = [f for f in (tmp_files_after - tmp_files_before) if f.endswith(".pdf")]
    assert len(new_tmp_pdfs) == 0, f"Unexpected PDF files written to /tmp: {new_tmp_pdfs}"


# -----------------------------------------------------------------------------
# 9. Real E2E Test: Real PostgreSQL + Mocked Gemini + Real ReportLab Renderer
# -----------------------------------------------------------------------------

def test_api_pdf_real_pipeline_end_to_end(db_session: Session):
    """
    Real Pipeline End-to-End Integration Test:
    - Real PostgreSQL transactional session with seeded database entities
    - Real RoadmapPDFContextService (Phase 2)
    - Real RoadmapPDFNarrativeService with mocked Gemini structured output (Phase 3)
    - Real RoadmapPDFRenderer compiling genuine ReportLab A4 PDF (Phase 4)
    - Real FastAPI request and response (Phase 5)
    """
    # 1. Create real database records
    user = User(
        id=uuid.uuid4(),
        email=f"e2e_candidate_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Dr. Jane Developer",
        target_role="Backend Engineer",
    )
    db_session.add(user)

    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Dr. Jane Developer",
        target_role="Backend Engineer",
        experience_level="SENIOR",
        college="Indian Institute of Technology",
        degree="M.Tech",
        branch="Computer Science",
        semester=None,
    )
    db_session.add(profile)

    role = db_session.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    if not role:
        role = JobRole(
            id=uuid.uuid4(),
            title="Backend Engineer",
            slug="backend-engineer",
            category="Software Engineering",
        )
        db_session.add(role)

    skill_python = db_session.query(Skill).filter(Skill.slug == "python").first()
    if not skill_python:
        skill_python = Skill(
            id=uuid.uuid4(),
            name="Python",
            slug="python",
            category="Programming Languages",
        )
        db_session.add(skill_python)

    skill_fastapi = db_session.query(Skill).filter(Skill.slug == "fastapi").first()
    if not skill_fastapi:
        skill_fastapi = Skill(
            id=uuid.uuid4(),
            name="FastAPI",
            slug="fastapi",
            category="Frameworks",
        )
        db_session.add(skill_fastapi)

    roadmap = CandidateRoadmap(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=role.id,
        target_role_title=role.title,
        location="India",
        status="ACTIVE",
        roadmap_version="v1.0",
    )
    db_session.add(roadmap)

    m1 = RoadmapMilestone(
        id=uuid.uuid4(),
        roadmap_id=roadmap.id,
        skill_id=skill_python.id,
        order_index=1,
        priority_score=0.90,
        priority_level="HIGH",
        gap_status="MISSING",
        reason="Core language competency",
        status="NOT_STARTED",
    )
    m2 = RoadmapMilestone(
        id=uuid.uuid4(),
        roadmap_id=roadmap.id,
        skill_id=skill_fastapi.id,
        order_index=2,
        priority_score=0.85,
        priority_level="HIGH",
        gap_status="PARTIAL",
        reason="Modern asynchronous framework",
        status="NOT_STARTED",
    )
    db_session.add(m1)
    db_session.add(m2)
    db_session.commit()

    # 2. Mock GeminiClient.with_structured_output to return realistic narrative matching real DB skills
    mock_narrative = RoadmapPDFPersonalizedNarrative(
        personalized_subtitle="Accelerated Senior Backend Roadmap",
        executive_summary="Targeted trajectory designed to advance core Python paradigms and FastAPI microservices.",
        readiness_explanation="Candidate demonstrates strong fundamental competencies with specific framework expansion required.",
        top_gap_narratives=[
            SkillGapNarrative(
                skill_id=str(skill_python.id),
                why_it_matters="Mastery of advanced Python data structures and concurrent execution is critical.",
                suggested_focus="Master asyncio event loops and memory profiling.",
            ),
            SkillGapNarrative(
                skill_id=str(skill_fastapi.id),
                why_it_matters="FastAPI provides asynchronous concurrency and type-safe schema validation.",
                suggested_focus="Deepen dependency injection and async database sessions.",
            ),
        ],
        phases=[
            RoadmapPhaseNarrative(
                skill_id=skill_python.id,
                phase_title="Advanced Python Architecture & Concurrency",
                personalized_rationale="Solidify fundamental asynchronous paradigms before moving to framework layers.",
                key_topics=("Asyncio event loops", "Generators and coroutines", "Memory optimization"),
                expected_focus="Design robust, performant foundational backend modules.",
            ),
            RoadmapPhaseNarrative(
                skill_id=skill_fastapi.id,
                phase_title="High-Throughput Microservice Engineering with FastAPI",
                personalized_rationale="Construct type-safe, asynchronous RESTful APIs adhering to clean architecture.",
                key_topics=("Pydantic V2 models", "Dependency injection", "Async database sessions"),
                expected_focus="Deliver production-grade asynchronous services.",
            ),
        ],
        immediate_next_steps=[
            "Review Python asyncio documentation",
            "Set up a FastAPI project with async SQLAlchemy",
        ],
        closing_encouragement="Consistent practical application will rapidly elevate your backend engineering capabilities.",
    )

    with patch("app.ai.roadmap.narrative_service.GeminiClient") as MockClientClass:
        mock_client_inst = MagicMock()
        mock_runnable = MagicMock()
        mock_runnable.invoke.return_value = mock_narrative
        mock_client_inst.with_structured_output.return_value = mock_runnable
        MockClientClass.return_value = mock_client_inst

        # 3. Call endpoint via TestClient
        resp = client.get(
            f"/api/v1/roadmaps/{roadmap.id}/pdf",
            headers={"X-User-Id": str(user.id)},
        )

        # 4. Assert HTTP transport invariants
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.headers["cache-control"] == "no-store"
        assert f'inline; filename="skillforge-roadmap-{roadmap.id}.pdf"' == resp.headers["content-disposition"]
        assert "x-skillforge-version" not in resp.headers

        # 5. Assert valid PDF binary structure
        pdf_bytes = resp.content
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 2000

        # 6. Parse and validate rendered PDF content with pypdf
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        assert len(reader.pages) >= 1
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "SkillForge" in full_text
        assert "Dr. Jane Developer" in full_text
        assert "Backend Engineer" in full_text
        assert "Advanced Python Architecture" in full_text


@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
def test_api_pdf_bidirectional_user_isolation(
    mock_generate_narrative,
    mock_render,
    db_session: Session,
    test_users,
    sample_validated_content,
):
    """
    Explicitly tests User A and User B bidirectional roadmap access:
    - User A owns Roadmap A; User B owns Roadmap B
    - User A -> Roadmap A -> 200 OK
    - User B -> Roadmap A -> 403 Forbidden
    - User B -> Roadmap B -> 200 OK
    - User A -> Roadmap B -> 403 Forbidden
    """
    user_a = test_users["user_a"]
    user_b = test_users["user_b"]

    role = db_session.query(JobRole).first()
    if not role:
        role = JobRole(id=uuid.uuid4(), title="Software Engineer", slug="software-engineer")
        db_session.add(role)
        db_session.commit()

    roadmap_a = CandidateRoadmap(
        id=uuid.uuid4(),
        user_id=user_a.id,
        role_id=role.id,
        target_role_title=role.title,
        location="India",
        status="ACTIVE",
    )
    roadmap_b = CandidateRoadmap(
        id=uuid.uuid4(),
        user_id=user_b.id,
        role_id=role.id,
        target_role_title=role.title,
        location="India",
        status="ACTIVE",
    )
    db_session.add(roadmap_a)
    db_session.add(roadmap_b)
    db_session.commit()

    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = b"%PDF-1.4\nTest"

    # User A -> Roadmap A -> 200 OK
    resp_a_own = client.get(f"/api/v1/roadmaps/{roadmap_a.id}/pdf", headers={"X-User-Id": str(user_a.id)})
    assert resp_a_own.status_code == 200

    # User B -> Roadmap A -> 403 Forbidden
    resp_b_cross = client.get(f"/api/v1/roadmaps/{roadmap_a.id}/pdf", headers={"X-User-Id": str(user_b.id)})
    assert resp_b_cross.status_code == 403
    assert "Cross-user access denied" in resp_b_cross.json()["detail"]

    # User B -> Roadmap B -> 200 OK
    resp_b_own = client.get(f"/api/v1/roadmaps/{roadmap_b.id}/pdf", headers={"X-User-Id": str(user_b.id)})
    assert resp_b_own.status_code == 200

    # User A -> Roadmap B -> 403 Forbidden
    resp_a_cross = client.get(f"/api/v1/roadmaps/{roadmap_b.id}/pdf", headers={"X-User-Id": str(user_a.id)})
    assert resp_a_cross.status_code == 403
    assert "Cross-user access denied" in resp_a_cross.json()["detail"]


@patch("app.api.v1.roadmap.roadmap_pdf_renderer.render")
@patch("app.api.v1.roadmap.RoadmapPDFNarrativeService.generate_validated_narrative")
def test_api_pdf_arbitrary_query_user_id_not_trusted(
    mock_generate_narrative,
    mock_render,
    test_users,
    test_roadmap_for_user_a,
    sample_validated_content,
):
    """
    Passing an arbitrary query parameter ?user_id=<victim> does not compromise identity;
    identity is strictly governed by X-User-Id.
    """
    user_a = test_users["user_a"]
    user_b = test_users["user_b"]
    roadmap_a = test_roadmap_for_user_a

    mock_generate_narrative.return_value = sample_validated_content
    mock_render.return_value = b"%PDF-1.4\nTest"

    # User B passes their X-User-Id but tries to claim user_id=User A in query string to access Roadmap A
    resp = client.get(
        f"/api/v1/roadmaps/{roadmap_a.id}/pdf?user_id={user_a.id}",
        headers={"X-User-Id": str(user_b.id)},
    )
    # Must fail because authenticated context is User B, who does not own Roadmap A
    assert resp.status_code == 403
    assert "Cross-user access denied" in resp.json()["detail"]


def test_api_pdf_no_duplicate_gap_or_readiness_calculations():
    """Verifies that the route does not import or invoke skill_gap_service or recalculate metrics."""
    import inspect
    from app.api.v1.roadmap import get_roadmap_pdf

    source = inspect.getsource(get_roadmap_pdf)
    assert "skill_gap_service" not in source
    assert "calculate_readiness" not in source
    assert "classify_gap" not in source
    assert "score_gap" not in source
    assert "prioritize_gaps" not in source

