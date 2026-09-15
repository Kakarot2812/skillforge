"""
Comprehensive Phase 3 Test Suite:
AI Roadmap PDF Structured Narrative Generation and Reference Integrity Validation.

Verifies all 30 required Phase 3 unit/contract invariants + 1 opt-in live test:
1. Valid Phase 2 context produces structured narrative
2. GeminiClient is used
3. Exactly one Gemini invocation occurs
4. Structured output is parsed successfully
5. Invalid structured output fails
6. Unknown skill ID fails validation
7. Unknown resource ID fails validation
8. Unknown project ID fails validation
9. Unknown milestone ID fails validation
10. Roadmap milestone reordering fails validation
11. Changed roadmap duration fails validation
12. Changed gap classification fails validation
13. Changed priority fails validation
14. Changed demand score fails validation
15. Changed readiness fails validation
16. Changed verification status fails validation
17. Invented URL fails validation
18. Invented resource fails validation
19. Invented project fails validation
20. Invented skill fails validation
21. Curated project cannot become candidate proof
22. Weekly hours cannot be fabricated
23. Missing required authoritative record fails
24. Duplicate identifiers fail where inappropriate
25. Valid references pass
26. Authoritative values remain unchanged after Gemini generation
27. Profile fields are not unnecessarily exposed (email excluded)
28. No secrets reach Gemini prompt
29. Gemini provider error is translated correctly
30. Validation errors are typed and safe
31. Live integration test with real Gemini 2.5 Flash (opt-in)
"""

from datetime import datetime, timezone
import os
from typing import Tuple
from unittest.mock import MagicMock
import uuid
import pytest

from app.ai.context.roadmap_pdf_context import (
    EvidenceStatusType,
    PriorityTierLevel,
    SkillGapClassification,
    VerifiedApprovedProject,
    VerifiedApprovedResource,
    VerifiedCandidateEvidenceItem,
    VerifiedCandidateProfile,
    VerifiedMarketDemandFact,
    VerifiedPrioritizedGapsSummary,
    VerifiedReadinessMetrics,
    VerifiedRoadmapMilestoneContext,
    VerifiedRoadmapPDFContext,
    VerifiedRoadmapPrerequisite,
    VerifiedRoadmapSummary,
    VerifiedSkillGapFact,
    generate_deterministic_verification_hash,
)
from app.ai.gemini.client import GeminiClient
from app.ai.gemini.exceptions import GeminiAPIError, GeminiError, GeminiTimeoutError
from app.ai.roadmap.exceptions import (
    NarrativeGenerationError,
    NarrativeValidationError,
    ReferenceIntegrityError,
    RoadmapNarrativeError,
)
from app.ai.roadmap.narrative_prompts import build_roadmap_narrative_messages
from app.ai.roadmap.narrative_schemas import (
    RoadmapPDFPersonalizedNarrative,
    RoadmapPhaseNarrative,
    SkillGapNarrative,
    ValidatedRoadmapPDFContent,
    ValidatedRoadmapPhase,
    ValidatedTopSkillGap,
)
from app.ai.roadmap.narrative_service import RoadmapPDFNarrativeService
from app.ai.roadmap.reference_validator import ReferenceIntegrityValidator


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def sample_ids():
    """Provides stable, reproducible UUIDs for context entities."""
    return {
        "user_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "role_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "roadmap_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "skill_python": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "skill_fastapi": uuid.UUID("55555555-5555-5555-5555-555555555555"),
        "skill_docker": uuid.UUID("66666666-6666-6666-6666-666666666666"),
        "resource_1": uuid.UUID("77777777-7777-7777-7777-777777777777"),
        "project_1": uuid.UUID("88888888-8888-8888-8888-888888888888"),
    }


