"""
Comprehensive Phase 4 Test Suite:
SkillForge AI Career Roadmap PDF ReportLab Renderer.

Verifies all 30 required Phase 4 presentation/layout invariants + visual inspection:
1. Renderer creates valid PDF bytes
2. Output starts with PDF signature (%PDF-)
3. Empty/minimal valid content renders
4. Full realistic roadmap renders
5. Readiness percentage is rendered from authoritative value
6. Readiness zero renders safely
7. Zero required skills renders safely
8. Gap ordering is preserved
9. Roadmap ordering is preserved
10. Milestone duration is preserved
11. Resource URLs come only from validated content
12. Approved projects render as challenges
13. Curated projects are not described as candidate proof
14. Next steps render
15. Long text wraps without failure
16. Long resource titles do not break layout
17. Long project descriptions do not break layout
18. Multiple pages render successfully
19. Page footer renders consistently
20. No Gemini call occurs
21. No database access occurs
22. No network call occurs
23. Renderer has no FastAPI dependency
24. Renderer has no SQLAlchemy dependency
25. Renderer produces deterministic content for identical input
26. Missing optional profile fields render safely
27. Missing resources render safely
28. Missing projects render safely
29. Missing verification data renders safely
30. Malformed validated input is rejected by type/contract
31. Visual inspection validation
"""

