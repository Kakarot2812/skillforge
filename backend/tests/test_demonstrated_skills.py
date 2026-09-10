import uuid
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import (
    GitHubRepository,
    ProjectEvidence,
    Skill,
    DemonstratedSkill,
    User,
)
from app.services.demonstrated_skill_service import (
    aggregate_repository_scores,
    compute_evidence_level,
    demonstrated_skill_service,
)
from app.services.github_analyzer import github_analyzer

client = TestClient(app)


def test_aggregation_formula_and_clamping():
    """Verify deterministic multi-repository aggregation formula and clamping."""
    # Empty
    assert aggregate_repository_scores([]) == 0.0

    # Single repo
    assert aggregate_repository_scores([0.95]) == 0.95
    assert aggregate_repository_scores([0.70]) == 0.70

    # Two independent repos (noisy-OR: 1 - (1 - 0.95)(1 - 0.90) = 0.994999... -> rounded to 0.99)
    assert aggregate_repository_scores([0.95, 0.90]) == 0.99
    assert aggregate_repository_scores([0.70, 0.70]) == 0.91

    # Clamping bounds: never exceeds 1.0 or drops below 0.0
    assert 0.0 <= aggregate_repository_scores([1.5, 2.0]) <= 1.0
    assert 0.0 <= aggregate_repository_scores([-0.5]) <= 1.0


def test_evidence_level_classification():
    """Verify deterministic evidence level tiers (HIGH, MEDIUM, LOW)."""
    assert compute_evidence_level(1.0) == "HIGH"
    assert compute_evidence_level(0.85) == "HIGH"
    assert compute_evidence_level(0.84) == "MEDIUM"
    assert compute_evidence_level(0.70) == "MEDIUM"
    assert compute_evidence_level(0.69) == "LOW"
    assert compute_evidence_level(0.0) == "LOW"


def test_single_repo_multiple_evidence_no_inflation():
    """
    Requirement 2 & 4: Multiple evidence items within the SAME repository
    must NOT inflate confidence (max is taken).
    """
    db = SessionLocal()
    repo_id = uuid.uuid4()
    repo = GitHubRepository(
        id=repo_id,
        user_id=None,
        github_repository_id=10101,
        repo_name="single-repo-test",
        full_name="org/single-repo-test",
        repo_url="https://github.com/org/single-repo-test",
        is_fork=False,
    )
    db.add(repo)

    fastapi_skill = db.query(Skill).filter(Skill.slug == "fastapi").first()

    # 3 evidence items in the same repository for FastAPI
    for i in range(3):
        ev = ProjectEvidence(
            id=uuid.uuid4(),
            repo_id=repo_id,
            skill_id=fastapi_skill.id,
            evidence_type="dependency",
            file_path=f"requirements-{i}.txt",
            artifact_name=f"requirements-{i}.txt",
            matched_content="fastapi>=0.115",
            confidence_score=0.95,
        )
        db.add(ev)
    db.commit()

    try:
        # Aggregate
        dem = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=fastapi_skill.id, user_id=None
        )
        assert dem is not None
        # Confidence must remain 0.95, NOT 3 * 0.95 or inflated!
        assert dem.confidence_score == 0.95
        assert dem.evidence_level == "HIGH"
        assert dem.evidence_count == 3
        assert dem.repository_count == 1
    finally:
        db.delete(repo)
        db.commit()
        demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=fastapi_skill.id, user_id=None
        )
        db.close()


def test_multi_repository_independent_confirmation():
    """
    Requirement 3: Independent confirmation across 2 distinct repositories
    increases confidence according to the aggregation formula.
    """
    db = SessionLocal()
    repo1_id = uuid.uuid4()
    repo2_id = uuid.uuid4()

    r1 = GitHubRepository(
        id=repo1_id,
        github_repository_id=20201,
        repo_name="service-alpha",
        full_name="org/service-alpha",
        repo_url="https://github.com/org/service-alpha",
        is_fork=False,
    )
    r2 = GitHubRepository(
        id=repo2_id,
        github_repository_id=20202,
        repo_name="service-beta",
        full_name="org/service-beta",
        repo_url="https://github.com/org/service-beta",
        is_fork=False,
    )
    db.add_all([r1, r2])

    docker_skill = db.query(Skill).filter(Skill.slug == "docker").first()

    # Repo 1 has Dockerfile (0.90)
    ev1 = ProjectEvidence(
        id=uuid.uuid4(),
        repo_id=repo1_id,
        skill_id=docker_skill.id,
        evidence_type="dockerfile",
        file_path="Dockerfile",
        confidence_score=0.90,
    )
    # Repo 2 has docker-compose (0.88)
    ev2 = ProjectEvidence(
        id=uuid.uuid4(),
        repo_id=repo2_id,
        skill_id=docker_skill.id,
        evidence_type="dockerfile",
        file_path="docker-compose.yml",
        confidence_score=0.88,
    )
    db.add_all([ev1, ev2])
    db.commit()

    try:
        dem = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=docker_skill.id, user_id=None
        )
        assert dem is not None
        assert dem.repository_count == 2
        assert dem.evidence_count == 2
        # Combined score: 1 - (1 - 0.90)(1 - 0.88) = 1 - 0.10 * 0.12 = 0.988 -> 0.99
        assert dem.confidence_score == 0.99
        assert dem.evidence_level == "HIGH"
    finally:
        db.delete(r1)
        db.delete(r2)
        db.commit()
        demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=docker_skill.id, user_id=None
        )
        db.close()