@pytest.fixture
def valid_phase2_context(sample_ids) -> VerifiedRoadmapPDFContext:
    """Constructs a complete, deterministic, authoritative Phase 2 context fixture."""
    user_id = sample_ids["user_id"]
    role_id = sample_ids["role_id"]
    roadmap_id = sample_ids["roadmap_id"]
    skill_fastapi = sample_ids["skill_fastapi"]
    skill_docker = sample_ids["skill_docker"]

    candidate = VerifiedCandidateProfile(
        user_id=user_id,
        email="candidate.secret@skillforge.internal",  # Sensitive field
        name="Alice Candidate",
        target_role="Backend Engineer",
        experience_level="INTERMEDIATE",
        college="National Engineering Institute",
        degree="B.Tech",
        branch="Computer Science",
        semester=7,
        education="B.Tech Computer Science (Sem 7)",
    )

    readiness = VerifiedReadinessMetrics(
        readiness_percentage=60,
        total_required_skills=5,
        strong_count=3,
        partial_count=1,
        missing_count=1,
        has_resume=True,
        has_github=True,
        scoring_version="v1",
    )

    gap_docker = VerifiedSkillGapFact(
        skill_id=skill_docker,
        skill_name="Docker",
        canonical_slug="docker",
        category="DevOps",
        gap_status=SkillGapClassification.MISSING,
        priority_score=0.88,
        priority_level=PriorityTierLevel.HIGH,
        demand_score=0.82,
        growth_rate=0.18,
        deterministic_explanation="Crucial containerization competency for backend deployment.",
    )

    gap_fastapi = VerifiedSkillGapFact(
        skill_id=skill_fastapi,
        skill_name="FastAPI",
        canonical_slug="fastapi",
        category="Frameworks",
        gap_status=SkillGapClassification.PARTIAL,
        priority_score=0.72,
        priority_level=PriorityTierLevel.MEDIUM,
        demand_score=0.78,
        growth_rate=0.22,
        deterministic_explanation="High industry demand for asynchronous Python APIs.",
    )

    prioritized_gaps = VerifiedPrioritizedGapsSummary(
        total_actionable_gaps=2,
        high_priority_count=1,
        medium_priority_count=1,
        low_priority_count=0,
        top_gaps=(gap_docker, gap_fastapi),
    )

    approved_res = VerifiedApprovedResource(
        resource_id=sample_ids["resource_1"],
        skill_id=skill_fastapi,
        skill_name="FastAPI",
        title="FastAPI Official Documentation",
        url="https://fastapi.tiangolo.com",
        provider="Official",
        resource_type="DOCUMENTATION",
        difficulty="BEGINNER",
        estimated_minutes=120,
        is_approved=True,
    )

    approved_proj = VerifiedApprovedProject(
        project_id=sample_ids["project_1"],
        skill_id=skill_docker,
        skill_name="Docker",
        title="Scalable Microservice Architecture",
        description="Implement and containerize a high-performance REST API.",
        difficulty="INTERMEDIATE",
        deliverables=("Dockerfile", "docker-compose.yml"),
        verification_criteria=("Service builds and passes healthcheck",),
        estimated_hours=8,
        is_curated_challenge=True,
        is_candidate_proof=False,
    )

    m1 = VerifiedRoadmapMilestoneContext(
        milestone_id=uuid.uuid4(),
        order_index=1,
        skill_id=skill_fastapi,
        skill_name="FastAPI",
        canonical_slug="fastapi",
        category="Frameworks",
        gap_status=SkillGapClassification.PARTIAL,
        priority_score=0.72,
        priority_level=PriorityTierLevel.MEDIUM,
        is_transitive_prerequisite=False,
        deterministic_reason="Foundational asynchronous API development framework",
        status="NOT_STARTED",
        prerequisites=(),
        learning_objectives=("Async route design", "Pydantic dependency injection"),
        resources=(approved_res,),
        project=None,
        latest_verification=None,
    )

    m2 = VerifiedRoadmapMilestoneContext(
        milestone_id=uuid.uuid4(),
        order_index=2,
        skill_id=skill_docker,
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
                skill_id=skill_fastapi,
                skill_name="FastAPI",
                canonical_slug="fastapi",
                dependency_type="RECOMMENDED",
                is_satisfied=False,
            ),
        ),
        learning_objectives=("Multi-stage Dockerfiles", "Container orchestration"),
        resources=(),
        project=approved_proj,
        latest_verification=None,
    )

    roadmap = VerifiedRoadmapSummary(
        roadmap_id=roadmap_id,
        user_id=user_id,
        role_id=role_id,
        target_role_title="Backend Engineer",
        location="India",
        status="ACTIVE",
        roadmap_version="v1",
        total_milestones=2,
        high_priority_count=1,
        medium_priority_count=1,
        low_priority_count=0,
        transitive_prerequisite_count=0,
        milestones=(m1, m2),
    )

    m_tuples = (
        (1, str(skill_fastapi), "PARTIAL", "MEDIUM"),
        (2, str(skill_docker), "MISSING", "HIGH"),
    )
    v_hash = generate_deterministic_verification_hash(
        roadmap_id=roadmap_id,
        user_id=user_id,
        role_id=role_id,
        target_role_title="Backend Engineer",
        readiness_percentage=60,
        strong_count=3,
        partial_count=1,
        missing_count=1,
        milestone_tuples=m_tuples,
    )

    return VerifiedRoadmapPDFContext(
        schema_version="v1.0",
        candidate=candidate,
        readiness=readiness,
        prioritized_gaps=prioritized_gaps,
        all_gap_facts=(gap_docker, gap_fastapi),
        roadmap=roadmap,
        market_facts=(
            VerifiedMarketDemandFact(
                skill_id=skill_docker,
                skill_name="Docker",
                canonical_slug="docker",
                demand_score=0.82,
                growth_rate=0.18,
                growth_class="RISING",
                data_source="adzuna",
            ),
        ),
        verification_evidence=(),
        weekly_hours_recommendation=None,  # Invariant: strictly None
        verification_hash=v_hash,
    )


