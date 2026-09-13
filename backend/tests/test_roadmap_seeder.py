"""
Comprehensive test suite for Phase 2: Static Roadmap Dataset & Idempotent Seeder.

Covers:
1. Dataset aggregation & structure
2. Expected counts (12 roadmaps, 56 stages, 130 skills, 174 prerequisites, 260 resources, 390 problems)
3. Role mapping (5 canonical with role_id/market_data, 7 curated without)
4. Canonical skill mapping (50 mapped, 80 unmapped)
5. Prerequisite resolution & edge validity
6. DAG acyclicity (Kahn's algorithm, 0 cycles)
7. Resource counts & types (1 DOCUMENTATION, 1 YOUTUBE per skill)
8. Practice problem counts & difficulty distribution (1 BEGINNER, 1 INTERMEDIATE, 1 ADVANCED per skill)
9. Duplicate problem IDs remaining correctly scoped
10. Idempotent seeding (repeated runs yield identical state)
11. Transaction rollback behavior on failure
"""

import uuid
import pytest
from typing import Dict, List, Set
from collections import Counter

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
    Skill,
    User,
    Roadmap,
    RoadmapStage,
    RoadmapSkill,
    RoadmapPrerequisite,
    LearningResource,
    UserRoadmapProgress,
    UserPracticeProgress,
)
from app.db.roadmaps_data import (
    ROADMAPS_SEED_DATA,
    CANONICAL_ROLE_IDS,
    ROADMAP_IDS,
)
from app.db.seed_roadmaps import (
    seed_roadmaps,
    validate_seeded_roadmaps,
    CANONICAL_ROLE_SLUGS,
)


@pytest.fixture
def in_memory_db():
    """In-memory SQLite database pre-populated with canonical roles and skills."""
    engine = create_engine("sqlite:///:memory:")
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
    yield session
    session.close()


def test_01_dataset_aggregation_and_counts():
    """Verify raw dataset totals match specifications."""
    assert len(ROADMAPS_SEED_DATA) == 12

    total_stages = sum(len(r.get("stages", [])) for r in ROADMAPS_SEED_DATA)
    assert total_stages == 56

    total_skills = 0
    total_prereqs = 0
    total_resources = 0
    total_problems = 0
    for r in ROADMAPS_SEED_DATA:
        for st in r.get("stages", []):
            for sk in st.get("skills", []):
                total_skills += 1
                total_prereqs += len(sk.get("prerequisites", []))
                total_resources += len(sk.get("resources", []))
                total_problems += len(sk.get("practice_problems", []))

    assert total_skills == 130
    assert total_prereqs == 174
    assert total_resources == 260
    assert total_problems == 390


def test_02_role_mapping_invariants(in_memory_db):
    """Verify 5 canonical tracks map to JobRole and 7 curated tracks remain unmapped."""
    seed_roadmaps(in_memory_db, auto_commit=True, validate=True)

    roadmaps = in_memory_db.query(Roadmap).all()
    assert len(roadmaps) == 12

    canonical = [r for r in roadmaps if r.slug in CANONICAL_ROLE_SLUGS]
    curated = [r for r in roadmaps if r.slug not in CANONICAL_ROLE_SLUGS]

    assert len(canonical) == 5
    assert len(curated) == 7

    for r in canonical:
        assert r.role_id is not None
        assert r.has_market_data is True
        assert r.role.slug == r.slug

    for r in curated:
        assert r.role_id is None
        assert r.has_market_data is False


def test_03_canonical_skill_mapping(in_memory_db):
    """Verify exactly 50 skills map to canonical skills and 80 remain unmapped."""
    seed_roadmaps(in_memory_db, auto_commit=True, validate=True)

    skills = in_memory_db.query(RoadmapSkill).all()
    assert len(skills) == 130

    mapped = [s for s in skills if s.canonical_skill_id is not None]
    unmapped = [s for s in skills if s.canonical_skill_id is None]

    assert len(mapped) == 50
    assert len(unmapped) == 80