def test_recomputation_idempotency_and_stale_removal():
    """
    Requirements 5, 6, 7:
    - Recomputation does not create duplicate rows or alter scores
    - Stale evidence removal lowers counts
    - Total evidence removal deletes the demonstrated skill
    """
    db = SessionLocal()
    repo_id = uuid.uuid4()
    repo = GitHubRepository(
        id=repo_id,
        github_repository_id=30301,
        repo_name="redis-service",
        full_name="org/redis-service",
        repo_url="https://github.com/org/redis-service",
        is_fork=False,
    )
    db.add(repo)

    redis_skill = db.query(Skill).filter(Skill.slug == "redis").first()

    ev1 = ProjectEvidence(
        id=uuid.uuid4(),
        repo_id=repo_id,
        skill_id=redis_skill.id,
        evidence_type="dependency",
        file_path="requirements.txt",
        confidence_score=0.95,
    )
    ev2 = ProjectEvidence(
        id=uuid.uuid4(),
        repo_id=repo_id,
        skill_id=redis_skill.id,
        evidence_type="dockerfile",
        file_path="docker-compose.yml",
        confidence_score=0.88,
    )
    db.add_all([ev1, ev2])
    db.commit()

    try:
        # Initial computation
        dem1 = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=redis_skill.id, user_id=None
        )
        assert dem1 is not None
        dem_id = dem1.id
        assert dem1.evidence_count == 2

        # Idempotent recomputation: same record ID, same score
        dem2 = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=redis_skill.id, user_id=None
        )
        assert dem2.id == dem_id
        assert dem2.confidence_score == dem1.confidence_score

        # Ensure no duplicate DemonstratedSkill records exist
        all_for_skill = (
            db.query(DemonstratedSkill)
            .filter(DemonstratedSkill.skill_id == redis_skill.id, DemonstratedSkill.user_id.is_(None))
            .all()
        )
        assert len(all_for_skill) == 1

        # Delete one evidence item (stale evidence removed)
        db.delete(ev1)
        db.commit()

        dem3 = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=redis_skill.id, user_id=None
        )
        assert dem3.evidence_count == 1
        assert dem3.confidence_score == 0.88

        # Delete the final evidence item -> demonstrated skill must be deleted!
        db.delete(ev2)
        db.commit()

        dem4 = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=redis_skill.id, user_id=None
        )
        assert dem4 is None
        remaining = (
            db.query(DemonstratedSkill)
            .filter(DemonstratedSkill.skill_id == redis_skill.id, DemonstratedSkill.user_id.is_(None))
            .first()
        )
        assert remaining is None

    finally:
        db.delete(repo)
        db.commit()
        db.close()


def test_user_ownership_isolation():
    """
    Requirement 13: Skills demonstrated by User A are isolated from User B.
    """
    db = SessionLocal()
    user_a = User(email=f"user-a-{uuid.uuid4()}@example.com")
    user_b = User(email=f"user-b-{uuid.uuid4()}@example.com")
    db.add_all([user_a, user_b])
    db.commit()

    repo_a = GitHubRepository(
        id=uuid.uuid4(),
        user_id=user_a.id,
        github_repository_id=40401,
        repo_name="repo-a",
        full_name="user-a/repo-a",
        repo_url="https://github.com/user-a/repo-a",
        is_fork=False,
    )
    db.add(repo_a)

    python_skill = db.query(Skill).filter(Skill.slug == "python").first()

    ev_a = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=user_a.id,
        repo_id=repo_a.id,
        skill_id=python_skill.id,
        evidence_type="dependency",
        file_path="requirements.txt",
        confidence_score=0.95,
    )
    db.add(ev_a)
    db.commit()

    try:
        # Recompute for User A
        dem_a = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=python_skill.id, user_id=user_a.id
        )
        assert dem_a is not None

        # Recompute for User B (has no evidence)
        dem_b = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=python_skill.id, user_id=user_b.id
        )
        assert dem_b is None

        # Query endpoint for User B: must be empty
        res_b = client.get(f"/api/v1/skills/demonstrated?user_id={user_b.id}")
        assert res_b.status_code == 200
        assert res_b.json()["meta"]["total"] == 0

        # Query endpoint for User A: must return Python
        res_a = client.get(f"/api/v1/skills/demonstrated?user_id={user_a.id}")
        assert res_a.status_code == 200
        assert res_a.json()["meta"]["total"] == 1
        assert res_a.json()["data"][0]["skill_name"] == "Python"
    finally:
        db.delete(user_a)
        db.delete(user_b)
        db.commit()
        db.close()


