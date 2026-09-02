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
from app.services.skill_gap_evidence_service import (
    skill_gap_evidence_service,
    build_classification_explanation,
    build_priority_explanation,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1-5: Pure Explanation Function Tests
# -----------------------------------------------------------------------------

def test_strong_classification_explanation():
    """1. STRONG status generates grounded explanation referencing GitHub confidence and repo count."""
    exp = build_classification_explanation(
        status="STRONG",
        claimed=False,
        demonstrated=True,
        demonstrated_score=0.92,
        evidence_level="HIGH",
        raw_mention=None,
        evidence_count=4,
        repository_count=2,
    )
    assert "Strong because" in exp
    assert "92%" in exp
    assert "2 repository" in exp
    assert "4 evidence artifact" in exp


def test_partial_resume_only_explanation():
    """2. PARTIAL status from resume claim only explicitly notes absence of GitHub code artifacts."""
    exp = build_classification_explanation(
        status="PARTIAL",
        claimed=True,
        demonstrated=False,
        demonstrated_score=0.0,
        evidence_level=None,
        raw_mention="Python 3.12",
        evidence_count=0,
        repository_count=0,
    )
    assert "Partial because" in exp
    assert "Python 3.12" in exp
    assert "no verified GitHub code demonstration was found" in exp


def test_partial_github_only_explanation():
    """3. PARTIAL status from low/medium GitHub evidence notes score is below 85% threshold."""
    exp = build_classification_explanation(
        status="PARTIAL",
        claimed=False,
        demonstrated=True,
        demonstrated_score=0.72,
        evidence_level="MEDIUM",
        raw_mention=None,
        evidence_count=2,
        repository_count=1,
    )
    assert "Partial because" in exp
    assert "72%" in exp
    assert "below the strong threshold (85%)" in exp


def test_missing_explanation():
    """4. MISSING status explanation clearly states neither resume nor GitHub evidence was found."""
    exp = build_classification_explanation(
        status="MISSING",
        claimed=False,
        demonstrated=False,
        demonstrated_score=0.0,
        evidence_level=None,
        raw_mention=None,
        evidence_count=0,
        repository_count=0,
    )
    assert "Missing because neither a resume claim nor verified GitHub code evidence was found" in exp


def test_priority_explanation_rules():
    """5. Priority explanation connects severity, demand %, and growth trend deterministically."""
    exp_high = build_priority_explanation("MISSING", "HIGH", 0.75, 0.85, 0.12)
    assert "HIGH priority" in exp_high
    assert "missing" in exp_high
    assert "85%" in exp_high
    assert "rapid industry growth" in exp_high

    exp_strong = build_priority_explanation("STRONG", None, 0.0, 0.90, 0.05)
    assert "already sufficiently demonstrated" in exp_strong


# -----------------------------------------------------------------------------
# 6-10: Evidence Retrieval & Integrity Tests
# -----------------------------------------------------------------------------

def test_gap_evidence_complete_candidate_evidence():
    """6. Returns full audit trail: Resume claim + GitHub repository artifacts + Market demand."""
    db = SessionLocal()
    user = User(email=f"audit-full-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()

    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    skill_id = skill.id

    # 1. Resume claim
    resume = Resume(
        id=uuid.uuid4(),
        user_id=user.id,
        file_name="resume_2026.pdf",
        file_type="application/pdf",
        file_size=12345,
        storage_path="/resumes/1.pdf",
    )
    db.add(resume)
    db.commit()

    claimed = UserClaimedSkill(
        id=uuid.uuid4(),
        user_id=user.id,
        skill_id=skill_id,
        resume_id=resume.id,
        raw_mention="Python 3.12 (Advanced)",
        confidence_score=1.0,
    )

    # 2. GitHub repository & project evidence
    repo = GitHubRepository(
        id=uuid.uuid4(),
        user_id=user.id,
        repo_name="fastapi-microservices",
        full_name="candidate/fastapi-microservices",
        repo_url="https://github.com/candidate/fastapi-microservices",
    )
    db.add(repo)
    db.commit()

    ev1 = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=user.id,
        repo_id=repo.id,
        skill_id=skill_id,
        evidence_type="MANIFEST_DEPENDENCY",
        file_path="requirements.txt",
        artifact_name="fastapi",
        matched_content="fastapi>=0.110.0",
        confidence_score=0.95,
    )
    ev2 = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=user.id,
        repo_id=repo.id,
        skill_id=skill_id,
        evidence_type="DOCKER_FILE",
        file_path="Dockerfile",
        artifact_name="python:3.12-slim",
        matched_content="FROM python:3.12-slim",
        confidence_score=0.88,
    )
    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=user.id,
        skill_id=skill_id,
        confidence_score=0.95,
        evidence_level="HIGH",
        evidence_count=2,
        repository_count=1,
    )

    db.add_all([claimed, ev1, ev2, demo])
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}/skills/{skill_id}/evidence?user_id={user_id}")
        assert res.status_code == 200
        data = res.json()["data"]

        # Skill & Status
        assert data["skill_name"] == "Python"
        assert data["canonical_slug"] == "python"
        assert data["status"] == "STRONG"

        # Candidate Evidence
        cand = data["candidate_evidence"]
        assert cand["has_evidence"] is True
        assert len(cand["resume_claims"]) == 1
        claim = cand["resume_claims"][0]
        assert claim["raw_mention"] == "Python 3.12 (Advanced)"
        assert claim["resume_file_name"] == "resume_2026.pdf"

        assert cand["github_demonstrated"]["evidence_level"] == "HIGH"
        assert cand["github_demonstrated"]["repository_count"] == 1
        assert len(cand["github_artifacts"]) == 2
        artifacts = cand["github_artifacts"]
        assert artifacts[0]["repo_name"] == "fastapi-microservices"

        # Market Evidence
        market = data["market_evidence"]
        assert market["role_slug"] == "backend-engineer"
        assert market["demand_score"] > 0.0

        # Deterministic Reasoning
        reasoning = data["reasoning"]
        assert "Strong because" in reasoning["classification_reason"]
        assert reasoning["scoring_version"] == "v1"
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