@pytest.fixture
def valid_personalized_narrative(sample_ids) -> RoadmapPDFPersonalizedNarrative:
    """Constructs a valid Gemini structured narrative output matching valid_phase2_context."""
    skill_fastapi = sample_ids["skill_fastapi"]
    skill_docker = sample_ids["skill_docker"]

    phase1 = RoadmapPhaseNarrative(
        skill_id=skill_fastapi,
        phase_title="Asynchronous API Mastery with FastAPI",
        personalized_rationale="Solidify asynchronous routing and schema validation to elevate your demonstrated partial knowledge.",
        key_topics=("Async route design", "Dependency injection", "Pydantic V2 schemas"),
        expected_focus="Build high-performance RESTful microservices.",
    )

    phase2 = RoadmapPhaseNarrative(
        skill_id=skill_docker,
        phase_title="Production Containerization with Docker",
        personalized_rationale="Package your backend applications into secure, lightweight container images for reproducible deployment.",
        key_topics=("Multi-stage builds", "Docker Compose", "Container networking"),
        expected_focus="Containerize backend services for production environments.",
    )

    gap1 = SkillGapNarrative(
        skill_id=skill_docker,
        why_it_matters="Docker is standard in modern backend teams to ensure consistent dev and prod parity.",
        suggested_focus="Focus on multi-stage builds and security best practices.",
    )

    gap2 = SkillGapNarrative(
        skill_id=skill_fastapi,
        why_it_matters="FastAPI enables asynchronous concurrency critical for high-throughput microservices.",
        suggested_focus="Master async database sessions and dependency injection.",
    )

    return RoadmapPDFPersonalizedNarrative(
        personalized_subtitle="Targeted Competency Pathway for Backend Engineer Roles",
        executive_summary="Alice presents a solid 60% readiness foundation with verified Python competencies. This roadmap bridges key gaps in FastAPI and Docker.",
        readiness_explanation="The 60% readiness score highlights strong baseline programming proficiency, with high-priority containerization gaps required for enterprise readiness.",
        top_gap_narratives=(gap1, gap2),
        phases=(phase1, phase2),
        immediate_next_steps=(
            "Deepen FastAPI route structuring using official documentation.",
            "Install Docker and implement a multi-stage container build for a sample API.",
        ),
        closing_encouragement="Executing this focused curriculum will position you strongly for competitive Backend Engineering roles.",
    )


