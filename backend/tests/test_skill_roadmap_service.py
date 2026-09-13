"""
Comprehensive test suite for Phase 3: Static Roadmap Schemas & Service.

Covers:
1. Catalog retrieval & deterministic ordering (12 domains)
2. Detail retrieval (stages, skills, resources, practice problems)
3. Canonical skill mapping (mapped vs nullable)
4. Curated ordering (stage_order + skill_order)
5. Recommended ordering:
   - Pure topological sort (Kahn's algorithm)
   - Every prerequisite precedes its dependent skill across all 12 roadmaps
   - Deterministic output
   - Cycle detection raises PrerequisiteCycleError
   - Strictly independent of user progress, skill gaps, candidate profile, and P4
6. Relationship validation (wrong roadmap/skill, invalid IDs, invalid problem IDs)
7. Skill progress tracking:
   - Supported statuses: NOT_STARTED, LEARNING, DONE, SKIPPED
   - Idempotent upserts, created_at and updated_at populated
   - Rejection of invalid statuses
8. Practice problem progress tracking:
   - Supported statuses: NOT_STARTED, IN_PROGRESS, COMPLETED
   - completed_at set on COMPLETED, cleared on transition away
   - Duplicate problem IDs remain strictly scoped by roadmap_skill_id
   - Rejection of invalid statuses
9. Progress schemas match actual Phase 1 database models:
   - No started_at, completed_at, notes on UserProgressItem
   - No solution_code on UserPracticeProgressUpdateRequest
   - No attempts_count on UserPracticeProgressItem
10. User isolation (User A progress never leaks to User B)
11. Roadmap progress summary metrics
"""

import inspect
import uuid
from datetime import datetime, timezone
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

# SQLite hook for JSONB compatibility in unit tests
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

from app.db.database import Base
from app.db.models import (
    JobRole,
    LearningResource,
    Roadmap,
    RoadmapPrerequisite,
    RoadmapSkill,
    RoadmapStage,
    Skill,
    User,
    UserPracticeProgress,
    UserRoadmapProgress,
)
from app.db.seed_roadmaps import seed_roadmaps
import app.services.skill_roadmap_service as srs_module
from app.schemas.skill_roadmap import (
    RoadmapDetailData,
    RoadmapListItem,
    RoadmapSkillItem,
    RoadmapSummary,
    UserPracticeProgressItem,
    UserPracticeProgressUpdateRequest,
    UserProgressItem,
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
    SkillRoadmapService,
)