def test_gap_evidence_empty_candidate_evidence_is_200():
    """7. Candidate with no claims and no code artifacts gets 200 OK with empty evidence list."""
    db = SessionLocal()
    user = User(email=f"empty-cand-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    skill = db.query(Skill).filter(Skill.slug == "docker").first()
    skill_id = skill.id
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}/skills/{skill_id}/evidence?user_id={user_id}")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["status"] == "MISSING"

        cand = data["candidate_evidence"]
        assert cand["has_evidence"] is False
        assert len(cand["resume_claims"]) == 0
        assert cand["github_demonstrated"] is None
        assert len(cand["github_artifacts"]) == 0

        # Market evidence is still intact
        assert data["market_evidence"]["role_slug"] == "backend-engineer"
        assert data["market_evidence"]["demand_score"] > 0.0
        assert "Missing because" in data["reasoning"]["classification_reason"]
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


# -----------------------------------------------------------------------------
# 8-12: Error Handling & Security Tests
# -----------------------------------------------------------------------------

def test_evidence_malformed_role_uuid():
    """8. Malformed role UUID returns 422 VALIDATION_ERROR."""
    res = client.get(f"/api/v1/gaps/not-a-uuid/skills/{uuid.uuid4()}/evidence")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_evidence_malformed_skill_uuid():
    """9. Malformed skill UUID returns 422 VALIDATION_ERROR."""
    res = client.get(f"/api/v1/gaps/{uuid.uuid4()}/skills/not-a-uuid/evidence")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_evidence_nonexistent_role():
    """10. Nonexistent role returns 404 NOT_FOUND."""
    fake_role = uuid.uuid4()
    db = SessionLocal()
    skill = db.query(Skill).first()
    skill_id = skill.id
    db.close()

    res = client.get(f"/api/v1/gaps/{fake_role}/skills/{skill_id}/evidence")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_evidence_skill_not_demanded_for_role():
    """11. Demanding evidence for a skill that is not required for the role returns 404 NOT_FOUND."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    role_id = role.id
    # PyTorch is AI/ML, NOT demanded for frontend-engineer
    pytorch_skill = db.query(Skill).filter(Skill.slug == "pytorch").first()
    skill_id = pytorch_skill.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}/skills/{skill_id}/evidence")
    assert res.status_code == 404
    assert "not demanded" in res.json()["error"]["message"]


def test_evidence_user_ownership_isolation():
    """12. User A cannot view User B's resume claims or GitHub artifacts."""
    db = SessionLocal()
    user_a = User(email=f"userA-evid-{uuid.uuid4()}@example.com")
    user_b = User(email=f"userB-evid-{uuid.uuid4()}@example.com")
    db.add_all([user_a, user_b])
    db.commit()

    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    skill_id = skill.id

    # User A has claim
    claim_a = UserClaimedSkill(
        id=uuid.uuid4(),
        user_id=user_a.id,
        skill_id=skill_id,
        raw_mention="User A Special Python Claim",
        confidence_score=1.0,
    )
    db.add(claim_a)
    db.commit()
    u_a_id = user_a.id
    u_b_id = user_b.id
    db.close()

    try:
        # User A sees the claim
        res_a = client.get(f"/api/v1/gaps/{role_id}/skills/{skill_id}/evidence?user_id={u_a_id}")
        assert res_a.status_code == 200
        claims_a = res_a.json()["data"]["candidate_evidence"]["resume_claims"]
        assert len(claims_a) == 1
        assert claims_a[0]["raw_mention"] == "User A Special Python Claim"

        # User B does NOT see User A's claim
        res_b = client.get(f"/api/v1/gaps/{role_id}/skills/{skill_id}/evidence?user_id={u_b_id}")
        assert res_b.status_code == 200
        claims_b = res_b.json()["data"]["candidate_evidence"]["resume_claims"]
        assert len(claims_b) == 0
        assert res_b.json()["data"]["status"] == "MISSING"
    finally:
        db = SessionLocal()
        ua = db.query(User).filter(User.id == u_a_id).first()
        ub = db.query(User).filter(User.id == u_b_id).first()
        if ua: db.delete(ua)
        if ub: db.delete(ub)
        db.commit()
        db.close()