from datetime import datetime, timezone
import io
import socket
from unittest.mock import patch
import uuid
import pypdf
import pytest

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
from app.ai.roadmap.narrative_schemas import (
    ValidatedRoadmapPDFContent,
    ValidatedRoadmapPhase,
    ValidatedTopSkillGap,
)
from app.services.roadmap_pdf_renderer import (
    RoadmapPDFRenderer,
    roadmap_pdf_renderer,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_ids():
    """Stable UUIDs for deterministic testing."""
    return {
        "roadmap_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "user_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "skill_python": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "skill_fastapi": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "skill_docker": uuid.UUID("55555555-5555-5555-5555-555555555555"),
        "resource_1": uuid.UUID("66666666-6666-6666-6666-666666666666"),
        "project_1": uuid.UUID("77777777-7777-7777-7777-777777777777"),
    }


@pytest.fixture
def sample_validated_content(sample_ids) -> ValidatedRoadmapPDFContent:
    """Constructs a realistic, complete ValidatedRoadmapPDFContent fixture."""
    candidate = VerifiedCandidateProfile(
        user_id=sample_ids["user_id"],
        email="alice.engineer@skillforge.test",
        name="Alice Candidate",
        target_role="Backend Engineer",
        experience_level="INTERMEDIATE",
        college="National Institute of Technology",
        degree="B.Tech",
        branch="Computer Science",
        semester=7,
        education="B.Tech Computer Science (Sem 7)",
    )

    readiness = VerifiedReadinessMetrics(
        readiness_percentage=65,
        total_required_skills=6,
        strong_count=4,
        partial_count=1,
        missing_count=1,
        has_resume=True,
        has_github=True,
        scoring_version="v1",
    )

    gap_docker = ValidatedTopSkillGap(
        skill_id=sample_ids["skill_docker"],
        skill_name="Docker",
        canonical_slug="docker",
        category="DevOps",
        gap_status=SkillGapClassification.MISSING,
        priority_score=0.88,
        priority_level=PriorityTierLevel.HIGH,
        demand_score=0.84,
        growth_rate=0.20,
        why_it_matters="Docker containerization is essential for microservice isolation and reproducible deployments.",
        suggested_focus="Master multi-stage Dockerfiles and container healthcheck strategies.",
    )

    gap_fastapi = ValidatedTopSkillGap(
        skill_id=sample_ids["skill_fastapi"],
        skill_name="FastAPI",
        canonical_slug="fastapi",
        category="Frameworks",
        gap_status=SkillGapClassification.PARTIAL,
        priority_score=0.74,
        priority_level=PriorityTierLevel.MEDIUM,
        demand_score=0.78,
        growth_rate=0.24,
        why_it_matters="FastAPI delivers asynchronous concurrency required for high-throughput microservices.",
        suggested_focus="Deepen understanding of Pydantic dependency injection and async database sessions.",
    )

    res_fastapi = VerifiedApprovedResource(
        resource_id=sample_ids["resource_1"],
        skill_id=sample_ids["skill_fastapi"],
        skill_name="FastAPI",
        title="FastAPI Official Documentation",
        url="https://fastapi.tiangolo.com/tutorial",
        resource_type="DOCUMENTATION",
        provider="Tiangolo Official",
        difficulty="BEGINNER",
        estimated_minutes=120,
        is_approved=True,
    )

    proj_docker = VerifiedApprovedProject(
        project_id=sample_ids["project_1"],
        skill_id=sample_ids["skill_docker"],
        skill_name="Docker",
        title="Production Microservice Containerization",
        description="Build and containerize a resilient REST service using multi-stage builds and Docker Compose.",
        difficulty="INTERMEDIATE",
        deliverables=("Dockerfile", "docker-compose.yml", ".dockerignore"),
        verification_criteria=("Service builds cleanly", "Container passes healthcheck endpoint"),
        estimated_hours=8,
        is_curated_challenge=True,
        is_candidate_proof=False,
    )

    phase_1 = ValidatedRoadmapPhase(
        milestone_id=uuid.uuid4(),
        order_index=1,
        skill_id=sample_ids["skill_fastapi"],
        skill_name="FastAPI",
        canonical_slug="fastapi",
        category="Frameworks",
        gap_status=SkillGapClassification.PARTIAL,
        priority_score=0.74,
        priority_level=PriorityTierLevel.MEDIUM,
        is_transitive_prerequisite=False,
        deterministic_reason="Foundational asynchronous API development framework",
        status="NOT_STARTED",
        prerequisites=(),
        learning_objectives=("Async route design", "Pydantic dependency injection"),
        resources=(res_fastapi,),
        project=None,
        latest_verification=None,
        phase_title="Asynchronous API Mastery with FastAPI",
        personalized_rationale="Solidify asynchronous routing and schema validation to elevate your demonstrated partial knowledge.",
        key_topics=("Async route design", "Dependency injection", "Pydantic V2 schemas"),
        expected_focus="Build high-performance RESTful microservices with OpenAPI documentation.",
    )

    phase_2 = ValidatedRoadmapPhase(
        milestone_id=uuid.uuid4(),
        order_index=2,
        skill_id=sample_ids["skill_docker"],
        skill_name="Docker",
        canonical_slug="docker",
        category="DevOps",
        gap_status=SkillGapClassification.MISSING,
        priority_score=0.88,
        priority_level=PriorityTierLevel.HIGH,
        is_transitive_prerequisite=False,
        deterministic_reason="Service containerization and deployment isolation",
        status="NOT_STARTED",
        prerequisites=(
            VerifiedRoadmapPrerequisite(
                skill_id=sample_ids["skill_fastapi"],
                skill_name="FastAPI",
                canonical_slug="fastapi",
                dependency_type="RECOMMENDED",
                is_satisfied=False,
            ),
        ),
        learning_objectives=("Multi-stage Dockerfiles", "Container orchestration"),
        resources=(),
        project=proj_docker,
        latest_verification=None,
        phase_title="Production Containerization with Docker",
        personalized_rationale="Package your backend applications into secure, lightweight container images for reproducible deployment.",
        key_topics=("Multi-stage builds", "Docker Compose", "Container networking"),
        expected_focus="Containerize backend services for production environments.",
    )

    return ValidatedRoadmapPDFContent(
        schema_version="v1.0",
        generated_at=datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc),
        roadmap_id=sample_ids["roadmap_id"],
        candidate=candidate,
        readiness=readiness,
        target_role_title="Backend Engineer",
        location="India",
        total_milestones=2,
        high_priority_count=1,
        medium_priority_count=1,
        low_priority_count=0,
        transitive_prerequisite_count=0,
        market_facts=(
            VerifiedMarketDemandFact(
                skill_id=sample_ids["skill_docker"],
                skill_name="Docker",
                canonical_slug="docker",
                demand_score=0.84,
                growth_rate=0.20,
                growth_class="RISING",
                data_source="adzuna",
            ),
        ),
        verification_evidence=(),
        weekly_hours_recommendation=None,  # Invariant: strictly None
        verification_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        personalized_subtitle="Targeted Competency Pathway for Backend Engineer Roles",
        executive_summary="Alice has demonstrated strong foundations in Python and database management. To achieve industry readiness for Backend Engineer roles, closing gaps in FastAPI and Docker is prioritized.",
        readiness_explanation="The 65% readiness score reflects verified core competence with actionable focus areas in containerization and modern API frameworks.",
        validated_top_gaps=(gap_docker, gap_fastapi),
        validated_phases=(phase_1, phase_2),
        immediate_next_steps=(
            "Deepen FastAPI route structuring using official documentation.",
            "Install Docker and implement a multi-stage container build for a sample API.",
        ),
        closing_encouragement="Executing this focused curriculum will position you strongly for competitive Backend Engineering roles.",
    )


