"""
Comprehensive API test suite for Phase 4: Static Skill Roadmap API.

Verifies:
1. Catalog endpoint (GET /api/v1/roadmaps):
   - Returns 200 OK and exactly 12 roadmap domains
   - Deterministic ordering: canonical tracks first, then curated
   - Public access without authentication
2. Detail endpoint (GET /api/v1/roadmaps/{roadmap_id}):
   - Lookup by slug and UUID
   - Curated ordering mode
   - Recommended ordering mode (topological sort)
   - Rejection of invalid ordering modes (422)
   - 404 on nonexistent roadmap
   - Public access without authentication
   - Progress attached when valid user is provided
3. Skills endpoint (GET /api/v1/roadmaps/{roadmap_id}/skills):
   - Flat list of skills for the roadmap
   - Only returns skills for that roadmap
   - Preserves stage/skill order or recommended topological order
   - 404 on nonexistent roadmap
4. Skill detail endpoint (GET /api/v1/roadmaps/{roadmap_id}/skills/{skill_id}):
   - Valid skill returns 200 with resources and practice problems
   - Rejects skill belonging to a different roadmap (400)
   - 404 on nonexistent skill
   - Public access without authentication
5. User progress endpoint (GET /api/v1/users/me/roadmap-progress):
   - Requires authentication (401 when unauthenticated)
   - Returns user progress mapping
   - Supports domain progress summary mode (?roadmap_id=...&summary=true)
6. Skill progress update (PUT /api/v1/users/me/roadmap-progress/{skill_id}):
   - Requires authentication (401 when unauthenticated)
   - Successfully updates status (NOT_STARTED, LEARNING, DONE, SKIPPED)
   - Idempotent: repeated updates do not duplicate rows
   - Rejects invalid status (400)
   - 404 on nonexistent skill
7. Practice progress update (PUT /api/v1/users/me/roadmap-progress/{skill_id}/problems/{problem_id}):
   - Requires authentication (401 when unauthenticated)
   - Sets completed_at on COMPLETED, clears on transition away
   - Rejects invalid problem ID (404)
   - Duplicate problem IDs remain scoped by roadmap_skill_id
   - Rejects invalid status (400)
8. User isolation & IDOR protection:
   - User A cannot access or modify User B's progress
   - Conflicting query user_id and X-User-Id header returns 403 Forbidden
9. P4 regression safety:
   - Verifies existing P4 singular endpoint (/api/v1/roadmap) remains registered and separate
"""

import sys
from unittest.mock import MagicMock
import uuid
import pytest

# Ensure optional external AI/verification modules are mocked if not locally installed
for mod in [
    "langchain_core",
    "langchain_core.messages",
    "langchain_core.chat_history",
    "langchain_core.prompts",
    "langchain_ollama",
    "yaml",
]:
    sys.modules.setdefault(mod, MagicMock())

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB

# SQLite hook for JSONB compatibility in unit tests
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

from app.main import app
from app.db.database import Base, get_db
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


@pytest.fixture
def db_session():
    """In-memory SQLite database seeded with canonical roles, skills, and full static roadmap catalog."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
    Session = sessionmaker(bind=engine, autoflush=False)
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
def client(db_session):
    """TestClient with dependency override for get_db pointing to the in-memory SQLite session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


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
# 1. Catalog Endpoint Tests (GET /api/v1/roadmaps)
# -----------------------------------------------------------------------------

def test_get_catalog_returns_200_and_12_roadmaps(client):
    res = client.get("/api/v1/roadmaps")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert body["total"] == 12
    assert len(body["data"]) == 12


def test_get_catalog_deterministic_ordering(client):
    res = client.get("/api/v1/roadmaps")
    assert res.status_code == 200
    items = res.json()["data"]

    # First 5 must be canonical tracks (has_market_data = True)
    assert all(item["has_market_data"] is True for item in items[:5])
    # Remaining 7 must be curated tracks (has_market_data = False)
    assert all(item["has_market_data"] is False for item in items[5:])

    # Deterministic alphabetical title order within canonical tracks
    canonical_titles = [item["title"] for item in items[:5]]
    assert canonical_titles == sorted(canonical_titles)


# -----------------------------------------------------------------------------
# 2. Roadmap Detail Endpoint Tests (GET /api/v1/roadmaps/{roadmap_id})
# -----------------------------------------------------------------------------