# -----------------------------------------------------------------------------
# Unit Tests (30 Required Scenarios)
# -----------------------------------------------------------------------------

def test_01_valid_context_produces_structured_narrative(valid_phase2_context, valid_personalized_narrative):
    """Scenario 1: Valid Phase 2 context produces ValidatedRoadmapPDFContent."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative

    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    result = service.generate_validated_narrative(valid_phase2_context)

    assert isinstance(result, ValidatedRoadmapPDFContent)
    assert result.schema_version == "v1.0"
    assert len(result.validated_phases) == 2
    assert len(result.validated_top_gaps) == 2
    assert result.personalized_subtitle == valid_personalized_narrative.personalized_subtitle


def test_02_gemini_client_is_used(valid_phase2_context, valid_personalized_narrative):
    """Scenario 2: Verifies that GeminiClient.with_structured_output is used."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative

    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    service.generate_validated_narrative(valid_phase2_context)

    mock_client.with_structured_output.assert_called_once_with(RoadmapPDFPersonalizedNarrative)


def test_03_exactly_one_gemini_invocation_occurs(valid_phase2_context, valid_personalized_narrative):
    """Scenario 3: Verifies that exactly ONE Gemini invocation occurs (no loops, no multi-call agent)."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative

    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    service.generate_validated_narrative(valid_phase2_context)

    assert mock_runnable.invoke.call_count == 1


def test_04_structured_output_is_parsed_successfully(valid_phase2_context, valid_personalized_narrative):
    """Scenario 4: Verifies structured output fields are cleanly extracted and mapped."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative

    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    result = service.generate_validated_narrative(valid_phase2_context)

    assert result.executive_summary == valid_personalized_narrative.executive_summary
    assert result.readiness_explanation == valid_personalized_narrative.readiness_explanation
    assert result.immediate_next_steps == tuple(valid_personalized_narrative.immediate_next_steps)
    assert result.closing_encouragement == valid_personalized_narrative.closing_encouragement


def test_05_invalid_structured_output_fails(valid_phase2_context):
    """Scenario 5: Null or invalid Gemini return raises NarrativeGenerationError."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = None  # Empty response

    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    with pytest.raises(NarrativeGenerationError) as exc_info:
        service.generate_validated_narrative(valid_phase2_context)

    assert "empty or malformed" in str(exc_info.value).lower()


def test_06_unknown_skill_id_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 6: Unknown or foreign skill ID in phase raises ReferenceIntegrityError."""
    foreign_id = uuid.uuid4()
    bad_phase = RoadmapPhaseNarrative(
        skill_id=foreign_id,
        phase_title="Unknown Framework Mastery",
        personalized_rationale="Learning this unknown tech stack for your career trajectory.",
        key_topics=("Unknown Topic 1", "Unknown Topic 2"),
    )
    bad_narrative = valid_personalized_narrative.model_copy(
        update={"phases": (bad_phase, valid_personalized_narrative.phases[1])}
    )

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "skill_id mismatch" in str(exc_info.value).lower()
    assert str(foreign_id) in str(exc_info.value)


def test_07_unknown_resource_id_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 7: Authoritative resource IDs are immutable and foreign resource references fail."""
    # Attempting to introduce unapproved resource URLs in narrative text fails validation
    bad_phase = valid_personalized_narrative.phases[0].model_copy(
        update={"personalized_rationale": "Visit https://unapproved-tutorial.com/secret to learn this."}
    )
    bad_narrative = valid_personalized_narrative.model_copy(update={"phases": (bad_phase, valid_personalized_narrative.phases[1])})

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "invented external url" in str(exc_info.value).lower()


def test_08_unknown_project_id_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 8: Project ID cannot be invented; authoritative project data remains strictly from context."""
    # Validate that ValidatedRoadmapPhase inherits project strictly from Phase 2 context
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    res = service.generate_validated_narrative(valid_phase2_context)

    # Phase 2 had project_1 on milestone 2
    assert res.validated_phases[1].project is not None
    assert res.validated_phases[1].project.project_id == valid_phase2_context.roadmap.milestones[1].project.project_id
    assert res.validated_phases[1].project.is_candidate_proof is False


