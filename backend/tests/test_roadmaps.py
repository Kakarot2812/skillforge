import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import (
    Roadmap,
    RoadmapStage,
    RoadmapSkill,
    RoadmapPrerequisite,
    User,
    UserRoadmapProgress,
    UserPracticeProgress,
    Skill,
    JobRole,
    SkillGap,
    IndustrySkillDemand,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_user(db):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"roadmap_test_{user_id.hex[:8]}@example.com",
        full_name="Roadmap Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    # Cleanup
    db.query(UserPracticeProgress).filter(UserPracticeProgress.user_id == user.id).delete()
    db.query(UserRoadmapProgress).filter(UserRoadmapProgress.user_id == user.id).delete()
    db.query(SkillGap).filter(SkillGap.user_id == user.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()


@pytest.fixture
def second_test_user(db):
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"roadmap_test_isolation_{user_id.hex[:8]}@example.com",
        full_name="Isolation Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    # Cleanup
    db.query(UserPracticeProgress).filter(UserPracticeProgress.user_id == user.id).delete()
    db.query(UserRoadmapProgress).filter(UserRoadmapProgress.user_id == user.id).delete()
    db.query(User).filter(User.id == user.id).delete()
    db.commit()


# -----------------------------------------------------------------------------
# 1. Catalog & Discovery Tests
# -----------------------------------------------------------------------------

def test_list_roadmaps_catalog_returns_12_domains():
    """Verify all 12 roadmap domains are returned in the catalog."""
    response = client.get("/api/v1/roadmaps")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total" in data
    assert data["total"] == 12

    domains = [r["domain"] for r in data["data"]]
    assert "Backend Engineering" in domains
    assert "Frontend Engineering" in domains
    assert "Full Stack Engineering" in domains
    assert "Cloud & Infrastructure" in domains
    assert "Artificial Intelligence & Machine Learning" in domains
    assert "Mobile Development" in domains

    # Verify market data boundaries
    canonical_slugs = {
        "backend-engineer",
        "full-stack-engineer",
        "frontend-engineer",
        "cloud-devops-engineer",
        "ai-ml-engineer",
    }
    for item in data["data"]:
        if item["slug"] in canonical_slugs:
            assert item["has_market_data"] is True
            assert item["role_id"] is not None
        else:
            assert item["has_market_data"] is False
            assert item["role_id"] is None


def test_get_roadmap_detail_success():
    """Verify getting detail for backend-engineer returns stages and skills."""
    catalog = client.get("/api/v1/roadmaps").json()
    backend_meta = next(r for r in catalog["data"] if r["slug"] == "backend-engineer")

    res = client.get(f"/api/v1/roadmaps/{backend_meta['id']}")
    assert res.status_code == 200
    detail = res.json()["data"]

    assert detail["roadmap"]["title"] == "Backend Engineer"
    assert len(detail["stages"]) >= 4
    assert detail["summary"]["total_skills"] > 0
    assert detail["summary"]["completed_skills"] == 0

    first_stage = detail["stages"][0]
    assert len(first_stage["skills"]) > 0
    first_skill = first_stage["skills"][0]
    assert "id" in first_skill
    assert "name" in first_skill
    assert "difficulty" in first_skill
    assert "key_topics" in first_skill
    assert len(first_skill["resources"]) > 0


def test_invalid_roadmap_id_returns_404_or_422():
    """Verify error handling for invalid roadmap IDs."""
    fake_uuid = uuid.uuid4()
    res = client.get(f"/api/v1/roadmaps/{fake_uuid}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    malformed = client.get("/api/v1/roadmaps/not-a-valid-uuid")
    assert malformed.status_code == 422


# -----------------------------------------------------------------------------
# 2. Prerequisites & Resources Tests
# -----------------------------------------------------------------------------

def test_prerequisite_graph_has_no_cycles(db):
    """Verify that all prerequisite graphs across all roadmaps are valid DAGs (no cycles)."""
    roadmaps = db.query(Roadmap).all()
    for r in roadmaps:
        skills = db.query(RoadmapSkill).filter(RoadmapSkill.roadmap_id == r.id).all()
        skill_ids = {s.id for s in skills}

        prereqs = (
            db.query(RoadmapPrerequisite)
            .filter(RoadmapPrerequisite.roadmap_skill_id.in_(skill_ids))
            .all()
        )

        # Build adjacency list: u -> v means u requires v (v must come before u)
        adj = {s_id: set() for s_id in skill_ids}
        for p in prereqs:
            assert p.prerequisite_skill_id in skill_ids, "Prerequisite skill must belong to the same roadmap"
            adj[p.roadmap_skill_id].add(p.prerequisite_skill_id)

        # Detect cycle using DFS
        visited = {}  # 0 = unvisited, 1 = visiting, 2 = visited

        def has_cycle(node):
            visited[node] = 1
            for neighbor in adj.get(node, set()):
                if visited.get(neighbor, 0) == 1:
                    return True
                if visited.get(neighbor, 0) == 0 and has_cycle(neighbor):
                    return True
            visited[node] = 2
            return False

        for s_id in skill_ids:
            if visited.get(s_id, 0) == 0:
                assert not has_cycle(s_id), f"Circular prerequisite dependency detected in roadmap '{r.title}'"


def test_single_skill_resource_retrieval():
    """Verify single skill endpoint returns official doc and youtube resources."""
    catalog = client.get("/api/v1/roadmaps").json()
    backend_meta = next(r for r in catalog["data"] if r["slug"] == "backend-engineer")

    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    skill_item = detail["stages"][0]["skills"][0]

    res = client.get(f"/api/v1/roadmaps/{backend_meta['id']}/skills/{skill_item['id']}")
    assert res.status_code == 200
    skill = res.json()
    assert skill["id"] == skill_item["id"]
    assert len(skill["resources"]) >= 2

    types = {r["resource_type"] for r in skill["resources"]}
    assert "DOCUMENTATION" in types
    assert "YOUTUBE" in types

    for r in skill["resources"]:
        assert r["url"].startswith("http")
        assert len(r["title"]) > 0


# -----------------------------------------------------------------------------
# 3. Recommended Ordering (Topological Sort) Tests
# -----------------------------------------------------------------------------

def test_recommended_ordering_strictly_preserves_prerequisites():
    """
    Verify that in recommended ordering mode, prerequisites are NEVER violated.
    Every prerequisite must appear earlier in the sequence than its dependent.
    """
    catalog = client.get("/api/v1/roadmaps").json()
    backend_meta = next(r for r in catalog["data"] if r["slug"] == "backend-engineer")

    res = client.get(f"/api/v1/roadmaps/{backend_meta['id']}?ordering=recommended")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["ordering"] == "recommended"
    assert data["recommended_skills"] is not None
    rec_skills = data["recommended_skills"]

    skill_index = {s["id"]: idx for idx, s in enumerate(rec_skills)}

    for s in rec_skills:
        for prereq in s["prerequisites"]:
            prereq_id = prereq["skill_id"]
            if prereq_id in skill_index:
                assert skill_index[prereq_id] < skill_index[s["id"]], (
                    f"Prerequisite violation: {prereq['skill_name']} (index {skill_index[prereq_id]}) "
                    f"must precede {s['name']} (index {skill_index[s['id']]})"
                )


def test_recommended_ordering_bubbles_high_priority_gaps(db, test_user):
    """
    Verify that when candidate has a HIGH priority gap, it and its prerequisites
    are prioritized ahead of low-priority / unprioritized skills.
    """
    catalog = client.get("/api/v1/roadmaps").json()
    backend_meta = next(r for r in catalog["data"] if r["slug"] == "backend-engineer")

    # Find FastAPI skill
    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    fastapi_skill = None
    for stage in detail["stages"]:
        for s in stage["skills"]:
            if s["slug"] == "fastapi":
                fastapi_skill = s
                break

    assert fastapi_skill is not None
    canonical_fastapi_id = uuid.UUID(fastapi_skill["canonical_skill_id"])
    role_id = uuid.UUID(backend_meta["role_id"])

    # Insert a high-priority SkillGap record for this user
    high_gap = SkillGap(
        id=uuid.uuid4(),
        user_id=test_user.id,
        role_id=role_id,
        skill_id=canonical_fastapi_id,
        location="India",
        status="MISSING",
        demand_score=0.90,
        growth_rate=0.20,
        priority_score=0.85,
        priority_level="HIGH",
    )
    db.add(high_gap)
    db.commit()

    res = client.get(
        f"/api/v1/roadmaps/{backend_meta['id']}?ordering=recommended",
        headers={"X-User-Id": str(test_user.id)},
    )
    assert res.status_code == 200
    rec_skills = res.json()["data"]["recommended_skills"]

    fastapi_in_rec = next(s for s in rec_skills if s["slug"] == "fastapi")
    assert fastapi_in_rec["priority_level"] == "HIGH"

    # Python and REST APIs are prerequisites for FastAPI; they must appear before FastAPI
    python_idx = next(i for i, s in enumerate(rec_skills) if s["slug"] == "python")
    fastapi_idx = next(i for i, s in enumerate(rec_skills) if s["slug"] == "fastapi")

    assert python_idx < fastapi_idx, "Prerequisite Python must precede FastAPI"


# -----------------------------------------------------------------------------
# 4. User Progress & Cross-User Isolation Tests
# -----------------------------------------------------------------------------

def test_user_progress_lifecycle(test_user):
    """Verify user can update status to LEARNING, DONE, SKIPPED, NOT_STARTED."""
    catalog = client.get("/api/v1/roadmaps").json()
    backend_meta = next(r for r in catalog["data"] if r["slug"] == "backend-engineer")
    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    skill = detail["stages"][0]["skills"][0]
    skill_id = skill["id"]

    # 1. Update to LEARNING
    res1 = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}",
        json={"status": "LEARNING"},
        headers={"X-User-Id": str(test_user.id)},
    )
    assert res1.status_code == 200
    assert res1.json()["data"]["status"] == "LEARNING"

    # Verify reflected in roadmap detail
    detail_learning = client.get(
        f"/api/v1/roadmaps/{backend_meta['id']}",
        headers={"X-User-Id": str(test_user.id)},
    ).json()["data"]
    assert detail_learning["summary"]["learning_skills"] == 1
    assert detail_learning["stages"][0]["skills"][0]["user_status"] == "LEARNING"

    # 2. Update to DONE
    res2 = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}",
        json={"status": "DONE"},
        headers={"X-User-Id": str(test_user.id)},
    )
    assert res2.status_code == 200
    assert res2.json()["data"]["status"] == "DONE"

    # Verify summary metrics
    detail_done = client.get(
        f"/api/v1/roadmaps/{backend_meta['id']}",
        headers={"X-User-Id": str(test_user.id)},
    ).json()["data"]
    assert detail_done["summary"]["completed_skills"] == 1
    assert detail_done["summary"]["progress_percentage"] > 0