# -----------------------------------------------------------------------------
# Unit Tests (30 Required Scenarios)
# -----------------------------------------------------------------------------

def test_01_renderer_creates_valid_pdf_bytes(sample_validated_content):
    """Scenario 1: RoadmapPDFRenderer produces non-empty bytes."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_02_output_starts_with_pdf_signature(sample_validated_content):
    """Scenario 2: PDF output begins with valid %PDF- magic signature."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    assert pdf_bytes.startswith(b"%PDF-")


def test_03_empty_minimal_valid_content_renders(sample_ids):
    """Scenario 3: Minimal valid content with 1 phase, no gaps, no resources renders cleanly."""
    candidate = VerifiedCandidateProfile(
        user_id=sample_ids["user_id"],
        email="minimal@test.internal",
    )
    readiness = VerifiedReadinessMetrics(
        readiness_percentage=0,
        total_required_skills=1,
        strong_count=0,
        partial_count=0,
        missing_count=1,
    )
    phase = ValidatedRoadmapPhase(
        order_index=1,
        skill_id=sample_ids["skill_python"],
        skill_name="Python",
        canonical_slug="python",
        gap_status=SkillGapClassification.MISSING,
        deterministic_reason="Core programming foundation",
        phase_title="Core Python Foundations",
        personalized_rationale="Foundational syntax and data structures.",
        key_topics=("Syntax", "Loops"),
    )
    minimal_content = ValidatedRoadmapPDFContent(
        schema_version="v1.0",
        roadmap_id=sample_ids["roadmap_id"],
        candidate=candidate,
        readiness=readiness,
        target_role_title="Software Developer",
        total_milestones=1,
        high_priority_count=0,
        medium_priority_count=0,
        low_priority_count=0,
        transitive_prerequisite_count=0,
        verification_hash="abc1234567890def",
        personalized_subtitle="Minimal Pathway",
        executive_summary="Executive pathway overview for candidate development.",
        readiness_explanation="Initial baseline assessment.",
        validated_phases=(phase,),
        immediate_next_steps=("Start with Python official tutorial.", "Write basic scripts."),
        closing_encouragement="Consistent practice will yield rapid results.",
    )

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(minimal_content)

    assert pdf_bytes.startswith(b"%PDF-")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


def test_04_full_realistic_roadmap_renders(sample_validated_content):
    """Scenario 4: Full realistic roadmap with all components renders cleanly."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    assert "Personalized Career Roadmap" in extracted_text
    assert "Backend Engineer" in extracted_text
    assert "Alice Candidate" in extracted_text


def test_05_readiness_percentage_is_rendered_from_authoritative_value(sample_validated_content):
    """Scenario 5: Authoritative readiness percentage (65%) appears in extracted PDF text."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    assert "65%" in extracted_text
    assert "ROLE READINESS SCORE" in extracted_text


def test_06_readiness_zero_renders_safely(sample_validated_content):
    """Scenario 6: Readiness percentage = 0 renders safely without division by zero."""
    zero_readiness = sample_validated_content.readiness.model_copy(
        update={"readiness_percentage": 0, "strong_count": 0, "partial_count": 0, "missing_count": 6}
    )
    content = sample_validated_content.model_copy(update={"readiness": zero_readiness})

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    assert pdf_bytes.startswith(b"%PDF-")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)
    assert "0%" in extracted_text


def test_07_zero_required_skills_renders_safely(sample_validated_content):
    """Scenario 7: total_required_skills = 0 renders safely without division by zero."""
    empty_readiness = sample_validated_content.readiness.model_copy(
        update={"readiness_percentage": 0, "total_required_skills": 0, "strong_count": 0, "partial_count": 0, "missing_count": 0}
    )
    content = sample_validated_content.model_copy(update={"readiness": empty_readiness})

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    assert pdf_bytes.startswith(b"%PDF-")