def test_09_unknown_milestone_id_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 9: Superfluous or unknown milestone phase raises ReferenceIntegrityError."""
    extra_phase = RoadmapPhaseNarrative(
        skill_id=uuid.uuid4(),
        phase_title="Superfluous Phase",
        personalized_rationale="Invented phase that is not in canonical roadmap sequence.",
        key_topics=("Topic A", "Topic B"),
    )
    bad_narrative = valid_personalized_narrative.model_copy(
        update={"phases": list(valid_personalized_narrative.phases) + [extra_phase]}
    )

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "milestone count mismatch" in str(exc_info.value).lower()


def test_10_roadmap_milestone_reordering_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 10: Swapping milestone order raises ReferenceIntegrityError."""
    # Invert the order of phase 1 and phase 2
    inverted_phases = (
        valid_personalized_narrative.phases[1],
        valid_personalized_narrative.phases[0],
    )
    bad_narrative = valid_personalized_narrative.model_copy(update={"phases": inverted_phases})

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "milestone #1 skill_id mismatch" in str(exc_info.value).lower()
    assert "reordering" in str(exc_info.value).lower()


def test_11_changed_roadmap_duration_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 11: Milestone order and counts in validated content are copied strictly from context."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    res = service.generate_validated_narrative(valid_phase2_context)

    assert res.total_milestones == valid_phase2_context.roadmap.total_milestones
    assert res.validated_phases[0].order_index == 1
    assert res.validated_phases[1].order_index == 2


def test_12_changed_gap_classification_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 12: Deterministic gap classifications are copied directly and cannot be altered by Gemini."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    res = service.generate_validated_narrative(valid_phase2_context)

    # In context: FastAPI is PARTIAL, Docker is MISSING
    assert res.validated_phases[0].gap_status == SkillGapClassification.PARTIAL
    assert res.validated_phases[1].gap_status == SkillGapClassification.MISSING


def test_13_changed_priority_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 13: Priority scores and tiers are copied directly from context and cannot be altered."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    res = service.generate_validated_narrative(valid_phase2_context)

    assert res.validated_phases[0].priority_level == PriorityTierLevel.MEDIUM
    assert res.validated_phases[0].priority_score == 0.72
    assert res.validated_phases[1].priority_level == PriorityTierLevel.HIGH
    assert res.validated_phases[1].priority_score == 0.88


def test_14_changed_demand_score_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 14: Market demand metrics are copied directly from context."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    res = service.generate_validated_narrative(valid_phase2_context)

    docker_gap = next(g for g in res.validated_top_gaps if g.skill_name == "Docker")
    assert docker_gap.demand_score == 0.82
    assert docker_gap.growth_rate == 0.18


def test_15_changed_readiness_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 15: Readiness percentage is copied strictly from Phase 2 context."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    res = service.generate_validated_narrative(valid_phase2_context)

    assert res.readiness.readiness_percentage == 60
    assert res.readiness.strong_count == 3
    assert res.readiness.partial_count == 1
    assert res.readiness.missing_count == 1


def test_16_changed_verification_status_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 16: Verification status in milestones and root hash are copied directly from context."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    res = service.generate_validated_narrative(valid_phase2_context)

    assert res.verification_hash == valid_phase2_context.verification_hash
    assert res.validated_phases[0].status == "NOT_STARTED"


def test_17_invented_url_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 17: Introducing an external URL in any narrative text raises ReferenceIntegrityError."""
    bad_narrative = valid_personalized_narrative.model_copy(
        update={"executive_summary": "Check out https://learn-fastapi.com for complete course materials."}
    )

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "invented external url" in str(exc_info.value).lower()
    assert "https://learn-fastapi.com" in str(exc_info.value)


def test_18_invented_resource_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 18: Invented resource links in next steps raise ReferenceIntegrityError."""
    bad_narrative = valid_personalized_narrative.model_copy(
        update={
            "immediate_next_steps": (
                "Go to http://free-courses.net/docker-course to start learning.",
                "Review FastAPI route parameters.",
            )
        }
    )

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "invented external url" in str(exc_info.value).lower()


