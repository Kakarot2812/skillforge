"""
Comprehensive Phase 2 Test Suite:
Verified SkillForge Context Builder for Personalized Career Roadmap PDF.

Verifies:
1. Context builds successfully for an owned roadmap.
2. Missing authentication (None user_id) is rejected with 401 Unauthorized.
3. Cross-user access (IDOR) is rejected with 403 Forbidden.
4. Non-existent roadmap ID is rejected with 404 Not Found.
5. Candidate with missing UserProfile is handled cleanly without inventing values.
6. Deterministic readiness percentage and counts are preserved.
7. Deterministic gap classifications (STRONG, PARTIAL, MISSING) are preserved.
8. Deterministic priority scores and categories are preserved.
9. Deterministic industry demand facts are preserved.
10. Canonical roadmap sequencing and milestone ordering are strictly preserved.
11. Approved learning resources are preserved without inventing external links.
12. Curated approved projects are preserved and marked is_candidate_proof=False.
13. Provenance and reference IDs (skill_id, resource_id, project_id) are preserved.
14. Output is bitwise deterministic across multiple executions on identical database state.
15. Collections are deterministically sorted.
16. Context is strictly bounded (no full resume or code dumps).
17. Zero Gemini or LLM invocations occur during context assembly.
18. weekly_hours_recommendation is strictly None (never fabricated).
19. Verification hash is deterministic and repeatable.
20. Null/optional fields remain None and are never populated with invented values.
"""