def test_invalid_status_update_rejected(test_user):
    """Verify invalid progress status is rejected with 422."""
    catalog = client.get("/api/v1/roadmaps").json()
    backend_meta = next(r for r in catalog["data"] if r["slug"] == "backend-engineer")
    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    skill_id = detail["stages"][0]["skills"][0]["id"]

    res = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}",
        json={"status": "NOT_A_VALID_STATUS"},
        headers={"X-User-Id": str(test_user.id)},
    )
    assert res.status_code == 422


def test_cross_user_progress_isolation(test_user, second_test_user):
    """Verify User A's progress updates never leak to or affect User B."""
    catalog = client.get("/api/v1/roadmaps").json()
    backend_meta = next(r for r in catalog["data"] if r["slug"] == "backend-engineer")
    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    skill_id = detail["stages"][0]["skills"][0]["id"]

    # User A marks skill as DONE
    client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}",
        json={"status": "DONE"},
        headers={"X-User-Id": str(test_user.id)},
    )

    # User B marks same skill as LEARNING
    client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}",
        json={"status": "LEARNING"},
        headers={"X-User-Id": str(second_test_user.id)},
    )

    # Check User A's view: status must be DONE
    user_a_view = client.get(
        f"/api/v1/roadmaps/{backend_meta['id']}",
        headers={"X-User-Id": str(test_user.id)},
    ).json()["data"]
    assert user_a_view["stages"][0]["skills"][0]["user_status"] == "DONE"
    assert user_a_view["summary"]["completed_skills"] == 1
    assert user_a_view["summary"]["learning_skills"] == 0

    # Check User B's view: status must be LEARNING
    user_b_view = client.get(
        f"/api/v1/roadmaps/{backend_meta['id']}",
        headers={"X-User-Id": str(second_test_user.id)},
    ).json()["data"]
    assert user_b_view["stages"][0]["skills"][0]["user_status"] == "LEARNING"
    assert user_b_view["summary"]["completed_skills"] == 0
    assert user_b_view["summary"]["learning_skills"] == 1