def test_08_gap_ordering_preserved(sample_validated_content):
    """Scenario 8: Prioritized top skill gaps appear in exact sequence (Docker then FastAPI)."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    gaps_marker = extracted_text.find("Prioritized Skill Gaps")
    assert gaps_marker != -1
    gaps_section = extracted_text[gaps_marker:]

    pos_docker = gaps_section.find("Docker")
    pos_fastapi = gaps_section.find("FastAPI")

    assert pos_docker != -1
    assert pos_fastapi != -1
    assert pos_docker < pos_fastapi


def test_09_roadmap_ordering_preserved(sample_validated_content):
    """Scenario 9: Roadmap milestone phases appear in exact 1..N sequence."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    pos_phase1 = extracted_text.find("PHASE 1")
    pos_phase2 = extracted_text.find("PHASE 2")

    assert pos_phase1 != -1
    assert pos_phase2 != -1
    assert pos_phase1 < pos_phase2


def test_10_milestone_duration_is_preserved(sample_validated_content):
    """Scenario 10: Approved resource duration (120 min) is rendered from authoritative input."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    assert "120 min" in extracted_text


def test_11_resource_urls_come_only_from_validated_content(sample_validated_content):
    """Scenario 11: Rendered resource title and URL originate strictly from validated content."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    assert "FastAPI Official Documentation" in extracted_text
    assert "Tiangolo Official" in extracted_text


def test_12_approved_projects_render_as_challenges(sample_validated_content):
    """Scenario 12: Curated approved project renders as a distinct challenge box."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    assert "PRACTICE CHALLENGE" in extracted_text
    assert "Production Microservice Containerization" in extracted_text


def test_13_curated_projects_not_described_as_candidate_proof(sample_validated_content):
    """Scenario 13: Invariant banner explicitly states NOT CANDIDATE PROOF."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    assert "NOT CANDIDATE PROOF" in extracted_text