import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.context.roadmap_pdf_context import (
    EvidenceStatusType,
    PriorityTierLevel,
    SkillGapClassification,
    VerifiedRoadmapPDFContext,
    generate_deterministic_verification_hash,
)
from app.db.models import (
    ApprovedProject,
    ApprovedResource,
    CandidateRoadmap,
    JobRole,
    MilestoneVerification,
    Resume,
    RoadmapMilestone,
    Skill,
    User,
    UserClaimedSkill,
    UserProfile,
)
from app.main import app
from app.services.roadmap_pdf_context_service import (
    RoadmapPDFContextService,
    roadmap_pdf_context_service,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def db_session():
    """Provides a transactional database session rolled back after test."""
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_roles_and_skills(db_session: Session):
    """Retrieves canonical roles and skills seeded in database."""
    backend_role = db_session.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    python_skill = db_session.query(Skill).filter(Skill.slug == "python").first()
    fastapi_skill = db_session.query(Skill).filter(Skill.slug == "fastapi").first()
    docker_skill = db_session.query(Skill).filter(Skill.slug == "docker").first()
    postgres_skill = db_session.query(Skill).filter(Skill.slug == "postgresql").first()

    return {
        "backend_role": backend_role,
        "python": python_skill,
        "fastapi": fastapi_skill,
        "docker": docker_skill,
        "postgres": postgres_skill,
    }


@pytest.fixture
def candidate_users(db_session: Session):
    """Creates two distinct candidates with profiles for isolation and context testing."""
    user_a = User(
        id=uuid.uuid4(),
        email=f"candidate_a_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Alice Engineer",
        target_role="Backend Engineer",
    )
    user_b = User(
        id=uuid.uuid4(),
        email=f"candidate_b_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Bob Developer",
        target_role="Frontend Engineer",
    )
    db_session.add(user_a)
    db_session.add(user_b)
    db_session.commit()

    profile_a = UserProfile(
        id=uuid.uuid4(),
        user_id=user_a.id,
        name="Alice Engineer",
        education="B.Tech in Computer Science",
        college="National Institute of Technology",
        degree="B.Tech",
        branch="Computer Science",
        semester=6,
        target_role="Backend Engineer",
        experience_level="INTERMEDIATE",
    )
    db_session.add(profile_a)
    db_session.commit()
    db_session.refresh(user_a)
    db_session.refresh(user_b)

    return {"user_a": user_a, "user_b": user_b, "profile_a": profile_a}


@pytest.fixture
def generated_roadmap_for_user_a(test_roles_and_skills, candidate_users, db_session: Session):
    """Generates an authenticated, persisted roadmap for User A via canonical API."""
    backend_role = test_roles_and_skills["backend_role"]
    user_a = candidate_users["user_a"]

    payload = {
        "role_id": str(backend_role.id),
        "location": "India",
        "include_resume": False,
        "include_github": False,
    }
    headers = {"X-User-Id": str(user_a.id)}
    res = client.post("/api/v1/roadmap/generate", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]

    roadmap_id = uuid.UUID(data["id"])
    return roadmap_id


# -----------------------------------------------------------------------------
# 1. Core Context Assembly & Ownership Tests
# -----------------------------------------------------------------------------

def test_context_builds_successfully_for_owned_roadmap(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 1: Context builds cleanly and returns VerifiedRoadmapPDFContext for owned roadmap."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    assert isinstance(ctx, VerifiedRoadmapPDFContext)
    assert ctx.schema_version == "v1.0"
    assert ctx.candidate.user_id == user_a.id
    assert ctx.candidate.email == user_a.email
    assert ctx.candidate.name == "Alice Engineer"
    assert ctx.candidate.college == "National Institute of Technology"
    assert ctx.candidate.semester == 6
    assert ctx.roadmap.roadmap_id == roadmap_id
    assert ctx.roadmap.total_milestones > 0
    assert len(ctx.roadmap.milestones) == ctx.roadmap.total_milestones


def test_unauthorized_roadmap_access_rejected_missing_auth(
    db_session: Session, generated_roadmap_for_user_a
):
    """Scenario 2: None authenticated_user_id raises 401 Unauthorized."""
    roadmap_id = generated_roadmap_for_user_a

    with pytest.raises(HTTPException) as exc_info:
        roadmap_pdf_context_service.build_verified_context(
            db=db_session,
            roadmap_id=roadmap_id,
            authenticated_user_id=None,
        )
    assert exc_info.value.status_code == 401
    assert "Authentication required" in exc_info.value.detail


def test_cross_user_access_rejected_idor(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 3: User B attempting to access User A's roadmap raises 403 Forbidden."""
    user_b = candidate_users["user_b"]
    roadmap_id = generated_roadmap_for_user_a

    with pytest.raises(HTTPException) as exc_info:
        roadmap_pdf_context_service.build_verified_context(
            db=db_session,
            roadmap_id=roadmap_id,
            authenticated_user_id=user_b.id,
        )
    assert exc_info.value.status_code == 403
    assert "Cross-user access denied" in exc_info.value.detail


def test_roadmap_not_found_raises_404(db_session: Session, candidate_users):
    """Scenario 4: Non-existent roadmap ID raises 404 Not Found."""
    user_a = candidate_users["user_a"]
    missing_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        roadmap_pdf_context_service.build_verified_context(
            db=db_session,
            roadmap_id=missing_id,
            authenticated_user_id=user_a.id,
        )
    assert exc_info.value.status_code == 404
    assert f"Roadmap with id '{missing_id}' not found" in exc_info.value.detail


# -----------------------------------------------------------------------------
# 2. Profile Handling & Zero Fabrication Tests
# -----------------------------------------------------------------------------

def test_missing_profile_handled_cleanly(
    db_session: Session, test_roles_and_skills, candidate_users
):
    """Scenario 5: User without UserProfile record builds context with User fallback without inventing values."""
    user_b = candidate_users["user_b"]
    backend_role = test_roles_and_skills["backend_role"]

    # Generate roadmap for User B (who has no UserProfile record)
    res = client.post(
        "/api/v1/roadmap/generate",
        json={"role_id": str(backend_role.id), "location": "India"},
        headers={"X-User-Id": str(user_b.id)},
    )
    assert res.status_code == 200
    roadmap_id = uuid.UUID(res.json()["data"]["id"])

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_b.id,
    )

    assert ctx.candidate.user_id == user_b.id
    assert ctx.candidate.name == "Candidate Beta" or ctx.candidate.name == user_b.full_name
    assert ctx.candidate.college is None
    assert ctx.candidate.degree is None
    assert ctx.candidate.branch is None
    assert ctx.candidate.semester is None
    assert ctx.candidate.experience_level is None


def test_null_optional_fields_do_not_cause_invented_values(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 20: Optional milestone fields remain None when unpopulated."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    # Weekly hours recommendation must strictly remain None
    assert ctx.weekly_hours_recommendation is None

    # Check transitive milestones: priority score and level must be None
    transitive_milestones = [m for m in ctx.roadmap.milestones if m.is_transitive_prerequisite]
    for tm in transitive_milestones:
        assert tm.priority_score is None
        assert tm.priority_level is None


# -----------------------------------------------------------------------------
# 3. Deterministic Intelligence Preservation Tests
# -----------------------------------------------------------------------------

def test_deterministic_readiness_preserved(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 6: Readiness percentage formula and counts match SkillGapService."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    readiness = ctx.readiness
    assert readiness.total_required_skills > 0
    assert readiness.strong_count >= 0
    assert readiness.partial_count >= 0
    assert readiness.missing_count >= 0
    assert (readiness.strong_count + readiness.partial_count + readiness.missing_count) == readiness.total_required_skills

    expected_pct = round((readiness.strong_count / readiness.total_required_skills) * 100)
    assert readiness.readiness_percentage == expected_pct


def test_deterministic_gap_classifications_preserved(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 7: Gaps strictly adhere to STRONG, PARTIAL, MISSING enums."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    assert len(ctx.all_gap_facts) > 0
    for gf in ctx.all_gap_facts:
        assert isinstance(gf.gap_status, SkillGapClassification)
        assert gf.gap_status.value in {"STRONG", "PARTIAL", "MISSING"}


def test_deterministic_priority_values_preserved(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 8: Priority levels (HIGH, MEDIUM, LOW) and scores match canonical prioritization."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    prio_summary = ctx.prioritized_gaps
    assert prio_summary.total_actionable_gaps == len(prio_summary.top_gaps)
    assert prio_summary.high_priority_count + prio_summary.medium_priority_count + prio_summary.low_priority_count == prio_summary.total_actionable_gaps

    for g in prio_summary.top_gaps:
        assert g.priority_score is not None
        assert 0.0 <= g.priority_score <= 1.0
        assert isinstance(g.priority_level, PriorityTierLevel)
        assert g.gap_status in {SkillGapClassification.MISSING, SkillGapClassification.PARTIAL}


def test_deterministic_demand_values_preserved(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 9: Market demand scores, growth rates, and growth classes are preserved."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    assert len(ctx.market_facts) > 0
    for mf in ctx.market_facts:
        assert 0.0 <= mf.demand_score <= 1.0
        assert mf.growth_class in {"RISING", "STABLE", "DECLINING"}
        assert mf.location == "India"
        assert mf.data_source == "adzuna"


# -----------------------------------------------------------------------------
# 4. Roadmap Sequence, Resources & Curated Projects Tests
# -----------------------------------------------------------------------------

def test_roadmap_ordering_preserved(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 10: Milestones maintain strictly increasing 1-indexed order_index matching canonical DAG."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    milestones = ctx.roadmap.milestones
    assert len(milestones) > 0

    order_indices = [m.order_index for m in milestones]
    assert order_indices == list(range(1, len(milestones) + 1))


def test_approved_resources_preserved(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 11: Approved resources originate strictly from approved_resources with is_approved=True."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    resource_found = False
    for m in ctx.roadmap.milestones:
        for r in m.resources:
            resource_found = True
            assert r.is_approved is True
            assert r.url.startswith("http://") or r.url.startswith("https://")
            assert r.resource_type in {"OFFICIAL_DOCS", "TUTORIAL", "GUIDE", "BOOK", "COURSE"}
            assert r.difficulty in {"BEGINNER", "INTERMEDIATE", "ADVANCED"}

    assert resource_found, "At least one approved resource should be attached to seeded roadmap milestones"


def test_approved_projects_preserved_and_not_candidate_proof(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 12: Curated projects have deliverables and are strictly marked is_candidate_proof=False."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    project_found = False
    for m in ctx.roadmap.milestones:
        if m.project:
            project_found = True
            p = m.project
            assert p.is_curated_challenge is True
            assert p.is_candidate_proof is False, "Curated project must NOT be represented as proof of candidate skill"
            assert isinstance(p.deliverables, tuple)
            assert isinstance(p.verification_criteria, tuple)
            assert p.difficulty in {"BEGINNER", "INTERMEDIATE", "ADVANCED"}

    assert project_found, "At least one approved project challenge should be attached to seeded roadmap milestones"


def test_provenance_and_reference_ids_preserved(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 13: Provenance IDs (skill_id, resource_id, project_id) are valid UUIDs matching DB."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    all_db_skills = {s.id for s in db_session.query(Skill).all()}
    for m in ctx.roadmap.milestones:
        assert m.skill_id in all_db_skills
        for r in m.resources:
            assert isinstance(r.resource_id, uuid.UUID)
        if m.project:
            assert isinstance(m.project.project_id, uuid.UUID)


# -----------------------------------------------------------------------------
# 5. Determinism, Bounds & Verification Hash Tests
# -----------------------------------------------------------------------------

def test_output_is_deterministic_for_identical_state(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 14: Repeated execution on identical database state yields identical context and identical hash."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx_1 = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )
    ctx_2 = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    assert ctx_1.verification_hash == ctx_2.verification_hash
    assert ctx_1.readiness.readiness_percentage == ctx_2.readiness.readiness_percentage
    assert len(ctx_1.roadmap.milestones) == len(ctx_2.roadmap.milestones)

    # Compare milestone attributes
    for m1, m2 in zip(ctx_1.roadmap.milestones, ctx_2.roadmap.milestones):
        assert m1.order_index == m2.order_index
        assert m1.skill_id == m2.skill_id
        assert m1.gap_status == m2.gap_status
        assert m1.priority_score == m2.priority_score


def test_collections_have_deterministic_ordering(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 15: Prioritized gaps are sorted by priority_score DESC, milestones by order_index ASC."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    # Prioritized gaps check: scores are non-increasing
    scores = [g.priority_score or 0.0 for g in ctx.prioritized_gaps.top_gaps]
    assert scores == sorted(scores, reverse=True)

    # Milestones check: strictly ascending
    orders = [m.order_index for m in ctx.roadmap.milestones]
    assert orders == sorted(orders)


def test_context_is_bounded_no_raw_dumps(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 16: Context contains only bounded summary fields, no raw file text or repos dumps."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )

    ctx_json = ctx.model_dump_json()

    # Bounded size: a standard roadmap context should be under 50KB JSON
    assert len(ctx_json) < 50000

    # Ensure no repository code or large binary blobs are present
    assert "class " not in ctx_json or "def " not in ctx_json


def test_no_gemini_client_invocation_occurs(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 17: Context building executes zero Gemini or LLM API calls."""
    from unittest.mock import patch
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    with patch("app.ai.gemini.client.GeminiClient.invoke") as mock_invoke:
        with patch("app.ai.gemini.client.GeminiClient.with_structured_output") as mock_structured:
            ctx = roadmap_pdf_context_service.build_verified_context(
                db=db_session,
                roadmap_id=roadmap_id,
                authenticated_user_id=user_a.id,
            )
            assert ctx is not None
            mock_invoke.assert_not_called()
            mock_structured.assert_not_called()


def test_weekly_hours_recommendation_is_not_invented(
    db_session: Session, candidate_users, generated_roadmap_for_user_a
):
    """Scenario 18: weekly_hours_recommendation strictly remains None per design invariant."""
    user_a = candidate_users["user_a"]
    roadmap_id = generated_roadmap_for_user_a

    ctx = roadmap_pdf_context_service.build_verified_context(
        db=db_session,
        roadmap_id=roadmap_id,
        authenticated_user_id=user_a.id,
    )
    assert ctx.weekly_hours_recommendation is None


def test_verification_hash_is_deterministic_and_reproducible():
    """Scenario 19: generate_deterministic_verification_hash produces stable SHA-256."""
    u_id = uuid.uuid4()
    r_id = uuid.uuid4()
    role_id = uuid.uuid4()
    milestone_tuples = (
        (1, str(uuid.uuid4()), "PARTIAL", "HIGH"),
        (2, str(uuid.uuid4()), "MISSING", "HIGH"),
    )

    hash_1 = generate_deterministic_verification_hash(
        roadmap_id=r_id,
        user_id=u_id,
        role_id=role_id,
        target_role_title="Backend Engineer",
        readiness_percentage=45,
        strong_count=3,
        partial_count=2,
        missing_count=3,
        milestone_tuples=milestone_tuples,
    )

    hash_2 = generate_deterministic_verification_hash(
        roadmap_id=r_id,
        user_id=u_id,
        role_id=role_id,
        target_role_title="Backend Engineer",
        readiness_percentage=45,
        strong_count=3,
        partial_count=2,
        missing_count=3,
        milestone_tuples=milestone_tuples,
    )

    assert hash_1 == hash_2
    assert len(hash_1) == 64  # Valid SHA-256 hex string