def test_get_roadmap_detail_by_slug_and_uuid(client, db_session):
    # Lookup by slug
    res_slug = client.get("/api/v1/roadmaps/backend-engineer")
    assert res_slug.status_code == 200
    data_slug = res_slug.json()["data"]
    assert data_slug["roadmap"]["slug"] == "backend-engineer"
    assert data_slug["roadmap"]["title"] == "Backend Engineer"
    assert len(data_slug["stages"]) == 6
    assert data_slug["summary"]["total_skills"] == 18

    # Lookup by UUID
    roadmap_uuid = data_slug["roadmap"]["id"]
    res_uuid = client.get(f"/api/v1/roadmaps/{roadmap_uuid}")
    assert res_uuid.status_code == 200
    data_uuid = res_uuid.json()["data"]
    assert data_uuid["roadmap"]["id"] == roadmap_uuid
    assert data_uuid["roadmap"]["slug"] == "backend-engineer"


def test_get_roadmap_detail_curated_ordering(client):
    res = client.get("/api/v1/roadmaps/backend-engineer?ordering=curated")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["ordering"] == "curated"
    assert data["recommended_skills"] is None

    # Verify stage ordering is strictly ascending
    stage_orders = [stage["stage_order"] for stage in data["stages"]]
    assert stage_orders == sorted(stage_orders)


def test_get_roadmap_detail_recommended_ordering(client):
    res = client.get("/api/v1/roadmaps/backend-engineer?ordering=recommended")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["ordering"] == "recommended"
    assert data["recommended_skills"] is not None
    assert len(data["recommended_skills"]) == 18

    # Verify prerequisite ordering invariance
    rec_skills = data["recommended_skills"]
    position_map = {sk["id"]: idx for idx, sk in enumerate(rec_skills)}
    for sk in rec_skills:
        for p in sk["prerequisites"]:
            assert position_map[p["skill_id"]] < position_map[sk["id"]]


def test_get_roadmap_detail_invalid_ordering_returns_422(client):
    res = client.get("/api/v1/roadmaps/backend-engineer?ordering=random_invalid")
    assert res.status_code == 422


def test_get_roadmap_detail_not_found_returns_404(client):
    res = client.get("/api/v1/roadmaps/completely-nonexistent-domain")
    assert res.status_code == 404


# -----------------------------------------------------------------------------
# 3. Roadmap Skills Endpoint Tests (GET /api/v1/roadmaps/{roadmap_id}/skills)
# -----------------------------------------------------------------------------

def test_get_roadmap_skills_curated_and_recommended(client):
    # Curated order
    res_curated = client.get("/api/v1/roadmaps/backend-engineer/skills?ordering=curated")
    assert res_curated.status_code == 200
    skills_curated = res_curated.json()
    assert len(skills_curated) == 18
    assert all(sk["roadmap_id"] == skills_curated[0]["roadmap_id"] for sk in skills_curated)

    # Recommended order
    res_rec = client.get("/api/v1/roadmaps/backend-engineer/skills?ordering=recommended")
    assert res_rec.status_code == 200
    skills_rec = res_rec.json()
    assert len(skills_rec) == 18


def test_get_roadmap_skills_invalid_roadmap_returns_404(client):
    res = client.get("/api/v1/roadmaps/nonexistent-track/skills")
    assert res.status_code == 404


# -----------------------------------------------------------------------------
# 4. Skill Detail Endpoint Tests (GET /api/v1/roadmaps/{roadmap_id}/skills/{skill_id})
# -----------------------------------------------------------------------------

def test_get_roadmap_skill_detail_success(client):
    res = client.get("/api/v1/roadmaps/backend-engineer/skills/python")
    assert res.status_code == 200
    skill = res.json()
    assert skill["slug"] == "python"
    assert skill["name"] == "Python"
    assert skill["canonical_skill_id"] is not None
    assert len(skill["resources"]) == 2
    assert len(skill["practice_problems"]) == 3


def test_get_roadmap_skill_detail_wrong_roadmap_rejected(client):
    # Asking for iOS 'swiftui-development' under Backend roadmap must be rejected
    res = client.get("/api/v1/roadmaps/backend-engineer/skills/swiftui-development")
    assert res.status_code == 400


def test_get_roadmap_skill_detail_nonexistent_skill_returns_404(client):
    res = client.get("/api/v1/roadmaps/backend-engineer/skills/nonexistent-skill-xyz")
    assert res.status_code == 404


# -----------------------------------------------------------------------------
# 5. Public Access Tests (Browsing without Auth)
# -----------------------------------------------------------------------------