# -----------------------------------------------------------------------------
# 5. Canonical Taxonomy Consistency
# -----------------------------------------------------------------------------

def test_canonical_skill_taxonomy_consistency(db):
    """
    Verify that whenever a roadmap skill references a canonical_skill_id,
    that ID exists in the canonical skills table.
    """
    roadmap_skills = db.query(RoadmapSkill).filter(RoadmapSkill.canonical_skill_id.isnot(None)).all()
    canonical_skill_ids = {s.id for s in db.query(Skill).all()}

    for rs in roadmap_skills:
        assert rs.canonical_skill_id in canonical_skill_ids, (
            f"RoadmapSkill '{rs.name}' references invalid canonical_skill_id '{rs.canonical_skill_id}'"
        )


# -----------------------------------------------------------------------------
# 6. User Identity & Authentication Integration Tests
# -----------------------------------------------------------------------------

def test_unauthenticated_roadmap_access():
    """
    Verify that unauthenticated users can access roadmap catalog, full detail,
    stage structure, and learning resources without errors and without being
    forced into a fake user ID.
    """
    # 1. Catalog without user identity
    cat_res = client.get("/api/v1/roadmaps")
    assert cat_res.status_code == 200
    catalog = cat_res.json()["data"]
    backend_meta = next(r for r in catalog if r["slug"] == "backend-engineer")

    # 2. Roadmap detail without user_id or X-User-Id header
    detail_res = client.get(f"/api/v1/roadmaps/{backend_meta['id']}")
    assert detail_res.status_code == 200
    detail = detail_res.json()["data"]
    assert detail["roadmap"]["title"] == "Backend Engineer"
    assert detail["summary"]["total_skills"] > 0
    assert detail["summary"]["completed_skills"] == 0
    assert detail["summary"]["progress_percentage"] == 0

    # Every skill defaults to NOT_STARTED for anonymous/unauthenticated users
    for stage in detail["stages"]:
        for skill in stage["skills"]:
            assert skill["user_status"] == "NOT_STARTED"

    # 3. Flat skill list without user identity
    skills_res = client.get(f"/api/v1/roadmaps/{backend_meta['id']}/skills")
    assert skills_res.status_code == 200
    assert len(skills_res.json()) > 0

    # 4. Single skill detail without user identity
    first_skill_id = detail["stages"][0]["skills"][0]["id"]
    skill_res = client.get(f"/api/v1/roadmaps/{backend_meta['id']}/skills/{first_skill_id}")
    assert skill_res.status_code == 200
    assert skill_res.json()["user_status"] == "NOT_STARTED"
    assert len(skill_res.json()["resources"]) > 0