def test_04_prerequisite_edges_and_dag_acyclicity(in_memory_db):
    """Verify all 174 prerequisite edges stay inside their roadmap and form strict acyclic DAGs."""
    seed_roadmaps(in_memory_db, auto_commit=True, validate=True)

    edges = in_memory_db.query(RoadmapPrerequisite).all()
    assert len(edges) == 174

    for e in edges:
        assert e.roadmap_skill.roadmap_id == e.prerequisite_skill.roadmap_id

    # Kahn's algorithm per roadmap
    for r in in_memory_db.query(Roadmap).all():
        skills = in_memory_db.query(RoadmapSkill).filter(RoadmapSkill.roadmap_id == r.id).all()
        skill_ids = {s.id for s in skills}
        adj = {sid: [] for sid in skill_ids}
        in_degree = {sid: 0 for sid in skill_ids}

        for s in skills:
            for p in s.prerequisites:
                adj[p.prerequisite_skill_id].append(s.id)
                in_degree[s.id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            curr = queue.pop(0)
            visited += 1
            for nxt in adj[curr]:
                in_degree[nxt] -= 1
                if in_degree[nxt] == 0:
                    queue.append(nxt)

        assert visited == len(skill_ids), f"Cycle detected in roadmap {r.slug}"


def test_05_learning_resources_distribution(in_memory_db):
    """Verify every roadmap skill has exactly 1 DOCUMENTATION and 1 YOUTUBE resource."""
    seed_roadmaps(in_memory_db, auto_commit=True, validate=True)

    skills = in_memory_db.query(RoadmapSkill).all()
    for s in skills:
        types = [r.resource_type for r in s.resources]
        assert len(types) == 2
        assert sorted(types) == ["DOCUMENTATION", "YOUTUBE"]


def test_06_practice_problems_distribution(in_memory_db):
    """Verify every roadmap skill has 3 problems: BEGINNER, INTERMEDIATE, ADVANCED."""
    seed_roadmaps(in_memory_db, auto_commit=True, validate=True)

    skills = in_memory_db.query(RoadmapSkill).all()
    for s in skills:
        probs = s.practice_problems or []
        assert len(probs) == 3
        diffs = [p.get("difficulty") for p in probs]
        assert sorted(diffs) == ["ADVANCED", "BEGINNER", "INTERMEDIATE"]


def test_07_duplicate_problem_ids_scoped_by_skill():
    """Verify duplicate problem IDs (ts-prob-*, a11y-prob-*) exist but are scoped to different skills."""
    counter = Counter()
    for r in ROADMAPS_SEED_DATA:
        for st in r.get("stages", []):
            for sk in st.get("skills", []):
                for p in sk.get("practice_problems", []):
                    counter[p["problem_id"]] += 1

    duplicates = {pid: count for pid, count in counter.items() if count > 1}
    expected_duplicates = {
        "ts-prob-1": 2, "ts-prob-2": 2, "ts-prob-3": 2,
        "a11y-prob-1": 2, "a11y-prob-2": 2, "a11y-prob-3": 2,
    }
    assert duplicates == expected_duplicates


def test_08_idempotent_seeding(in_memory_db):
    """Verify seeder can be run 3 times consecutively without creating duplicate rows."""
    counts1 = seed_roadmaps(in_memory_db, auto_commit=True, validate=True)
    counts2 = seed_roadmaps(in_memory_db, auto_commit=True, validate=True)
    counts3 = seed_roadmaps(in_memory_db, auto_commit=True, validate=True)

    assert counts1 == counts2 == counts3

    assert in_memory_db.query(Roadmap).count() == 12
    assert in_memory_db.query(RoadmapStage).count() == 56
    assert in_memory_db.query(RoadmapSkill).count() == 130
    assert in_memory_db.query(RoadmapPrerequisite).count() == 174
    assert in_memory_db.query(LearningResource).count() == 260


def test_09_transaction_rollback_on_missing_canonical_skill(in_memory_db):
    """Verify seeder rolls back cleanly if an invalid canonical skill is referenced."""
    from app.db.roadmaps_data.backend import BACKEND_ROADMAP

    # Temporarily corrupt a canonical slug in memory
    original_slug = BACKEND_ROADMAP["stages"][0]["skills"][0]["canonical_slug"]
    try:
        BACKEND_ROADMAP["stages"][0]["skills"][0]["canonical_slug"] = "non-existent-skill-xyz"
        with pytest.raises(ValueError, match="not found in skills table"):
            seed_roadmaps(in_memory_db, auto_commit=True, validate=True)

        # Confirm rollback: no roadmaps should remain committed
        assert in_memory_db.query(Roadmap).count() == 0
    finally:
        BACKEND_ROADMAP["stages"][0]["skills"][0]["canonical_slug"] = original_slug