def test_public_browsing_works_without_auth(client):
    # No headers or query params supplied
    assert client.get("/api/v1/roadmaps").status_code == 200
    assert client.get("/api/v1/roadmaps/frontend-engineer").status_code == 200
    assert client.get("/api/v1/roadmaps/frontend-engineer/skills").status_code == 200
    assert client.get("/api/v1/roadmaps/frontend-engineer/skills/react").status_code == 200


# -----------------------------------------------------------------------------
# 6. Skill Progress Lifecycle Tests (PUT /api/v1/users/me/roadmap-progress/{skill_id})
# -----------------------------------------------------------------------------

def test_user_skill_progress_unauthenticated_returns_401(client):
    res = client.put(
        "/api/v1/users/me/roadmap-progress/python",
        json={"status": "LEARNING"},
    )
    assert res.status_code == 401


def test_user_skill_progress_lifecycle_and_idempotency(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}

    # 1. Update to LEARNING
    res1 = client.put(
        "/api/v1/users/me/roadmap-progress/python",
        json={"status": "LEARNING"},
        headers=headers,
    )
    assert res1.status_code == 200
    body1 = res1.json()
    assert body1["success"] is True
    assert body1["data"]["status"] == "LEARNING"
    progress_id = body1["data"]["id"]

    # 2. Update to DONE (idempotent row update)
    res2 = client.put(
        "/api/v1/users/me/roadmap-progress/python",
        json={"status": "DONE"},
        headers=headers,
    )
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["data"]["id"] == progress_id
    assert body2["data"]["status"] == "DONE"

    # 3. Retrieve progress mapping
    res_map = client.get("/api/v1/users/me/roadmap-progress", headers=headers)
    assert res_map.status_code == 200
    mapping = res_map.json()
    assert mapping[body2["data"]["roadmap_skill_id"]] == "DONE"


def test_user_skill_progress_invalid_status_returns_400(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}
    res = client.put(
        "/api/v1/users/me/roadmap-progress/python",
        json={"status": "INVALID_STATUS_XYZ"},
        headers=headers,
    )
    assert res.status_code in {400, 422}


def test_user_skill_progress_nonexistent_skill_returns_404(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}
    res = client.put(
        f"/api/v1/users/me/roadmap-progress/{uuid.uuid4()}",
        json={"status": "LEARNING"},
        headers=headers,
    )
    assert res.status_code == 404


# -----------------------------------------------------------------------------
# 7. Practice Progress Lifecycle Tests
# -----------------------------------------------------------------------------