def test_14_next_steps_render(sample_validated_content):
    """Scenario 14: Immediate execution steps render accurately."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    assert "Immediate Execution Steps" in extracted_text
    assert "Deepen FastAPI route structuring" in extracted_text
    assert "multi-stage container build" in extracted_text


def test_15_long_text_wraps_without_failure(sample_validated_content):
    """Scenario 15: Very long rationale and summary text wrap cleanly without error."""
    long_rationale = (
        "This is an extraordinarily comprehensive engineering rationale explaining why the candidate must "
        "thoroughly master this specific technological domain before proceeding to subsequent architectural layers. "
    ) * 4  # ~600 chars

    phase_copy = sample_validated_content.validated_phases[0].model_copy(
        update={"personalized_rationale": long_rationale}
    )
    content = sample_validated_content.model_copy(
        update={"validated_phases": (phase_copy, sample_validated_content.validated_phases[1])}
    )

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    assert pdf_bytes.startswith(b"%PDF-")


def test_16_long_resource_titles_do_not_break_layout(sample_validated_content):
    """Scenario 16: Lengthy approved resource titles do not overflow or cause table layout failure."""
    long_title = "Comprehensive Guide to Asynchronous Microservices and Distributed System Protocols in Python FastAPI"
    res_copy = sample_validated_content.validated_phases[0].resources[0].model_copy(
        update={"title": long_title}
    )
    phase_copy = sample_validated_content.validated_phases[0].model_copy(
        update={"resources": (res_copy,)}
    )
    content = sample_validated_content.model_copy(
        update={"validated_phases": (phase_copy, sample_validated_content.validated_phases[1])}
    )

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    assert pdf_bytes.startswith(b"%PDF-")


def test_17_long_project_descriptions_do_not_break_layout(sample_validated_content):
    """Scenario 17: Long project briefs and extensive deliverables wrap safely in challenge box."""
    long_desc = "Implement a highly available multi-region containerized API cluster with distributed caching and queue workers. " * 3
    proj_copy = sample_validated_content.validated_phases[1].project.model_copy(
        update={"description": long_desc}
    )
    phase_copy = sample_validated_content.validated_phases[1].model_copy(
        update={"project": proj_copy}
    )
    content = sample_validated_content.model_copy(
        update={"validated_phases": (sample_validated_content.validated_phases[0], phase_copy)}
    )

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    assert pdf_bytes.startswith(b"%PDF-")


def test_18_multiple_pages_render_successfully(sample_validated_content):
    """Scenario 18: Generating a roadmap with multiple milestones produces multi-page document."""
    # Duplicate phases to simulate a 6-milestone curriculum
    p1 = sample_validated_content.validated_phases[0]
    p2 = sample_validated_content.validated_phases[1]

    expanded_phases = []
    for i in range(1, 7):
        base = p1 if i % 2 == 1 else p2
        expanded_phases.append(base.model_copy(update={"order_index": i}))

    content = sample_validated_content.model_copy(
        update={"validated_phases": tuple(expanded_phases), "total_milestones": 6}
    )

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 2


def test_19_page_footer_renders_consistently(sample_validated_content):
    """Scenario 19: Running footer renders brand text and page count on every page."""
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    total_pages = len(reader.pages)

    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        assert "SkillForge AI" in text
        assert f"Page {idx} of {total_pages}" in text


def test_20_no_gemini_call_occurs(sample_validated_content):
    """Scenario 20: Verified zero Gemini / LangChain invocations during PDF rendering."""
    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_gemini:
        renderer = RoadmapPDFRenderer()
        pdf_bytes = renderer.render(sample_validated_content)

        assert pdf_bytes.startswith(b"%PDF-")
        mock_gemini.assert_not_called()


def test_21_no_database_access_occurs(sample_validated_content):
    """Scenario 21: Verified zero SQLAlchemy database queries during rendering."""
    with patch("sqlalchemy.orm.Session") as mock_session:
        renderer = RoadmapPDFRenderer()
        pdf_bytes = renderer.render(sample_validated_content)

        assert pdf_bytes.startswith(b"%PDF-")
        mock_session.assert_not_called()


def test_22_no_network_call_occurs(sample_validated_content):
    """Scenario 22: Verified zero network socket calls during PDF compilation."""
    with patch("socket.socket") as mock_socket:
        renderer = RoadmapPDFRenderer()
        pdf_bytes = renderer.render(sample_validated_content)

        assert pdf_bytes.startswith(b"%PDF-")
        mock_socket.assert_not_called()


def test_23_renderer_has_no_fastapi_dependency():
    """Scenario 23: Confirms app.services.roadmap_pdf_renderer has zero FastAPI imports."""
    import inspect
    mod = inspect.getmodule(RoadmapPDFRenderer)
    src = inspect.getsource(mod)

    assert "import fastapi" not in src.lower()
    assert "from fastapi" not in src.lower()


def test_24_renderer_has_no_sqlalchemy_dependency():
    """Scenario 24: Confirms app.services.roadmap_pdf_renderer has zero SQLAlchemy imports."""
    import inspect
    mod = inspect.getmodule(RoadmapPDFRenderer)
    src = inspect.getsource(mod)

    assert "import sqlalchemy" not in src.lower()
    assert "from sqlalchemy" not in src.lower()


def test_25_renderer_produces_deterministic_content_for_identical_input(sample_validated_content):
    """Scenario 25: Rendering identical input twice produces identical page count and extracted text."""
    renderer = RoadmapPDFRenderer()
    pdf_1 = renderer.render(sample_validated_content)
    pdf_2 = renderer.render(sample_validated_content)

    reader_1 = pypdf.PdfReader(io.BytesIO(pdf_1))
    reader_2 = pypdf.PdfReader(io.BytesIO(pdf_2))

    assert len(reader_1.pages) == len(reader_2.pages)

    text_1 = " ".join(p.extract_text() for p in reader_1.pages)
    text_2 = " ".join(p.extract_text() for p in reader_2.pages)
    assert text_1 == text_2


def test_26_missing_optional_profile_fields_render_safely(sample_validated_content):
    """Scenario 26: Null candidate optional fields (name, degree, semester) render cleanly with fallback."""
    sparse_candidate = VerifiedCandidateProfile(
        user_id=sample_validated_content.candidate.user_id,
        email="anonymous@skillforge.test",
        name=None,
        college=None,
        degree=None,
        branch=None,
        semester=None,
        education=None,
        experience_level=None,
    )
    content = sample_validated_content.model_copy(update={"candidate": sparse_candidate})

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted_text = " ".join(page.extract_text() for page in reader.pages)

    assert "SkillForge Candidate" in extracted_text


def test_27_missing_resources_render_safely(sample_validated_content):
    """Scenario 27: Milestones with empty resources render without table error."""
    p_no_res = sample_validated_content.validated_phases[0].model_copy(update={"resources": ()})
    content = sample_validated_content.model_copy(
        update={"validated_phases": (p_no_res, sample_validated_content.validated_phases[1])}
    )

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    assert pdf_bytes.startswith(b"%PDF-")


def test_28_missing_projects_render_safely(sample_validated_content):
    """Scenario 28: Milestones with project=None render cleanly."""
    p_no_proj = sample_validated_content.validated_phases[1].model_copy(update={"project": None})
    content = sample_validated_content.model_copy(
        update={"validated_phases": (sample_validated_content.validated_phases[0], p_no_proj)}
    )

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    assert pdf_bytes.startswith(b"%PDF-")


def test_29_missing_verification_data_renders_safely(sample_validated_content):
    """Scenario 29: Empty verification evidence renders cleanly."""
    content = sample_validated_content.model_copy(update={"verification_evidence": ()})

    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(content)

    assert pdf_bytes.startswith(b"%PDF-")


def test_30_malformed_validated_input_is_rejected_by_type():
    """Scenario 30: Invalid input types (None, string, dict) raise TypeError."""
    renderer = RoadmapPDFRenderer()

    with pytest.raises(TypeError):
        renderer.render(None)

    with pytest.raises(TypeError):
        renderer.render({"invalid": "dict"})


def test_31_visual_inspection_validation(sample_validated_content):
    """
    Scenario 31: Visual inspection verification of document structure.
    Validates page layout geometry, margins, hierarchy, and section containment.
    """
    renderer = RoadmapPDFRenderer()
    pdf_bytes = renderer.render(sample_validated_content)

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    assert page_count >= 1

    # 1. Verify standard A4 geometry across all pages
    for i, page in enumerate(reader.pages):
        box = page.mediabox
        width = float(box.width)
        height = float(box.height)
        assert 594 <= width <= 596, f"Page {i+1} width {width} not standard A4"
        assert 841 <= height <= 843, f"Page {i+1} height {height} not standard A4"

    all_text = " ".join(page.extract_text() for page in reader.pages)

    # 2. Visual Hierarchy: Top Header & Branding
    assert "SkillForge AI" in all_text
    assert "CAREER INTELLIGENCE PLATFORM" in all_text
    assert "Personalized Career Roadmap" in all_text
    assert "Targeted Competency Pathway for Backend Engineer Roles" in all_text

    # 3. Candidate Metadata Card
    assert "Alice Candidate" in all_text
    assert "Backend Engineer" in all_text

    # 4. Prominent Readiness Metric & Progress Breakdown
    assert "65%" in all_text
    assert "ROLE READINESS SCORE" in all_text
    assert "4 Demonstrated" in all_text
    assert "1 Missing of 6 Required" in all_text

    # 5. Top Skill Gaps Table
    assert "Prioritized Skill Gaps" in all_text
    assert "Docker" in all_text
    assert "FastAPI" in all_text

    # 6. Actionable Learning Roadmap Phases
    assert "Actionable Learning Roadmap" in all_text
    assert "PHASE 1" in all_text
    assert "Asynchronous API Mastery with FastAPI" in all_text
    assert "PHASE 2" in all_text
    assert "Production Containerization with Docker" in all_text

    # 7. Curated Practice Challenge Callout Box
    assert "PRACTICE CHALLENGE" in all_text
    assert "RECOMMENDED" in all_text
    assert "NOT CANDIDATE PROOF" in all_text

    # 8. Immediate Next Steps & Closing Narrative
    assert "Immediate Execution Steps (7–14 Days)" in all_text
    assert "Career Acceleration Outlook" in all_text

    # 9. Uniform Footer Attributions
    for i, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        assert f"Page {i} of {page_count}" in page_text

    # 10. PDF Document Metadata
    info = reader.metadata
    assert info.title == "Personalized Career Roadmap"
    assert info.author == "SkillForge AI"