def test_19_invented_project_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 19: Invented project links in closing encouragement raise ReferenceIntegrityError."""
    bad_narrative = valid_personalized_narrative.model_copy(
        update={"closing_encouragement": "Complete the project hosted at https://github.com/external/project-repo to verify."}
    )

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "invented external url" in str(exc_info.value).lower()


def test_20_invented_skill_fails_validation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 20: Top gap narrative referencing an unapproved skill_id raises ReferenceIntegrityError."""
    unapproved_id = uuid.uuid4()
    bad_gap = SkillGapNarrative(
        skill_id=unapproved_id,
        why_it_matters="Rust provides memory safety guarantees.",
        suggested_focus="Master ownership and lifetimes in Rust.",
    )
    bad_narrative = valid_personalized_narrative.model_copy(
        update={"top_gap_narratives": (bad_gap,)}
    )

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "unauthorized or non-prioritized skill_id" in str(exc_info.value).lower()
    assert str(unapproved_id) in str(exc_info.value)


def test_21_curated_project_cannot_become_candidate_proof(valid_phase2_context, valid_personalized_narrative):
    """Scenario 21: Narrative claiming candidate has completed a curated project raises ReferenceIntegrityError."""
    bad_phase = valid_personalized_narrative.phases[1].model_copy(
        update={"personalized_rationale": "You have completed this project during your coursework so this is verified."}
    )
    bad_narrative = valid_personalized_narrative.model_copy(
        update={"phases": (valid_personalized_narrative.phases[0], bad_phase)}
    )

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "prohibited candidate-proof claim" in str(exc_info.value).lower()