@pytest.fixture
def db_session():
    """In-memory SQLite database seeded with canonical roles, skills, and full static roadmap catalog."""
    engine = create_engine("sqlite:///:memory:")
    # Note: Strictly decoupled: NO IndustrySkillDemand or SkillGap tables needed!
    tables = [
        JobRole.__table__,
        Skill.__table__,
        User.__table__,
        Roadmap.__table__,
        RoadmapStage.__table__,
        RoadmapSkill.__table__,
        RoadmapPrerequisite.__table__,
        LearningResource.__table__,
        UserRoadmapProgress.__table__,
        UserPracticeProgress.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. Seed canonical job roles (from migration 0007)
    canonical_roles_data = [
        {"id": uuid.UUID("9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c"), "title": "Backend Engineer", "slug": "backend-engineer", "category": "Engineering"},
        {"id": uuid.UUID("0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d"), "title": "Full Stack Engineer", "slug": "full-stack-engineer", "category": "Engineering"},
        {"id": uuid.UUID("1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e"), "title": "Frontend Engineer", "slug": "frontend-engineer", "category": "Engineering"},
        {"id": uuid.UUID("2c3d4e5f-6a7b-8c9d-0e1f-2a3b4c5d6e7f"), "title": "Cloud/DevOps Engineer", "slug": "cloud-devops-engineer", "category": "Cloud & Infrastructure"},
        {"id": uuid.UUID("3d4e5f6a-7b8c-9d0e-1f2a-3b4c5d6e7f8a"), "title": "AI/ML Engineer", "slug": "ai-ml-engineer", "category": "Data & AI"},
    ]
    for rd in canonical_roles_data:
        session.add(JobRole(**rd))

    # 2. Seed canonical skills (from migration 0003)
    seed_skills_data = [
        ("Python", "python"), ("TypeScript", "typescript"), ("JavaScript", "javascript"),
        ("Java", "java"), ("Go", "go"), ("SQL", "sql"), ("C++", "cpp"), ("C#", "csharp"),
        ("React", "react"), ("Next.js", "nextjs"), ("Tailwind CSS", "tailwindcss"),
        ("HTML", "html"), ("CSS", "css"), ("FastAPI", "fastapi"), ("Node.js", "nodejs"),
        ("Spring Boot", "spring-boot"), ("PostgreSQL", "postgresql"), ("MongoDB", "mongodb"),
        ("Redis", "redis"), ("pgvector", "pgvector"), ("Docker", "docker"),
        ("Kubernetes", "kubernetes"), ("AWS", "aws"), ("GitHub Actions", "github-actions"),
        ("Git", "git"), ("REST APIs", "rest-apis"), ("Pytest", "pytest"),
        ("Docker Compose", "docker-compose"), ("PyTorch", "pytorch"), ("Pandas", "pandas")
    ]
    for name, slug in seed_skills_data:
        session.add(Skill(id=uuid.uuid4(), name=name, slug=slug))

    session.commit()

    # 3. Seed complete static roadmaps
    seed_roadmaps(session, auto_commit=True, validate=True)

    yield session
    session.close()


@pytest.fixture
def service():
    return SkillRoadmapService()


@pytest.fixture
def user_a(db_session):
    u = User(id=uuid.uuid4(), email="user_a@example.com", full_name="User A")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def user_b(db_session):
    u = User(id=uuid.uuid4(), email="user_b@example.com", full_name="User B")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


# -----------------------------------------------------------------------------
# 1. Zero Coupling to P4 / SkillGap Verification
# -----------------------------------------------------------------------------

def test_zero_coupling_to_p4_and_skill_gap():
    """Verify static roadmap service has zero imports or dependencies on SkillGapService or P4."""
    source = inspect.getsource(srs_module)
    forbidden_terms = [
        "SkillGapService",
        "SkillGap",
        "IndustrySkillDemand",
        "roadmap_engine",
        "from app.services.roadmap_service",
        "import roadmap_service",
        "priority_score",
        "priority_level",
        "gap_status",
        "demand_score",
    ]
    for term in forbidden_terms:
        assert term not in source, f"Forbidden term '{term}' found in static skill roadmap service source!"


# -----------------------------------------------------------------------------
# 2. Schema / DB Model Matching Tests
# -----------------------------------------------------------------------------

def test_progress_schemas_match_database_models():
    """Verify that progress schemas match Phase 1 DB models and do not contain unsupported fields."""
    # UserProgressItem vs UserRoadmapProgress
    expected_user_progress_fields = {"id", "user_id", "roadmap_skill_id", "status", "created_at", "updated_at"}
    actual_user_progress_fields = set(UserProgressItem.model_fields.keys())
    assert actual_user_progress_fields == expected_user_progress_fields

    unsupported_skill_fields = {"started_at", "completed_at", "notes"}
    assert unsupported_skill_fields.isdisjoint(actual_user_progress_fields)

    # UserPracticeProgressUpdateRequest
    expected_update_fields = {"status"}
    actual_update_fields = set(UserPracticeProgressUpdateRequest.model_fields.keys())
    assert actual_update_fields == expected_update_fields
    assert "solution_code" not in actual_update_fields

    # UserPracticeProgressItem vs UserPracticeProgress
    expected_practice_item_fields = {
        "id", "user_id", "roadmap_skill_id", "problem_id", "status", "completed_at", "created_at", "updated_at"
    }
    actual_practice_item_fields = set(UserPracticeProgressItem.model_fields.keys())
    assert actual_practice_item_fields == expected_practice_item_fields
    assert "attempts_count" not in actual_practice_item_fields

    # RoadmapSkillItem has no P4 gap/priority fields
    skill_item_fields = set(RoadmapSkillItem.model_fields.keys())
    unsupported_p4_fields = {"gap_status", "priority_level", "priority_score", "demand_score"}
    assert unsupported_p4_fields.isdisjoint(skill_item_fields)

    # RoadmapSummary has no P4 gap counts
    summary_fields = set(RoadmapSummary.model_fields.keys())
    assert "high_priority_gap_count" not in summary_fields
    assert "medium_priority_gap_count" not in summary_fields


# -----------------------------------------------------------------------------
# 3. Catalog Tests
# -----------------------------------------------------------------------------

def test_get_roadmap_catalog_returns_all_12_domains(service, db_session):
    catalog = service.get_roadmap_catalog(db_session)
    assert len(catalog) == 12

    # Check that canonical tracks with market data appear first
    market_data_flags = [r.has_market_data for r in catalog]
    assert market_data_flags[:5] == [True, True, True, True, True]
    assert market_data_flags[5:] == [False, False, False, False, False, False, False]

    # Verify deterministic title sorting within groups
    canonical_titles = [r.title for r in catalog[:5]]
    assert canonical_titles == sorted(canonical_titles)


# -----------------------------------------------------------------------------
# 4. Roadmap Detail & Structure Tests
# -----------------------------------------------------------------------------

def test_get_roadmap_detail_by_slug_and_uuid(service, db_session):
    detail_by_slug = service.get_roadmap_detail(db_session, "backend-engineer")
    assert detail_by_slug.roadmap.slug == "backend-engineer"
    assert len(detail_by_slug.stages) == 6
    assert detail_by_slug.summary.total_skills == 18

    detail_by_uuid = service.get_roadmap_detail(db_session, detail_by_slug.roadmap.id)
    assert detail_by_uuid.roadmap.id == detail_by_slug.roadmap.id
    assert detail_by_uuid.roadmap.slug == "backend-engineer"


def test_get_roadmap_detail_stage_and_skill_ordering(service, db_session):
    detail = service.get_roadmap_detail(db_session, "backend-engineer")

    # Verify stages are strictly in ascending order
    stage_orders = [st.stage_order for st in detail.stages]
    assert stage_orders == sorted(stage_orders)

    # Verify skills within each stage are in ascending order
    for st in detail.stages:
        skill_orders = [sk.skill_order for sk in st.skills]
        assert skill_orders == sorted(skill_orders)
        for sk in st.skills:
            assert len(sk.resources) == 2
            assert len(sk.practice_problems) == 3


def test_get_roadmap_detail_not_found(service, db_session):
    with pytest.raises(RoadmapNotFoundError):
        service.get_roadmap_detail(db_session, "non-existent-roadmap")


# -----------------------------------------------------------------------------
# 5. Canonical Skill Mapping Tests
# -----------------------------------------------------------------------------

def test_canonical_skill_mapping(service, db_session):
    detail = service.get_roadmap_detail(db_session, "backend-engineer")
    python_skill = next(sk for st in detail.stages for sk in st.skills if sk.slug == "python")
    assert python_skill.canonical_skill_id is not None

    ios_detail = service.get_roadmap_detail(db_session, "ios-developer")
    swiftui_skill = next(sk for st in ios_detail.stages for sk in st.skills if sk.slug == "swiftui-development")
    assert swiftui_skill.canonical_skill_id is None


# -----------------------------------------------------------------------------
# 6. Curated Ordering Tests
# -----------------------------------------------------------------------------

def test_curated_ordering(service, db_session):
    detail = service.get_roadmap_detail(db_session, "full-stack-engineer", ordering="curated")
    assert detail.ordering == "curated"
    assert detail.recommended_skills is None

    flattened = []
    for st in detail.stages:
        for sk in st.skills:
            flattened.append((st.stage_order, sk.skill_order))
    for i in range(len(flattened) - 1):
        assert flattened[i] <= flattened[i + 1]


# -----------------------------------------------------------------------------
# 7. Recommended Ordering (Topological Sort) Tests
# -----------------------------------------------------------------------------

def test_recommended_ordering_prerequisite_invariance(service, db_session):
    """Every prerequisite must precede its dependent skill across all 12 roadmaps."""
    catalog = service.get_roadmap_catalog(db_session)
    for r_item in catalog:
        detail = service.get_roadmap_detail(db_session, r_item.slug, ordering="recommended")
        assert detail.ordering == "recommended"
        assert detail.recommended_skills is not None
        assert len(detail.recommended_skills) == detail.summary.total_skills

        rec_skills = detail.recommended_skills
        position_map = {sk.id: idx for idx, sk in enumerate(rec_skills)}

        for sk in rec_skills:
            for p in sk.prerequisites:
                assert position_map[p.skill_id] < position_map[sk.id], (
                    f"In roadmap {r_item.slug}, prerequisite {p.skill_slug} (pos {position_map[p.skill_id]}) "
                    f"does not precede dependent {sk.slug} (pos {position_map[sk.id]})"
                )


def test_recommended_ordering_is_deterministic(service, db_session):
    run1 = service.get_roadmap_detail(db_session, "backend-engineer", ordering="recommended")
    run2 = service.get_roadmap_detail(db_session, "backend-engineer", ordering="recommended")

    slugs1 = [s.slug for s in run1.recommended_skills]
    slugs2 = [s.slug for s in run2.recommended_skills]
    assert slugs1 == slugs2


def test_recommended_ordering_independent_of_user_or_skill_gaps(service, db_session, user_a, user_b):
    """
    Recommended ordering must be identical for identical DB state regardless of:
    - unauthenticated (user_id=None)
    - user A with learning/completed skills
    - user B with different skill progress
    """
    # Baseline: unauthenticated
    baseline = service.get_roadmap_detail(db_session, "backend-engineer", ordering="recommended", user_id=None)
    baseline_ids = [s.id for s in baseline.recommended_skills]

    # User A has progress on python and fastapi
    service.update_user_progress(db_session, user_a.id, "backend-engineer", "python", "DONE")
    service.update_user_progress(db_session, user_a.id, "backend-engineer", "fastapi", "LEARNING")

    user_a_detail = service.get_roadmap_detail(db_session, "backend-engineer", ordering="recommended", user_id=user_a.id)
    user_a_ids = [s.id for s in user_a_detail.recommended_skills]

    # User B has progress on docker
    service.update_user_progress(db_session, user_b.id, "backend-engineer", "docker", "DONE")

    user_b_detail = service.get_roadmap_detail(db_session, "backend-engineer", ordering="recommended", user_id=user_b.id)
    user_b_ids = [s.id for s in user_b_detail.recommended_skills]

    # Topological recommended ordering is strictly invariant
    assert baseline_ids == user_a_ids == user_b_ids


def test_recommended_ordering_detects_cycle(service, db_session):
    # Introduce an artificial cycle in prerequisites
    roadmap = db_session.query(Roadmap).filter(Roadmap.slug == "qa-automation-engineer").first()
    skills = db_session.query(RoadmapSkill).filter(RoadmapSkill.roadmap_id == roadmap.id).all()
    s1, s2 = skills[0], skills[1]

    # Create cycle: s1 -> s2 and s2 -> s1
    edge1 = RoadmapPrerequisite(roadmap_skill_id=s1.id, prerequisite_skill_id=s2.id)
    edge2 = RoadmapPrerequisite(roadmap_skill_id=s2.id, prerequisite_skill_id=s1.id)
    db_session.add_all([edge1, edge2])
    db_session.commit()

    with pytest.raises(PrerequisiteCycleError):
        service.get_roadmap_detail(db_session, "qa-automation-engineer", ordering="recommended")


# -----------------------------------------------------------------------------
# 8. Relationship Validation Tests
# -----------------------------------------------------------------------------

def test_relationship_validation_wrong_roadmap_and_skill(service, db_session):
    backend_roadmap = db_session.query(Roadmap).filter(Roadmap.slug == "backend-engineer").first()
    ios_roadmap = db_session.query(Roadmap).filter(Roadmap.slug == "ios-developer").first()
    ios_skill = db_session.query(RoadmapSkill).filter(RoadmapSkill.roadmap_id == ios_roadmap.id).first()

    with pytest.raises(RoadmapRelationshipError):
        service.get_roadmap_skill(db_session, backend_roadmap.id, ios_skill.id)


def test_relationship_validation_invalid_skill_id(service, db_session):
    backend_roadmap = db_session.query(Roadmap).filter(Roadmap.slug == "backend-engineer").first()
    with pytest.raises(RoadmapSkillNotFoundError):
        service.get_roadmap_skill(db_session, backend_roadmap.id, uuid.uuid4())


def test_relationship_validation_invalid_problem_id(service, db_session, user_a):
    with pytest.raises(PracticeProblemNotFoundError):
        service.update_user_practice_progress(
            db_session,
            user_id=user_a.id,
            roadmap_identifier="backend-engineer",
            skill_identifier="python",
            problem_id="completely-invalid-prob-999",
            status="COMPLETED",
        )


# -----------------------------------------------------------------------------
# 9. User Skill Progress Tests
# -----------------------------------------------------------------------------

def test_user_skill_progress_lifecycle(service, db_session, user_a):
    p1 = service.update_user_progress(
        db_session,
        user_id=user_a.id,
        roadmap_identifier="backend-engineer",
        skill_identifier="python",
        status="LEARNING",
    )
    assert p1.status == "LEARNING"
    assert p1.user_id == user_a.id
    assert p1.created_at is not None
    assert p1.updated_at is not None

    progress_map = service.get_user_roadmap_progress(db_session, user_a.id)
    assert progress_map[p1.roadmap_skill_id] == "LEARNING"

    detail = service.get_roadmap_detail(db_session, "backend-engineer", user_id=user_a.id)
    py_skill = next(sk for st in detail.stages for sk in st.skills if sk.slug == "python")
    assert py_skill.user_status == "LEARNING"
    assert detail.summary.learning_skills == 1

    # Idempotent update
    p2 = service.update_user_progress(
        db_session,
        user_id=user_a.id,
        roadmap_identifier="backend-engineer",
        skill_identifier="python",
        status="DONE",
    )
    assert p2.id == p1.id
    assert p2.status == "DONE"

    detail2 = service.get_roadmap_detail(db_session, "backend-engineer", user_id=user_a.id)
    py_skill2 = next(sk for st in detail2.stages for sk in st.skills if sk.slug == "python")
    assert py_skill2.user_status == "DONE"
    assert detail2.summary.completed_skills == 1


def test_user_skill_progress_supported_statuses(service, db_session, user_a):
    for status in ["NOT_STARTED", "LEARNING", "DONE", "SKIPPED"]:
        p = service.update_user_progress(db_session, user_a.id, "backend-engineer", "python", status)
        assert p.status == status

    with pytest.raises(InvalidProgressStatusError):
        service.update_user_progress(db_session, user_a.id, "backend-engineer", "python", "INVALID_STATUS")


# -----------------------------------------------------------------------------
# 10. User Practice Progress Tests
# -----------------------------------------------------------------------------

def test_user_practice_progress_lifecycle(service, db_session, user_a):
    # 1. Set to IN_PROGRESS
    p1 = service.update_user_practice_progress(
        db_session,
        user_id=user_a.id,
        roadmap_identifier="backend-engineer",
        skill_identifier="python",
        problem_id="python-prob-1",
        status="IN_PROGRESS",
    )
    assert p1.status == "IN_PROGRESS"
    assert p1.completed_at is None
    assert p1.created_at is not None
    assert p1.updated_at is not None

    # 2. Set to COMPLETED -> sets completed_at
    p2 = service.update_user_practice_progress(
        db_session,
        user_id=user_a.id,
        roadmap_identifier="backend-engineer",
        skill_identifier="python",
        problem_id="python-prob-1",
        status="COMPLETED",
    )
    assert p2.id == p1.id
    assert p2.status == "COMPLETED"
    assert p2.completed_at is not None

    # 3. Transition away from COMPLETED -> clears completed_at
    p3 = service.update_user_practice_progress(
        db_session,
        user_id=user_a.id,
        roadmap_identifier="backend-engineer",
        skill_identifier="python",
        problem_id="python-prob-1",
        status="IN_PROGRESS",
    )
    assert p3.id == p1.id
    assert p3.status == "IN_PROGRESS"
    assert p3.completed_at is None


def test_practice_progress_supports_only_intended_statuses(service, db_session, user_a):
    for valid_status in ["NOT_STARTED", "IN_PROGRESS", "COMPLETED"]:
        p = service.update_user_practice_progress(
            db_session, user_a.id, "backend-engineer", "python", "python-prob-1", valid_status
        )
        assert p.status == valid_status

    invalid_statuses = ["DONE", "SKIPPED", "REVIEW", "PENDING", "FAILED"]
    for inv in invalid_statuses:
        with pytest.raises(InvalidProgressStatusError):
            service.update_user_practice_progress(
                db_session, user_a.id, "backend-engineer", "python", "python-prob-1", inv
            )


def test_duplicate_practice_problem_ids_remain_scoped(service, db_session, user_a):
    # 'ts-prob-1' exists in both frontend (typescript) and data science (time-series-ds) under different skills
    fe_p = service.update_user_practice_progress(
        db_session,
        user_id=user_a.id,
        roadmap_identifier="frontend-engineer",
        skill_identifier="typescript",
        problem_id="ts-prob-1",
        status="COMPLETED",
    )
    assert fe_p.status == "COMPLETED"

    # User A's ts-prob-1 in Data Science time-series-ds should still be NOT_STARTED
    ds_skill = service.get_roadmap_skill(
        db_session,
        roadmap_identifier="data-scientist",
        skill_identifier="time-series-ds",
        user_id=user_a.id,
    )
    ds_prob1 = next(p for p in ds_skill.practice_problems if p.problem_id == "ts-prob-1")
    assert ds_prob1.user_status == "NOT_STARTED"


# -----------------------------------------------------------------------------
# 11. User Isolation Tests
# -----------------------------------------------------------------------------

def test_user_isolation(service, db_session, user_a, user_b):
    service.update_user_progress(
        db_session,
        user_id=user_a.id,
        roadmap_identifier="backend-engineer",
        skill_identifier="python",
        status="DONE",
    )
    service.update_user_practice_progress(
        db_session,
        user_id=user_a.id,
        roadmap_identifier="backend-engineer",
        skill_identifier="python",
        problem_id="python-prob-1",
        status="COMPLETED",
    )

    # User B views the same skill
    user_b_skill = service.get_roadmap_skill(
        db_session,
        roadmap_identifier="backend-engineer",
        skill_identifier="python",
        user_id=user_b.id,
    )
    assert user_b_skill.user_status == "NOT_STARTED"
    user_b_prob1 = next(p for p in user_b_skill.practice_problems if p.problem_id == "python-prob-1")
    assert user_b_prob1.user_status == "NOT_STARTED"

    # User B summary should show 0 completed
    user_b_summary = service.get_user_roadmap_summary(db_session, user_b.id, "backend-engineer")
    assert user_b_summary.completed_skills == 0
    assert user_b_summary.completed_practice_problems == 0


# -----------------------------------------------------------------------------
# 12. Roadmap Progress Summary Tests
# -----------------------------------------------------------------------------

def test_get_user_roadmap_summary(service, db_session, user_a):
    service.update_user_progress(db_session, user_a.id, "backend-engineer", "python", "DONE")
    service.update_user_progress(db_session, user_a.id, "backend-engineer", "fastapi", "LEARNING")
    service.update_user_practice_progress(db_session, user_a.id, "backend-engineer", "python", "python-prob-1", "COMPLETED")

    summary = service.get_user_roadmap_summary(db_session, user_a.id, "backend-engineer")
    assert summary.total_skills == 18
    assert summary.completed_skills == 1
    assert summary.learning_skills == 1
    assert summary.completed_practice_problems == 1
    assert summary.total_practice_problems == 54
    assert summary.progress_percentage == round((1 / 18) * 100, 1)
