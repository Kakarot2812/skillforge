import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import (
    JobRole,
    IndustrySkillDemand,
    Skill,
    User,
    Resume,
    UserClaimedSkill,
    GitHubRepository,
    ProjectEvidence,
    DemonstratedSkill,
    SkillGap,
)

client = TestClient(app)


def test_market_benchmark_endpoint_pure_market_data():
    """
    Verifies that GET /api/v1/demand/{role_id} returns objective industry demand data
    with zero candidate-specific classifications or bias.
    """
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "cloud-devops-engineer").first()
    assert role is not None
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/demand/{role_id}?location=India")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "meta" in body
    data = body["data"]

    # Role metadata is present
    assert data["role"]["slug"] == "cloud-devops-engineer"
    assert len(data["skills"]) == 8

    # Verify every skill has statistical demand and growth, but no candidate claim/gap status
    for skill in data["skills"]:
        assert "demand_score" in skill
        assert "growth_rate" in skill
        assert "status" not in skill  # No candidate-specific MISSING/PARTIAL/STRONG in market benchmark
        assert 0.0 <= skill["demand_score"] <= 1.0

    # Meta metrics
    assert data["role"]["title"] == "Cloud/DevOps Engineer"
    assert body["meta"]["total_demanded_skills"] == 8
    assert body["meta"]["top_skill"] == "Git"
    assert body["meta"]["average_demand_score"] > 0