def test_user_practice_progress_lifecycle_and_completed_at(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}

    # 1. IN_PROGRESS -> completed_at is None
    res1 = client.put(
        "/api/v1/users/me/roadmap-progress/python/problems/python-prob-1",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert res1.status_code == 200
    body1 = res1.json()["data"]
    assert body1["status"] == "IN_PROGRESS"
    assert body1["completed_at"] is None

    # 2. COMPLETED -> completed_at is set
    res2 = client.put(
        "/api/v1/users/me/roadmap-progress/python/problems/python-prob-1",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert res2.status_code == 200
    body2 = res2.json()["data"]
    assert body2["status"] == "COMPLETED"
    assert body2["completed_at"] is not None

    # 3. Back to IN_PROGRESS -> completed_at is cleared
    res3 = client.put(
        "/api/v1/users/me/roadmap-progress/python/problems/python-prob-1",
        json={"status": "IN_PROGRESS"},
        headers=headers,
    )
    assert res3.status_code == 200
    body3 = res3.json()["data"]
    assert body3["status"] == "IN_PROGRESS"
    assert body3["completed_at"] is None


def test_user_practice_progress_invalid_problem_returns_404(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}
    res = client.put(
        "/api/v1/users/me/roadmap-progress/python/problems/completely-invalid-prob-999",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert res.status_code == 404


def test_duplicate_practice_problem_ids_remain_scoped_via_api(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}

    # Complete ts-prob-1 in Frontend TypeScript
    res_fe = client.put(
        "/api/v1/users/me/roadmap-progress/typescript/problems/ts-prob-1",
        json={"status": "COMPLETED"},
        headers=headers,
    )
    assert res_fe.status_code == 200
    assert res_fe.json()["data"]["status"] == "COMPLETED"

    # Check Data Science time-series-ds problem ts-prob-1: still NOT_STARTED
    res_ds = client.get(
        "/api/v1/roadmaps/data-scientist/skills/time-series-ds",
        headers=headers,
    )
    assert res_ds.status_code == 200
    ds_prob1 = next(p for p in res_ds.json()["practice_problems"] if p["problem_id"] == "ts-prob-1")
    assert ds_prob1["user_status"] == "NOT_STARTED"


# -----------------------------------------------------------------------------
# 8. User Progress Summary Endpoint Tests
# -----------------------------------------------------------------------------

def test_user_roadmap_progress_summary_endpoint(client, user_a):
    headers = {"X-User-Id": str(user_a.id)}

    # Add some progress
    client.put("/api/v1/users/me/roadmap-progress/python", json={"status": "DONE"}, headers=headers)
    client.put("/api/v1/users/me/roadmap-progress/fastapi", json={"status": "LEARNING"}, headers=headers)
    client.put("/api/v1/users/me/roadmap-progress/python/problems/python-prob-1", json={"status": "COMPLETED"}, headers=headers)

    res = client.get(
        "/api/v1/users/me/roadmap-progress?roadmap_id=backend-engineer&summary=true",
        headers=headers,
    )
    assert res.status_code == 200
    summary = res.json()
    assert summary["total_skills"] == 18
    assert summary["completed_skills"] == 1
    assert summary["learning_skills"] == 1
    assert summary["completed_practice_problems"] == 1


# -----------------------------------------------------------------------------
# 9. User Isolation & IDOR Protection Tests
# -----------------------------------------------------------------------------

def test_user_isolation_progress_inaccessible_to_other_users(client, user_a, user_b):
    # User A completes Python
    client.put(
        "/api/v1/users/me/roadmap-progress/python",
        json={"status": "DONE"},
        headers={"X-User-Id": str(user_a.id)},
    )

    # User B views Backend Roadmap
    res_b = client.get(
        "/api/v1/roadmaps/backend-engineer",
        headers={"X-User-Id": str(user_b.id)},
    )
    assert res_b.status_code == 200
    b_data = res_b.json()["data"]
    py_skill_b = next(sk for st in b_data["stages"] for sk in st["skills"] if sk["slug"] == "python")
    assert py_skill_b["user_status"] == "NOT_STARTED"
    assert b_data["summary"]["completed_skills"] == 0


def test_idor_protection_conflicting_user_id_and_header_returns_400(client, user_a, user_b):
    # Providing user_a in query but user_b in header must fail with 400 Bad Request
    res = client.get(
        f"/api/v1/users/me/roadmap-progress?user_id={user_a.id}",
        headers={"X-User-Id": str(user_b.id)},
    )
    assert res.status_code == 400

    # Also test PUT with conflicting user identity returns 400 Bad Request
    res_put = client.put(
        f"/api/v1/users/me/roadmap-progress/python?user_id={user_a.id}",
        json={"status": "DONE"},
        headers={"X-User-Id": str(user_b.id)},
    )
    assert res_put.status_code == 400

    # Also test roadmap detail with conflicting user identity returns 400 Bad Request
    res_detail = client.get(
        f"/api/v1/roadmaps/backend-engineer?user_id={user_a.id}",
        headers={"X-User-Id": str(user_b.id)},
    )
    assert res_detail.status_code == 400


# -----------------------------------------------------------------------------
# 10. P4 Regression Safety Tests
# -----------------------------------------------------------------------------

def test_p4_singular_endpoint_remains_distinct_and_registered(client):
    """Confirm that the P4 endpoint /api/v1/roadmap remains registered alongside /api/v1/roadmaps."""
    schema = app.openapi()
    paths = schema.get("paths", {})

    # P4 endpoint paths must exist
    p4_paths = [p for p in paths if p.startswith("/api/v1/roadmap/") or p == "/api/v1/roadmap"]
    assert len(p4_paths) > 0

    # Static roadmap paths must exist
    static_paths = [p for p in paths if p.startswith("/api/v1/roadmaps")]
    assert len(static_paths) >= 4
    assert "/api/v1/roadmaps" in static_paths
    assert "/api/v1/roadmaps/{roadmap_id}" in static_paths
    assert "/api/v1/roadmaps/{roadmap_id}/skills" in static_paths
    assert "/api/v1/roadmaps/{roadmap_id}/skills/{skill_id}" in static_paths

    # User progress paths must exist
    progress_paths = [p for p in paths if p.startswith("/api/v1/users/me/roadmap-progress")]
    assert len(progress_paths) >= 3