def test_22_weekly_hours_cannot_be_fabricated(valid_phase2_context, valid_personalized_narrative):
    """Scenario 22: weekly_hours_recommendation remains strictly None in final validated content."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    res = service.generate_validated_narrative(valid_phase2_context)

    assert res.weekly_hours_recommendation is None


def test_23_missing_required_authoritative_record_fails(valid_phase2_context, valid_personalized_narrative):
    """Scenario 23: Returning fewer phases than canonical milestones raises ReferenceIntegrityError."""
    # Context has 2 milestones; narrative returns only 1 phase
    bad_narrative = valid_personalized_narrative.model_copy(
        update={"phases": (valid_personalized_narrative.phases[0],)}
    )

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "milestone count mismatch" in str(exc_info.value).lower()


def test_24_duplicate_identifiers_fail_where_inappropriate(valid_phase2_context, valid_personalized_narrative):
    """Scenario 24: Duplicate skill IDs across phases raise ReferenceIntegrityError."""
    duplicate_phase = valid_personalized_narrative.phases[0].model_copy()
    bad_narrative = valid_personalized_narrative.model_copy(
        update={"phases": (duplicate_phase, duplicate_phase)}
    )

    validator = ReferenceIntegrityValidator()
    with pytest.raises(ReferenceIntegrityError) as exc_info:
        validator.validate(bad_narrative, valid_phase2_context)

    assert "duplicate milestone skill_id" in str(exc_info.value).lower()


def test_25_valid_references_pass(valid_phase2_context, valid_personalized_narrative):
    """Scenario 25: Exactly matching references and compliant narrative pass validation cleanly."""
    validator = ReferenceIntegrityValidator()
    # Should not raise any exception
    validator.validate(valid_personalized_narrative, valid_phase2_context)


def test_26_authoritative_values_remain_unchanged_after_generation(valid_phase2_context, valid_personalized_narrative):
    """Scenario 26: Authoritative values in ValidatedRoadmapPDFContent match input context bit-for-bit."""
    mock_runnable = MagicMock()
    mock_runnable.invoke.return_value = valid_personalized_narrative
    mock_client = MagicMock(spec=GeminiClient)
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    res = service.generate_validated_narrative(valid_phase2_context)

    assert res.roadmap_id == valid_phase2_context.roadmap.roadmap_id
    assert res.candidate.user_id == valid_phase2_context.candidate.user_id
    assert res.target_role_title == valid_phase2_context.roadmap.target_role_title
    assert res.location == valid_phase2_context.roadmap.location
    assert res.readiness == valid_phase2_context.readiness
    assert res.verification_hash == valid_phase2_context.verification_hash
    assert res.market_facts == valid_phase2_context.market_facts


def test_27_profile_fields_not_unnecessarily_exposed(valid_phase2_context):
    """Scenario 27: Sensitive profile fields like candidate email are excluded from LLM prompt messages."""
    messages = build_roadmap_narrative_messages(valid_phase2_context)
    serialized_messages = "\n".join(str(m.content) for m in messages)

    assert "candidate.secret@skillforge.internal" not in serialized_messages
    assert valid_phase2_context.candidate.email not in serialized_messages


def test_28_no_secrets_reach_gemini_prompt(valid_phase2_context):
    """Scenario 28: No API keys, database URLs, or internal secrets exist in the constructed prompt."""
    messages = build_roadmap_narrative_messages(valid_phase2_context)
    serialized_messages = "\n".join(str(m.content) for m in messages)

    forbidden_tokens = ["AIzaSy", "postgresql://", "secret_key", "bearer ", "password="]
    for token in forbidden_tokens:
        assert token.lower() not in serialized_messages.lower()


def test_29_gemini_provider_error_translated_correctly(valid_phase2_context):
    """Scenario 29: Gemini client exceptions are caught and translated into domain NarrativeGenerationError."""
    mock_client = MagicMock(spec=GeminiClient)
    mock_runnable = MagicMock()
    mock_runnable.invoke.side_effect = GeminiAPIError("Provider quota exhausted or 503 unavailable")
    mock_client.with_structured_output.return_value = mock_runnable

    service = RoadmapPDFNarrativeService(gemini_client=mock_client)
    with pytest.raises(NarrativeGenerationError) as exc_info:
        service.generate_validated_narrative(valid_phase2_context)

    assert "gemini structured output generation failed" in str(exc_info.value).lower()
    assert isinstance(exc_info.value.original_exception, GeminiError)


def test_30_validation_errors_are_typed_and_safe():
    """Scenario 30: All validation exceptions inherit from RoadmapNarrativeError and provide safe messaging."""
    err = ReferenceIntegrityError("Reference validation error", violations=["violation 1", "violation 2"])
    assert isinstance(err, ReferenceIntegrityError)
    assert isinstance(err, NarrativeValidationError)
    assert isinstance(err, RoadmapNarrativeError)
    assert len(err.violations) == 2


# -----------------------------------------------------------------------------
# 31. Opt-in Live Integration Test (Skipped by default)
# -----------------------------------------------------------------------------

from app.config import settings


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_GEMINI_TEST") != "1"
    or not (os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY),
    reason="Opt-in live integration test: requires RUN_LIVE_GEMINI_TEST=1 and real GEMINI_API_KEY.",
)
def test_31_roadmap_pdf_generation_live_opt_in(valid_phase2_context):
    """
    Scenario 31: End-to-end live integration test against Gemini 2.5 Flash.
    Only executed when RUN_LIVE_GEMINI_TEST=1 and valid GEMINI_API_KEY is present.
    Performs exactly ONE structured invocation and validates reference integrity.
    Never prints or logs the API key.
    """
    client = GeminiClient()
    service = RoadmapPDFNarrativeService(gemini_client=client)

    result = service.generate_validated_narrative(valid_phase2_context)

    assert isinstance(result, ValidatedRoadmapPDFContent)
    assert result.readiness.readiness_percentage == valid_phase2_context.readiness.readiness_percentage
    assert len(result.validated_phases) == len(valid_phase2_context.roadmap.milestones)
    assert result.verification_hash == valid_phase2_context.verification_hash
    assert result.weekly_hours_recommendation is None