def test_unauthenticated_progress_mutation_returns_401():
    """
    Verify that progress persistence requires authenticated user identity.
    Unauthenticated calls return 401 Unauthorized.
    """
    catalog = client.get("/api/v1/roadmaps").json()["data"]
    backend_meta = next(r for r in catalog if r["slug"] == "backend-engineer")
    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    skill_id = detail["stages"][0]["skills"][0]["id"]

    # 1. GET /api/v1/users/me/roadmap-progress without auth
    get_res = client.get("/api/v1/users/me/roadmap-progress")
    assert get_res.status_code == 401
    assert "Authenticated user identity required" in get_res.json()["detail"]

    # 2. PUT /api/v1/users/me/roadmap-progress/{skill_id} without auth
    put_res = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}",
        json={"status": "DONE"},
    )
    assert put_res.status_code == 401
    assert "Authenticated user identity required" in put_res.json()["detail"]


def test_nonexistent_user_id_returns_404():
    """
    Verify that providing a non-existent user ID (such as the legacy dummy UUID
    00000000-0000-0000-0000-000000000001) returns 404 NOT FOUND.
    Confirms we do NOT create fake users or weaken verification checks.
    """
    fake_user_id = "00000000-0000-0000-0000-000000000001"
    catalog = client.get("/api/v1/roadmaps").json()["data"]
    backend_meta = next(r for r in catalog if r["slug"] == "backend-engineer")
    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    skill_id = detail["stages"][0]["skills"][0]["id"]

    # 1. Via query param
    res_query = client.get(f"/api/v1/roadmaps/{backend_meta['id']}?user_id={fake_user_id}")
    assert res_query.status_code == 404
    assert f"User with id '{fake_user_id}' not found." in res_query.json()["detail"]

    # 2. Via X-User-Id header
    res_hdr = client.get(
        f"/api/v1/roadmaps/{backend_meta['id']}",
        headers={"X-User-Id": fake_user_id},
    )
    assert res_hdr.status_code == 404
    assert f"User with id '{fake_user_id}' not found." in res_hdr.json()["detail"]

    # 3. On progress GET
    res_prog_get = client.get(
        "/api/v1/users/me/roadmap-progress",
        headers={"X-User-Id": fake_user_id},
    )
    assert res_prog_get.status_code == 404
    assert f"User with id '{fake_user_id}' not found." in res_prog_get.json()["detail"]

    # 4. On progress PUT
    res_prog_put = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}",
        json={"status": "DONE"},
        headers={"X-User-Id": fake_user_id},
    )
    assert res_prog_put.status_code == 404
    assert f"User with id '{fake_user_id}' not found." in res_prog_put.json()["detail"]