def test_candidate_resume_only_evidence_analysis():
    """
    CASE B: Candidate has an uploaded resume with claims, but NO GitHub evidence.
    Verifies candidate-specific gap analysis classifies claimed skills as PARTIAL
    and unclaimed as MISSING.
    """
    db = SessionLocal()
    user = User(email=f"resume-only-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "cloud-devops-engineer").first()
    docker_skill = db.query(Skill).filter(Skill.slug == "docker").first()
    git_skill = db.query(Skill).filter(Skill.slug == "git").first()
    db.add(user)
    db.flush()

    resume = Resume(
        user_id=user.id,
        file_name="devops_resume.pdf",
        storage_path="/tmp/devops_resume.pdf",
        file_size=1024,
        file_type="pdf",
    )
    db.add(resume)
    db.flush()

    # Candidate claims Docker and Git
    claim1 = UserClaimedSkill(
        user_id=user.id,
        resume_id=resume.id,
        skill_id=docker_skill.id,
        confidence_score=0.85,
        raw_mention="Docker",
    )
    claim2 = UserClaimedSkill(
        user_id=user.id,
        resume_id=resume.id,
        skill_id=git_skill.id,
        confidence_score=0.90,
        raw_mention="Git",
    )
    db.add_all([claim1, claim2])
    db.commit()
    user_id = user.id
    role_id = role.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}&location=India")
        assert res.status_code == 200
        data = res.json()["data"]

        # Resume claims should produce PARTIAL status (in absence of qualifying GitHub evidence)
        skills_by_slug = {s["canonical_slug"]: s for s in data["skills"]}
        assert skills_by_slug["docker"]["status"] == "PARTIAL"
        assert skills_by_slug["docker"]["claimed"] is True
        assert skills_by_slug["docker"]["demonstrated"] is False

        assert skills_by_slug["git"]["status"] == "PARTIAL"
        assert skills_by_slug["git"]["claimed"] is True

        # Unclaimed skills (e.g., Kubernetes, AWS) must be MISSING
        assert skills_by_slug["kubernetes"]["status"] == "MISSING"
        assert skills_by_slug["kubernetes"]["claimed"] is False
        assert skills_by_slug["aws"]["status"] == "MISSING"

        # Summary verification
        summary = data["summary"]
        assert summary["partial_count"] >= 2
        assert summary["missing_count"] <= 6
    finally:
        db = SessionLocal()
        db.query(SkillGap).filter(SkillGap.user_id == user_id).delete()
        db.query(UserClaimedSkill).filter(UserClaimedSkill.user_id == user_id).delete()
        db.query(Resume).filter(Resume.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        db.close()


def test_candidate_github_only_evidence_analysis():
    """
    CASE C: Candidate has connected GitHub with verified code artifacts, but NO resume.
    Verifies candidate-specific gap analysis recognizes demonstrated skills (STRONG if >= 0.85).
    """
    db = SessionLocal()
    user = User(email=f"github-only-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "cloud-devops-engineer").first()
    docker_skill = db.query(Skill).filter(Skill.slug == "docker").first()
    db.add(user)
    db.flush()

    repo = GitHubRepository(
        user_id=user.id,
        github_repository_id=987654321,
        repo_name="cloud-infra-project",
        full_name=f"{user.id}/cloud-infra-project",
        repo_url=f"https://github.com/{user.id}/cloud-infra-project",
        is_fork=False,
    )
    db.add(repo)
    db.flush()

    # Demonstrated Skill with confidence >= 0.85
    demonstrated = DemonstratedSkill(
        user_id=user.id,
        skill_id=docker_skill.id,
        confidence_score=0.90,
        evidence_level="HIGH",
        skill_metadata={"repositories": [{"repo_name": "cloud-infra-project"}]},
    )
    db.add(demonstrated)
    db.commit()
    user_id = user.id
    role_id = role.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}&location=India")
        assert res.status_code == 200
        data = res.json()["data"]

        skills_by_slug = {s["canonical_slug"]: s for s in data["skills"]}
        # Demonstrated Docker with 0.90 confidence => STRONG
        assert skills_by_slug["docker"]["status"] == "STRONG"
        assert skills_by_slug["docker"]["demonstrated"] is True
        assert skills_by_slug["docker"]["claimed"] is False

        # Skills without GitHub proof => MISSING
        assert skills_by_slug["kubernetes"]["status"] == "MISSING"

        # Summary verification
        summary = data["summary"]
        assert summary["strong_count"] == 1
    finally:
        db = SessionLocal()
        db.query(SkillGap).filter(SkillGap.user_id == user_id).delete()
        db.query(DemonstratedSkill).filter(DemonstratedSkill.user_id == user_id).delete()
        db.query(GitHubRepository).filter(GitHubRepository.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        db.close()


def test_multi_source_candidate_synthesis():
    """
    CASE D: Candidate has BOTH resume claims and GitHub code proof.
    Verifies multi-source synthesis correctly categorizes STRONG, PARTIAL, and MISSING.
    """
    db = SessionLocal()
    user = User(email=f"multi-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "cloud-devops-engineer").first()
    docker_skill = db.query(Skill).filter(Skill.slug == "docker").first()
    git_skill = db.query(Skill).filter(Skill.slug == "git").first()
    aws_skill = db.query(Skill).filter(Skill.slug == "aws").first()
    db.add(user)
    db.flush()

    # 1. Resume claim for AWS (PARTIAL)
    resume = Resume(
        user_id=user.id,
        file_name="cloud_resume.pdf",
        storage_path="/tmp/cloud_resume.pdf",
        file_size=2048,
        file_type="pdf",
    )
    db.add(resume)
    db.flush()
    claim_aws = UserClaimedSkill(
        user_id=user.id,
        resume_id=resume.id,
        skill_id=aws_skill.id,
        confidence_score=0.75,
        raw_mention="AWS Cloud",
    )
    db.add(claim_aws)

    # 2. GitHub repo with demonstrated Docker (STRONG)
    repo = GitHubRepository(
        user_id=user.id,
        github_repository_id=123456789,
        repo_name="docker-pipeline",
        full_name=f"{user.id}/docker-pipeline",
        repo_url=f"https://github.com/{user.id}/docker-pipeline",
        is_fork=False,
    )
    db.add(repo)
    db.flush()
    dem_docker = DemonstratedSkill(
        user_id=user.id,
        skill_id=docker_skill.id,
        confidence_score=0.92,
        evidence_level="HIGH",
        skill_metadata={"repositories": []},
    )
    db.add(dem_docker)

    # 3. Resume claim AND GitHub demonstrated for Git (STRONG)
    claim_git = UserClaimedSkill(
        user_id=user.id,
        resume_id=resume.id,
        skill_id=git_skill.id,
        confidence_score=0.95,
        raw_mention="Git Version Control",
    )
    dem_git = DemonstratedSkill(
        user_id=user.id,
        skill_id=git_skill.id,
        confidence_score=0.88,
        evidence_level="HIGH",
        skill_metadata={"repositories": []},
    )
    db.add_all([claim_git, dem_git])
    db.commit()
    user_id = user.id
    role_id = role.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}&location=India")
        assert res.status_code == 200
        data = res.json()["data"]
        skills_by_slug = {s["canonical_slug"]: s for s in data["skills"]}

        # Docker: GitHub demonstrated (0.92 >= 0.85) => STRONG
        assert skills_by_slug["docker"]["status"] == "STRONG"

        # Git: Claimed + Demonstrated (0.88 >= 0.85) => STRONG
        assert skills_by_slug["git"]["status"] == "STRONG"
        assert skills_by_slug["git"]["claimed"] is True
        assert skills_by_slug["git"]["demonstrated"] is True

        # AWS: Claimed in resume only => PARTIAL
        assert skills_by_slug["aws"]["status"] == "PARTIAL"
        assert skills_by_slug["aws"]["claimed"] is True
        assert skills_by_slug["aws"]["demonstrated"] is False

        # Kubernetes: No evidence in either source => MISSING
        assert skills_by_slug["kubernetes"]["status"] == "MISSING"

        summary = data["summary"]
        assert summary["strong_count"] == 2
        assert summary["partial_count"] == 1
        assert summary["missing_count"] == 5
    finally:
        db = SessionLocal()
        db.query(SkillGap).filter(SkillGap.user_id == user_id).delete()
        db.query(DemonstratedSkill).filter(DemonstratedSkill.user_id == user_id).delete()
        db.query(GitHubRepository).filter(GitHubRepository.user_id == user_id).delete()
        db.query(UserClaimedSkill).filter(UserClaimedSkill.user_id == user_id).delete()
        db.query(Resume).filter(Resume.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        db.close()


def test_resume_exclusion_clears_resume_evidence():
    """
    Verifies that include_resume=False strictly excludes resume claims
    from gap calculations (e.g. after candidate deletes their resume).
    """
    db = SessionLocal()
    user = User(email=f"del-resume-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "cloud-devops-engineer").first()
    docker_skill = db.query(Skill).filter(Skill.slug == "docker").first()
    db.add(user)
    db.flush()

    resume = Resume(
        user_id=user.id,
        file_name="temp_resume.pdf",
        storage_path="/tmp/temp_resume.pdf",
        file_size=1024,
        file_type="pdf",
    )
    db.add(resume)
    db.flush()

    claim = UserClaimedSkill(
        user_id=user.id,
        resume_id=resume.id,
        skill_id=docker_skill.id,
        confidence_score=0.90,
        raw_mention="Docker",
    )
    db.add(claim)
    db.commit()
    user_id = user.id
    role_id = role.id
    db.close()

    try:
        # With resume included: docker is PARTIAL
        res_with = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}&include_resume=true&include_github=false")
        assert res_with.status_code == 200
        docker_with = next(s for s in res_with.json()["data"]["skills"] if s["canonical_slug"] == "docker")
        assert docker_with["status"] == "PARTIAL"
        assert docker_with["claimed"] is True

        # When resume is excluded (deleted/deselected): docker drops to MISSING
        res_without = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}&include_resume=false&include_github=false")
        assert res_without.status_code == 200
        docker_without = next(s for s in res_without.json()["data"]["skills"] if s["canonical_slug"] == "docker")
        assert docker_without["status"] == "MISSING"
        assert docker_without["claimed"] is False
    finally:
        db = SessionLocal()
        db.query(SkillGap).filter(SkillGap.user_id == user_id).delete()
        db.query(UserClaimedSkill).filter(UserClaimedSkill.user_id == user_id).delete()
        db.query(Resume).filter(Resume.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        db.close()


def test_github_exclusion_clears_github_evidence():
    """
    Verifies that include_github=False strictly excludes GitHub evidence
    from gap calculations (e.g. after candidate disconnects GitHub).
    """
    db = SessionLocal()
    user = User(email=f"disconn-gh-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "cloud-devops-engineer").first()
    docker_skill = db.query(Skill).filter(Skill.slug == "docker").first()
    db.add(user)
    db.flush()

    repo = GitHubRepository(
        user_id=user.id,
        github_repository_id=11223344,
        repo_name="my-infra",
        full_name=f"{user.id}/my-infra",
        repo_url=f"https://github.com/{user.id}/my-infra",
        is_fork=False,
    )
    db.add(repo)
    db.flush()

    dem = DemonstratedSkill(
        user_id=user.id,
        skill_id=docker_skill.id,
        confidence_score=0.92,
        evidence_level="HIGH",
        skill_metadata={"repositories": []},
    )
    db.add(dem)
    db.commit()
    user_id = user.id
    role_id = role.id
    db.close()

    try:
        # With GitHub included: docker is STRONG
        res_with = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}&include_github=true&include_resume=false")
        assert res_with.status_code == 200
        docker_with = next(s for s in res_with.json()["data"]["skills"] if s["canonical_slug"] == "docker")
        assert docker_with["status"] == "STRONG"
        assert docker_with["demonstrated"] is True

        # When GitHub is excluded (disconnected): docker drops to MISSING
        res_without = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}&include_github=false&include_resume=false")
        assert res_without.status_code == 200
        docker_without = next(s for s in res_without.json()["data"]["skills"] if s["canonical_slug"] == "docker")
        assert docker_without["status"] == "MISSING"
        assert docker_without["demonstrated"] is False
    finally:
        db = SessionLocal()
        db.query(SkillGap).filter(SkillGap.user_id == user_id).delete()
        db.query(DemonstratedSkill).filter(DemonstratedSkill.user_id == user_id).delete()
        db.query(GitHubRepository).filter(GitHubRepository.user_id == user_id).delete()
        db.query(User).filter(User.id == user_id).delete()
        db.commit()
        db.close()


def test_github_username_switching_isolation():
    """
    Verifies that candidate gap analysis scoped to userA does NOT incorporate
    evidence from userB when usernames are switched.
    """
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "cloud-devops-engineer").first()
    docker_skill = db.query(Skill).filter(Skill.slug == "docker").first()

    # Create DemonstratedSkill for alice-dev
    dem_alice = DemonstratedSkill(
        skill_id=docker_skill.id,
        confidence_score=0.95,
        evidence_level="HIGH",
        skill_metadata={"repositories": [{"repo_name": "alice-dev/docker-tool", "owner": "alice-dev"}]},
    )
    db.add(dem_alice)
    db.commit()
    dem_id = dem_alice.id
    role_id = role.id
    db.close()

    try:
        # Scoped to alice-dev -> Docker is STRONG
        res_alice = client.get(f"/api/v1/gaps/{role_id}?username=alice-dev&include_resume=false&include_github=true")
        assert res_alice.status_code == 200
        docker_alice = next(s for s in res_alice.json()["data"]["skills"] if s["canonical_slug"] == "docker")
        assert docker_alice["status"] == "STRONG"
        assert docker_alice["demonstrated"] is True

        # Switch to bob-engineer -> alice's Docker proof must NOT leak to bob
        res_bob = client.get(f"/api/v1/gaps/{role_id}?username=bob-engineer&include_resume=false&include_github=true")
        assert res_bob.status_code == 200
        docker_bob = next(s for s in res_bob.json()["data"]["skills"] if s["canonical_slug"] == "docker")
        assert docker_bob["status"] == "MISSING"
        assert docker_bob["demonstrated"] is False
    finally:
        db = SessionLocal()
        db.query(DemonstratedSkill).filter(DemonstratedSkill.id == dem_id).delete()
        db.commit()
        db.close()