def test_demonstrated_skills_api_endpoints_and_filtering():
    """
    Requirements 8, 9, 14, 15, 16, 17, 18, 19:
    - GET /api/v1/skills/demonstrated
    - Filtering by repository_id, skill_id, evidence_level
    - GET /api/v1/skills/demonstrated/{skill_id}
    - 404 for missing demonstrated skill
    """
    db = SessionLocal()
    repo_id = uuid.uuid4()
    repo = GitHubRepository(
        id=repo_id,
        user_id=None,
        github_repository_id=50501,
        repo_name="api-gateway",
        full_name="org/api-gateway",
        repo_url="https://github.com/org/api-gateway",
        is_fork=False,
    )
    db.add(repo)

    go_skill = db.query(Skill).filter(Skill.slug == "go").first()

    ev = ProjectEvidence(
        id=uuid.uuid4(),
        repo_id=repo_id,
        skill_id=go_skill.id,
        evidence_type="dependency",
        file_path="go.mod",
        artifact_name="go.mod",
        matched_content="require github.com/gin-gonic/gin v1.9.1",
        evidence_description="Go module requirement in go.mod",
        confidence_score=0.95,
    )
    db.add(ev)
    db.commit()

    # Aggregate
    demonstrated_skill_service.recompute_demonstrated_skill(
        db=db, skill_id=go_skill.id, user_id=None
    )

    try:
        # 1. GET /api/v1/skills/demonstrated
        res = client.get("/api/v1/skills/demonstrated")
        assert res.status_code == 200
        body = res.json()
        assert "data" in body
        assert "meta" in body
        go_items = [s for s in body["data"] if s["skill_name"] == "Go"]
        assert len(go_items) == 1
        assert go_items[0]["confidence_score"] == 0.95
        assert go_items[0]["evidence_level"] == "HIGH"
        assert go_items[0]["repository_count"] == 1
        assert len(go_items[0]["repositories"]) == 1
        assert go_items[0]["repositories"][0]["repo_name"] == "api-gateway"

        # 2. Filter by skill_id
        res_skill = client.get(f"/api/v1/skills/demonstrated?skill_id={go_skill.id}")
        assert res_skill.status_code == 200
        assert res_skill.json()["meta"]["total"] == 1

        # 3. Filter by repository_id
        res_repo = client.get(f"/api/v1/skills/demonstrated?repository_id={repo_id}")
        assert res_repo.status_code == 200
        assert res_repo.json()["meta"]["total"] == 1

        # 4. Filter by evidence_level=HIGH
        res_high = client.get("/api/v1/skills/demonstrated?evidence_level=HIGH")
        assert res_high.status_code == 200
        assert any(s["skill_name"] == "Go" for s in res_high.json()["data"])

        # 5. Filter by evidence_level=LOW (should NOT include Go)
        res_low = client.get("/api/v1/skills/demonstrated?evidence_level=LOW")
        assert res_low.status_code == 200
        assert not any(s["skill_name"] == "Go" for s in res_low.json()["data"])

        # 6. GET /api/v1/skills/demonstrated/{skill_id} (Detail)
        res_detail = client.get(f"/api/v1/skills/demonstrated/{go_skill.id}")
        assert res_detail.status_code == 200
        d_body = res_detail.json()["data"]
        assert d_body["skill_name"] == "Go"
        assert d_body["confidence_score"] == 0.95
        assert len(d_body["evidence"]) >= 1
        assert d_body["evidence"][0]["file_path"] == "go.mod"
        assert d_body["evidence"][0]["matched_content"] == "require github.com/gin-gonic/gin v1.9.1"

        # 7. Non-existent skill returns 404
        fake_id = str(uuid.uuid4())
        res_404 = client.get(f"/api/v1/skills/demonstrated/{fake_id}")
        assert res_404.status_code == 404
        assert res_404.json()["error"]["code"] == "NOT_FOUND"

    finally:
        db.delete(repo)
        db.commit()
        # Clean up demonstrated skill
        dem = db.query(DemonstratedSkill).filter(DemonstratedSkill.skill_id == go_skill.id).first()
        if dem:
            db.delete(dem)
            db.commit()
        db.close()