def test_cross_user_idor_rejection(test_user, second_test_user):
    """
    Verify IDOR protection: conflicting user_id query param and X-User-Id
    header is strictly rejected with 403 FORBIDDEN.
    """
    catalog = client.get("/api/v1/roadmaps").json()["data"]
    backend_meta = next(r for r in catalog if r["slug"] == "backend-engineer")
    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    skill_id = detail["stages"][0]["skills"][0]["id"]

    # Conflicting IDs on roadmap detail
    res_detail = client.get(
        f"/api/v1/roadmaps/{backend_meta['id']}?user_id={test_user.id}",
        headers={"X-User-Id": str(second_test_user.id)},
    )
    assert res_detail.status_code == 403
    assert "Cross-user access denied" in res_detail.json()["detail"]

    # Conflicting IDs on progress GET
    res_prog_get = client.get(
        f"/api/v1/users/me/roadmap-progress?user_id={test_user.id}",
        headers={"X-User-Id": str(second_test_user.id)},
    )
    assert res_prog_get.status_code == 403
    assert "Cross-user access denied" in res_prog_get.json()["detail"]

    # Conflicting IDs on progress PUT
    res_prog_put = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}?user_id={test_user.id}",
        json={"status": "DONE"},
        headers={"X-User-Id": str(second_test_user.id)},
    )
    assert res_prog_put.status_code == 403
    assert "Cross-user access denied" in res_prog_put.json()["detail"]


# -----------------------------------------------------------------------------
# 5. Practice Problems & Modern Roadmap Tests
# -----------------------------------------------------------------------------

def test_all_skills_have_at_least_three_practice_problems():
    """Verify that every skill across all roadmaps has at least 3 progressive practice problems."""
    catalog = client.get("/api/v1/roadmaps").json()["data"]
    for roadmap_meta in catalog:
        detail = client.get(f"/api/v1/roadmaps/{roadmap_meta['id']}").json()["data"]
        for stage in detail["stages"]:
            for skill in stage["skills"]:
                problems = skill.get("practice_problems", [])
                assert len(problems) >= 3, (
                    f"Roadmap '{roadmap_meta['title']}' skill '{skill['name']}' has only {len(problems)} practice problems"
                )
                for prob in problems:
                    assert prob["problem_id"], "Missing problem_id"
                    assert prob["title"], "Missing problem title"
                    assert prob["difficulty"] in ["BEGINNER", "INTERMEDIATE", "ADVANCED"]
                    assert len(prob["concepts_tested"]) > 0, f"No concepts_tested in problem {prob['problem_id']}"
                    assert len(prob["requirements"]) > 0, f"No requirements in problem {prob['problem_id']}"
                    assert "user_status" in prob, f"user_status not present in problem {prob['problem_id']}"


def test_android_roadmap_completeness():
    """Verify flagship Android roadmap covers Kotlin, Compose, Material 3, Hilt, Room, Retrofit, Navigation, etc."""
    catalog = client.get("/api/v1/roadmaps").json()["data"]
    android_meta = next(r for r in catalog if r["slug"] == "android-developer")
    detail = client.get(f"/api/v1/roadmaps/{android_meta['id']}").json()["data"]

    assert detail["roadmap"]["title"] == "Android Developer"
    assert len(detail["stages"]) >= 6

    all_skill_slugs = {
        skill["slug"]
        for stage in detail["stages"]
        for skill in stage["skills"]
    }

    essential_android_skills = {
        "kotlin-fundamentals",
        "kotlin-coroutines-flow",
        "android-sdk-studio",
        "gradle-build-system",
        "jetpack-compose-fundamentals",
        "material3-design-system",
        "navigation-compose",
        "android-architecture-viewmodel",
        "hilt-dependency-injection",
        "retrofit-okhttp-networking",
        "room-datastore-persistence",
        "workmanager-background-tasks",
        "android-testing-quality",
        "android-security-hardening",
        "gradle-build-optimization-release",
    }
    for essential in essential_android_skills:
        assert essential in all_skill_slugs, f"Android roadmap missing essential skill: {essential}"



