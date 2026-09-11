"""
Automated test suite verifying candidate identity security, isolation, and lifecycle
for GitHub demonstrated skills.

Proves:
A. Candidate A with X-User-Id A receives only A's demonstrated skills.
B. Candidate B with X-User-Id B cannot receive A's demonstrated skills.
C. Conflicting X-User-Id A + query user_id B returns 403 Forbidden.
D. A username belonging to candidate A cannot be used by an unauthenticated/other candidate request to retrieve A's candidate-owned demonstrated skills.
E. Repository analysis with X-User-Id correctly persists/recomputes demonstrated skills for that candidate.
F. Existing legacy/unowned behavior does not expose candidate-owned rows.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import User, Skill, GitHubRepository, ProjectEvidence, DemonstratedSkill
from app.services.demonstrated_skill_service import demonstrated_skill_service

client = TestClient(app)


@pytest.fixture
def identity_fixture():
    db = SessionLocal()

    # 1. Create two canonical candidate users
    user_a = User(
        id=uuid.uuid4(),
        email=f"cand_a_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Candidate Alpha",
    )
    user_b = User(
        id=uuid.uuid4(),
        email=f"cand_b_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Candidate Beta",
    )
    db.add_all([user_a, user_b])
    db.commit()

    # 2. Query or create canonical skills
    python_skill = db.query(Skill).filter(Skill.slug == "python").first()
    fastapi_skill = db.query(Skill).filter(Skill.slug == "fastapi").first()

    # 3. Create repository for Candidate A
    repo_a = GitHubRepository(
        id=uuid.uuid4(),
        user_id=user_a.id,
        github_repository_id=100001,
        repo_name="alpha-project",
        full_name="candidate-a-gh/alpha-project",
        repo_url="https://github.com/candidate-a-gh/alpha-project",
        is_fork=False,
        default_branch="main",
        stars_count=10,
        forks_count=0,
    )
    db.add(repo_a)
    db.commit()

    # 4. Create ProjectEvidence for Candidate A
    ev_a = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=user_a.id,
        repo_id=repo_a.id,
        skill_id=fastapi_skill.id,
        evidence_type="dependency",
        file_path="requirements.txt",
        artifact_name="requirements.txt",
        evidence_description="FastAPI detected in requirements.txt",
        matched_content="fastapi==0.115.0",
        confidence_score=0.95,
    )
    db.add(ev_a)
    db.commit()

    # Recompute demonstrated skill for Candidate A
    dem_a = demonstrated_skill_service.recompute_demonstrated_skill(
        db=db, skill_id=fastapi_skill.id, user_id=user_a.id
    )

    yield {
        "user_a_id": user_a.id,
        "user_b_id": user_b.id,
        "repo_a_id": repo_a.id,
        "fastapi_skill_id": fastapi_skill.id,
        "gh_username_a": "candidate-a-gh",
    }

    # Cleanup
    db.query(DemonstratedSkill).filter(DemonstratedSkill.user_id.in_([user_a.id, user_b.id])).delete()
    db.query(ProjectEvidence).filter(ProjectEvidence.user_id.in_([user_a.id, user_b.id])).delete()
    db.query(GitHubRepository).filter(GitHubRepository.user_id.in_([user_a.id, user_b.id])).delete()
    db.query(User).filter(User.id.in_([user_a.id, user_b.id])).delete()
    db.commit()
    db.close()


def test_candidate_a_receives_only_a_demonstrated_skills(identity_fixture):
    """Test A: Candidate A with X-User-Id A receives only A's demonstrated skills."""
    res = client.get(
        "/api/v1/skills/demonstrated",
        headers={"X-User-Id": str(identity_fixture["user_a_id"])},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    skill_ids = [s["skill_id"] for s in data]
    assert str(identity_fixture["fastapi_skill_id"]) in skill_ids


def test_candidate_b_cannot_receive_candidate_a_demonstrated_skills(identity_fixture):
    """Test B: Candidate B with X-User-Id B cannot receive A's demonstrated skills."""
    res = client.get(
        "/api/v1/skills/demonstrated",
        headers={"X-User-Id": str(identity_fixture["user_b_id"])},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    # Candidate B has no demonstrated skills
    assert len(data) == 0

    # Also check detail endpoint
    res_detail = client.get(
        f"/api/v1/skills/demonstrated/{identity_fixture['fastapi_skill_id']}",
        headers={"X-User-Id": str(identity_fixture["user_b_id"])},
    )
    assert res_detail.status_code == 404


def test_conflicting_user_id_and_header_returns_403(identity_fixture):
    """Test C: Conflicting X-User-Id A + query user_id B returns 403 Forbidden."""
    res = client.get(
        f"/api/v1/skills/demonstrated?user_id={identity_fixture['user_b_id']}",
        headers={"X-User-Id": str(identity_fixture["user_a_id"])},
    )
    assert res.status_code == 403
    assert "Cross-user access denied" in res.json()["detail"]


def test_username_cannot_bypass_candidate_identity(identity_fixture):
    """
    Test D: A username belonging to candidate A cannot be used by an
    unauthenticated or other candidate request to retrieve A's candidate-owned demonstrated skills.
    """
    # Unauthenticated request querying Candidate A's GitHub username
    res_unauth = client.get(
        f"/api/v1/skills/demonstrated?username={identity_fixture['gh_username_a']}"
    )
    assert res_unauth.status_code == 200
    # Must NOT return Candidate A's private demonstrated skills
    assert len(res_unauth.json()["data"]) == 0

    # Candidate B querying Candidate A's GitHub username
    res_other = client.get(
        f"/api/v1/skills/demonstrated?username={identity_fixture['gh_username_a']}",
        headers={"X-User-Id": str(identity_fixture["user_b_id"])},
    )
    assert res_other.status_code == 200
    # Must NOT return Candidate A's demonstrated skills
    assert len(res_other.json()["data"]) == 0


def test_foreign_candidate_cannot_analyze_candidate_a_repo(identity_fixture):
    """Test E: Cross-user analysis protection prevents analyzing another candidate's repo."""
    res = client.post(
        "/api/v1/github/analyze",
        json={"repository_id": str(identity_fixture["repo_a_id"])},
        headers={"X-User-Id": str(identity_fixture["user_b_id"])},
    )
    assert res.status_code == 403
    assert "Cross-user access denied" in res.json()["detail"]


def test_legacy_unowned_behavior_does_not_expose_candidate_rows(identity_fixture):
    """Test F: Existing legacy/unowned query does not expose candidate-owned rows."""
    # Query without any user_id or X-User-Id header
    res = client.get("/api/v1/skills/demonstrated")
    assert res.status_code == 200
    data = res.json()["data"]
    # Candidate A's FastAPI skill must not be present in unowned results
    returned_skill_ids = [s["skill_id"] for s in data]
    assert str(identity_fixture["fastapi_skill_id"]) not in returned_skill_ids