def test_evidence_header_x_user_id_resolution():
    """13. Header X-User-Id properly scopes the evidence request."""
    db = SessionLocal()
    user = User(email=f"hdr-evid-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    skill_id = skill.id
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(
            f"/api/v1/gaps/{role_id}/skills/{skill_id}/evidence",
            headers={"X-User-Id": str(user_id)},
        )
        assert res.status_code == 200
        assert res.json()["meta"]["user_id"] == str(user_id)
        assert res.json()["meta"]["scoring_version"] == "v1"
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


def test_evidence_deterministic_ordering():
    """14. Multiple GitHub evidence artifacts are sorted deterministically (repo_name ASC, type ASC, confidence DESC, id ASC)."""
    db = SessionLocal()
    user = User(email=f"evid-order-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()

    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    skill = db.query(Skill).filter(Skill.slug == "fastapi").first()
    skill_id = skill.id

    repo_z = GitHubRepository(id=uuid.uuid4(), user_id=user.id, repo_name="z-repo", repo_url="https://github.com/u/z")
    repo_a = GitHubRepository(id=uuid.uuid4(), user_id=user.id, repo_name="a-repo", repo_url="https://github.com/u/a")
    db.add_all([repo_z, repo_a])
    db.commit()

    ev_z = ProjectEvidence(
        id=uuid.uuid4(), user_id=user.id, repo_id=repo_z.id, skill_id=skill_id,
        evidence_type="MANIFEST_DEPENDENCY", confidence_score=0.95
    )
    ev_a = ProjectEvidence(
        id=uuid.uuid4(), user_id=user.id, repo_id=repo_a.id, skill_id=skill_id,
        evidence_type="MANIFEST_DEPENDENCY", confidence_score=0.90
    )
    db.add_all([ev_z, ev_a])
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}/skills/{skill_id}/evidence?user_id={user_id}")
        assert res.status_code == 200
        artifacts = res.json()["data"]["candidate_evidence"]["github_artifacts"]
        assert len(artifacts) == 2
        # a-repo comes before z-repo
        assert artifacts[0]["repo_name"] == "a-repo"
        assert artifacts[1]["repo_name"] == "z-repo"
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()