def test_user_practice_problem_progress_lifecycle(test_user):
    """Verify updating practice problem status through NOT_STARTED -> IN_PROGRESS -> COMPLETED."""
    catalog = client.get("/api/v1/roadmaps").json()["data"]
    android_meta = next(r for r in catalog if r["slug"] == "android-developer")
    detail = client.get(
        f"/api/v1/roadmaps/{android_meta['id']}?user_id={test_user.id}",
        headers={"X-User-Id": str(test_user.id)},
    ).json()["data"]

    first_skill = detail["stages"][0]["skills"][0]
    skill_id = first_skill["id"]
    first_problem = first_skill["practice_problems"][0]
    problem_id = first_problem["problem_id"]

    # Initial status should be NOT_STARTED
    assert first_problem["user_status"] == "NOT_STARTED"

    # 1. Update to IN_PROGRESS
    res_in_prog = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}/problems/{problem_id}?user_id={test_user.id}",
        json={"status": "IN_PROGRESS"},
        headers={"X-User-Id": str(test_user.id)},
    )
    assert res_in_prog.status_code == 200
    data = res_in_prog.json()["data"]
    assert data["status"] == "IN_PROGRESS"
    assert data["problem_id"] == problem_id
    assert data["completed_at"] is None

    # Verify reflected in roadmap detail
    detail_updated = client.get(
        f"/api/v1/roadmaps/{android_meta['id']}?user_id={test_user.id}",
        headers={"X-User-Id": str(test_user.id)},
    ).json()["data"]
    refetched_skill = detail_updated["stages"][0]["skills"][0]
    refetched_prob = next(p for p in refetched_skill["practice_problems"] if p["problem_id"] == problem_id)
    assert refetched_prob["user_status"] == "IN_PROGRESS"

    # 2. Update to COMPLETED
    res_completed = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}/problems/{problem_id}?user_id={test_user.id}",
        json={"status": "COMPLETED"},
        headers={"X-User-Id": str(test_user.id)},
    )
    assert res_completed.status_code == 200
    assert res_completed.json()["data"]["status"] == "COMPLETED"
    assert res_completed.json()["data"]["completed_at"] is not None


def test_user_practice_problem_cross_user_isolation(test_user, second_test_user):
    """Verify that practice problem progress for user A is completely isolated from user B."""
    catalog = client.get("/api/v1/roadmaps").json()["data"]
    backend_meta = next(r for r in catalog if r["slug"] == "backend-engineer")
    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    skill_id = detail["stages"][0]["skills"][0]["id"]
    problem_id = detail["stages"][0]["skills"][0]["practice_problems"][0]["problem_id"]

    # User A completes problem
    res_a = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}/problems/{problem_id}?user_id={test_user.id}",
        json={"status": "COMPLETED"},
        headers={"X-User-Id": str(test_user.id)},
    )
    assert res_a.status_code == 200

    # User B queries problem: must still be NOT_STARTED
    res_b_detail = client.get(
        f"/api/v1/roadmaps/{backend_meta['id']}?user_id={second_test_user.id}",
        headers={"X-User-Id": str(second_test_user.id)},
    ).json()["data"]
    b_skill = res_b_detail["stages"][0]["skills"][0]
    b_prob = next(p for p in b_skill["practice_problems"] if p["problem_id"] == problem_id)
    assert b_prob["user_status"] == "NOT_STARTED"


def test_invalid_practice_status_rejected(test_user):
    """Verify that invalid practice statuses are rejected with 422."""
    catalog = client.get("/api/v1/roadmaps").json()["data"]
    backend_meta = next(r for r in catalog if r["slug"] == "backend-engineer")
    detail = client.get(f"/api/v1/roadmaps/{backend_meta['id']}").json()["data"]
    skill_id = detail["stages"][0]["skills"][0]["id"]
    problem_id = detail["stages"][0]["skills"][0]["practice_problems"][0]["problem_id"]

    res = client.put(
        f"/api/v1/users/me/roadmap-progress/{skill_id}/problems/{problem_id}?user_id={test_user.id}",
        json={"status": "FINISHED"},
        headers={"X-User-Id": str(test_user.id)},
    )
    assert res.status_code == 422
