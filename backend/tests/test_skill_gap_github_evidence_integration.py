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
from app.services.demonstrated_skill_service import (
    is_repo_owned_by_user,
    aggregate_repository_scores,
    compute_evidence_level,
    demonstrated_skill_service,
)
from app.services.skill_gap_service import skill_gap_service
from app.services.skill_gap_evidence_service import skill_gap_evidence_service

client = TestClient(app)


# =============================================================================
# Helper Unit Tests: is_repo_owned_by_user (Tests 11, 12, 13)
# =============================================================================

def test_11_legacy_repo_summary_ownership():
    """TEST 11: Legacy repo summary with repo_name and repo_url matches username."""
    legacy_repo = {
        "repository_id": str(uuid.uuid4()),
        "repo_name": "skillforge",
        "repo_url": "https://github.com/Kakarot2812/skillforge",
        "max_confidence": 0.95,
        "evidence_count": 1,
    }
    assert is_repo_owned_by_user(legacy_repo, "Kakarot2812") is True


def test_12_different_username_ownership_false():
    """TEST 12: Repository belonging to AnotherUser returns ownership FALSE for Kakarot2812."""
    other_repo = {
        "repository_id": str(uuid.uuid4()),
        "repo_name": "skillforge",
        "repo_url": "https://github.com/AnotherUser/skillforge",
        "max_confidence": 0.95,
        "evidence_count": 1,
    }
    assert is_repo_owned_by_user(other_repo, "Kakarot2812") is False


def test_13_case_insensitive_username_matching():
    """TEST 13: Case-insensitive matching works reliably and prevents collision."""
    repo = {
        "repository_id": str(uuid.uuid4()),
        "repo_name": "my-app",
        "repo_url": "https://github.com/OctoCat/my-app",
    }
    assert is_repo_owned_by_user(repo, "octocat") is True
    assert is_repo_owned_by_user(repo, "OCTOCAT") is True
    assert is_repo_owned_by_user(repo, "@octocat") is True
    assert is_repo_owned_by_user(repo, "octocat-other") is False
    assert is_repo_owned_by_user(repo, "octo") is False
    assert is_repo_owned_by_user(repo, "") is False
    assert is_repo_owned_by_user(repo, None) is False


# =============================================================================
# Core Gap Classification & Evidence Integration Tests (Tests 1 - 6)
# =============================================================================

def test_01_and_02_github_high_react_is_strong_and_not_missing():
    """
    TEST 1 & TEST 2:
    Candidate with GitHub HIGH React evidence (>= 0.85)
    -> React is NOT MISSING
    -> React is classified as STRONG.
    """
    db = SessionLocal()
    react_skill = db.query(Skill).filter(Skill.slug == "react").first()
    fs_role = db.query(JobRole).filter(JobRole.slug == "full-stack-engineer").first()
    test_user = f"gh-react-test-{uuid.uuid4().hex[:8]}"

    # Add DemonstratedSkill with high confidence for this candidate
    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=None,
        skill_id=react_skill.id,
        confidence_score=0.95,
        evidence_level="HIGH",
        evidence_count=2,
        repository_count=1,
        skill_metadata={
            "repositories": [
                {
                    "repo_name": "skillforge",
                    "repo_url": f"https://github.com/{test_user}/skillforge",
                    "max_confidence": 0.95,
                    "evidence_count": 2,
                }
            ],
            "evidence_types": ["dependency"],
        },
    )
    db.add(demo)
    db.commit()

    try:
        res = client.get(
            f"/api/v1/gaps/{fs_role.id}?location=India&include_resume=true&include_github=true&username={test_user}"
        )
        assert res.status_code == 200
        data = res.json()["data"]
        react_item = next(s for s in data["skills"] if s["canonical_slug"] == "react")

        # TEST 1: NOT MISSING
        assert react_item["status"] != "MISSING"

        # TEST 2: STRONG
        assert react_item["status"] == "STRONG"
        assert react_item["demonstrated"] is True
        assert react_item["demonstrated_score"] == 0.95
        assert react_item["evidence_level"] == "HIGH"
    finally:
        db.delete(demo)
        db.commit()
        db.close()


def test_03_resume_react_plus_github_high_react_remains_strong():
    """
    TEST 3:
    Candidate with both Resume React claim + GitHub HIGH React
    -> React remains STRONG.
    """
    db = SessionLocal()
    react_skill = db.query(Skill).filter(Skill.slug == "react").first()
    fs_role = db.query(JobRole).filter(JobRole.slug == "full-stack-engineer").first()
    test_user = f"both-react-{uuid.uuid4().hex[:8]}"

    resume = Resume(
        id=uuid.uuid4(),
        file_name="resume_with_react.pdf",
        file_type="pdf",
        file_size=2048,
        storage_path="/uploads/test.pdf",
    )
    db.add(resume)
    db.commit()

    claim = UserClaimedSkill(
        id=uuid.uuid4(),
        resume_id=resume.id,
        skill_id=react_skill.id,
        raw_mention="React 18 / Redux",
        confidence_score=1.0,
    )
    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=None,
        skill_id=react_skill.id,
        confidence_score=0.92,
        evidence_level="HIGH",
        evidence_count=3,
        repository_count=1,
        skill_metadata={
            "repositories": [
                {
                    "repo_name": "frontend-suite",
                    "repo_url": f"https://github.com/{test_user}/frontend-suite",
                    "max_confidence": 0.92,
                    "evidence_count": 3,
                }
            ]
        },
    )
    db.add_all([claim, demo])
    db.commit()

    try:
        res = client.get(
            f"/api/v1/gaps/{fs_role.id}?location=India&include_resume=true&include_github=true&username={test_user}&resume_id={resume.id}"
        )
        assert res.status_code == 200
        data = res.json()["data"]
        react_item = next(s for s in data["skills"] if s["canonical_slug"] == "react")

        assert react_item["status"] == "STRONG"
        assert react_item["claimed"] is True
        assert react_item["demonstrated"] is True
        assert react_item["demonstrated_score"] == 0.92
    finally:
        db.delete(demo)
        db.delete(claim)
        db.delete(resume)
        db.commit()
        db.close()


def test_04_resume_react_only_is_partial():
    """
    TEST 4:
    Candidate with Resume React claim ONLY (no GitHub evidence for this candidate)
    -> React is PARTIAL.
    """
    db = SessionLocal()
    react_skill = db.query(Skill).filter(Skill.slug == "react").first()
    fs_role = db.query(JobRole).filter(JobRole.slug == "full-stack-engineer").first()
    test_user = f"resume-only-{uuid.uuid4().hex[:8]}"

    resume = Resume(
        id=uuid.uuid4(),
        file_name="resume_react_only.pdf",
        file_type="pdf",
        file_size=2048,
        storage_path="/uploads/test.pdf",
    )
    db.add(resume)
    db.commit()

    claim = UserClaimedSkill(
        id=uuid.uuid4(),
        resume_id=resume.id,
        skill_id=react_skill.id,
        raw_mention="React Developer Claim",
        confidence_score=1.0,
    )
    db.add(claim)
    db.commit()

    try:
        res = client.get(
            f"/api/v1/gaps/{fs_role.id}?location=India&include_resume=true&include_github=true&username={test_user}&resume_id={resume.id}"
        )
        assert res.status_code == 200
        data = res.json()["data"]
        react_item = next(s for s in data["skills"] if s["canonical_slug"] == "react")

        assert react_item["status"] == "PARTIAL"
        assert react_item["claimed"] is True
        assert react_item["demonstrated"] is False
    finally:
        db.delete(claim)
        db.delete(resume)
        db.commit()
        db.close()


def test_05_neither_resume_nor_github_react_is_missing():
    """
    TEST 5:
    Neither Resume nor GitHub provides React evidence
    -> React is MISSING.
    """
    db = SessionLocal()
    fs_role = db.query(JobRole).filter(JobRole.slug == "full-stack-engineer").first()
    test_user = f"ghost-candidate-{uuid.uuid4().hex[:8]}"
    db.close()

    res = client.get(
        f"/api/v1/gaps/{fs_role.id}?location=India&include_resume=true&include_github=true&username={test_user}"
    )
    assert res.status_code == 200
    data = res.json()["data"]
    react_item = next(s for s in data["skills"] if s["canonical_slug"] == "react")

    assert react_item["status"] == "MISSING"
    assert react_item["claimed"] is False
    assert react_item["demonstrated"] is False


def test_06_github_low_confidence_react_is_partial():
    """
    TEST 6:
    GitHub demonstrated score is below STRONG threshold (< 0.85)
    -> React is PARTIAL (existing threshold behavior preserved).
    """
    db = SessionLocal()
    react_skill = db.query(Skill).filter(Skill.slug == "react").first()
    fs_role = db.query(JobRole).filter(JobRole.slug == "full-stack-engineer").first()
    test_user = f"low-conf-react-{uuid.uuid4().hex[:8]}"

    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=None,
        skill_id=react_skill.id,
        confidence_score=0.70,
        evidence_level="MEDIUM",
        evidence_count=1,
        repository_count=1,
        skill_metadata={
            "repositories": [
                {
                    "repo_name": "react-starter",
                    "repo_url": f"https://github.com/{test_user}/react-starter",
                    "max_confidence": 0.70,
                    "evidence_count": 1,
                }
            ]
        },
    )
    db.add(demo)
    db.commit()

    try:
        res = client.get(
            f"/api/v1/gaps/{fs_role.id}?location=India&include_resume=true&include_github=true&username={test_user}"
        )
        assert res.status_code == 200
        data = res.json()["data"]
        react_item = next(s for s in data["skills"] if s["canonical_slug"] == "react")

        assert react_item["status"] == "PARTIAL"
        assert react_item["demonstrated"] is True
        assert react_item["demonstrated_score"] == 0.70
        assert react_item["evidence_level"] == "MEDIUM"
    finally:
        db.delete(demo)
        db.commit()
        db.close()


# =============================================================================
# Cross-User and Resume Isolation Tests (Tests 7, 8, 14)
# =============================================================================

def test_07_and_14_cross_user_github_evidence_isolation():
    """
    TEST 7 & TEST 14:
    User A has verified HIGH React evidence in GitHub.
    User B connects a different GitHub account with NO React evidence.
    User B MUST NOT receive React evidence or STRONG classification.
    Candidate A's repositories do not affect Candidate B's score.
    """
    db = SessionLocal()
    react_skill = db.query(Skill).filter(Skill.slug == "react").first()
    fs_role = db.query(JobRole).filter(JobRole.slug == "full-stack-engineer").first()
    user_a = f"alice-{uuid.uuid4().hex[:6]}"
    user_b = f"bob-{uuid.uuid4().hex[:6]}"

    # Demo record has repo owned by Alice only
    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=None,
        skill_id=react_skill.id,
        confidence_score=0.95,
        evidence_level="HIGH",
        evidence_count=1,
        repository_count=1,
        skill_metadata={
            "repositories": [
                {
                    "repo_name": "alice-react-app",
                    "repo_url": f"https://github.com/{user_a}/alice-react-app",
                    "max_confidence": 0.95,
                    "evidence_count": 1,
                }
            ]
        },
    )
    db.add(demo)
    db.commit()

    try:
        # Alice gets STRONG
        res_a = client.get(
            f"/api/v1/gaps/{fs_role.id}?location=India&include_resume=true&include_github=true&username={user_a}"
        )
        assert res_a.status_code == 200
        react_a = next(s for s in res_a.json()["data"]["skills"] if s["canonical_slug"] == "react")
        assert react_a["status"] == "STRONG"
        assert react_a["demonstrated"] is True

        # Bob gets MISSING (Alice's evidence does not leak)
        res_b = client.get(
            f"/api/v1/gaps/{fs_role.id}?location=India&include_resume=true&include_github=true&username={user_b}"
        )
        assert res_b.status_code == 200
        react_b = next(s for s in res_b.json()["data"]["skills"] if s["canonical_slug"] == "react")
        assert react_b["status"] == "MISSING"
        assert react_b["demonstrated"] is False
        assert react_b["demonstrated_score"] == 0.0
    finally:
        db.delete(demo)
        db.commit()
        db.close()


def test_08_historical_resume_isolation_preserved():
    """
    TEST 8:
    Historical resume isolation:
    User has Resume 1 with HTML claim and Resume 2 without HTML claim.
    Scoping to Resume 2 ensures HTML claim from Resume 1 is strictly excluded.
    """
    db = SessionLocal()
    html_skill = db.query(Skill).filter(Skill.slug == "html").first()
    fe_role = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()

    resume_1 = Resume(id=uuid.uuid4(), file_name="res1.pdf", file_type="pdf", file_size=100, storage_path="/r1")
    resume_2 = Resume(id=uuid.uuid4(), file_name="res2.pdf", file_type="pdf", file_size=100, storage_path="/r2")
    db.add_all([resume_1, resume_2])
    db.commit()

    claim_1 = UserClaimedSkill(id=uuid.uuid4(), resume_id=resume_1.id, skill_id=html_skill.id, raw_mention="HTML Expert", confidence_score=1.0)
    db.add(claim_1)
    db.commit()

    try:
        # Request scoped to Resume 2 (which has no HTML)
        res = client.get(
            f"/api/v1/gaps/{fe_role.id}?location=India&include_resume=true&include_github=false&resume_id={resume_2.id}"
        )
        assert res.status_code == 200
        html_item = next(s for s in res.json()["data"]["skills"] if s["canonical_slug"] == "html")
        assert html_item["claimed"] is False
        assert html_item["status"] == "MISSING"
    finally:
        db.delete(claim_1)
        db.delete(resume_1)
        db.delete(resume_2)
        db.commit()
        db.close()


# =============================================================================
# Evidence Audit and Priority Consumption Tests (Tests 9, 10, 15)
# =============================================================================

def test_09_and_15_evidence_audit_contains_github_evidence_and_consistency():
    """
    TEST 9 & TEST 15:
    Evidence Audit for React contains candidate's GitHub evidence when GitHub is the source.
    Demonstrated Skills, Skill Gap, and Evidence Audit agree on the same candidate-owned evidence.
    """
    db = SessionLocal()
    react_skill = db.query(Skill).filter(Skill.slug == "react").first()
    fs_role = db.query(JobRole).filter(JobRole.slug == "full-stack-engineer").first()
    test_user = f"audit-react-{uuid.uuid4().hex[:8]}"

    repo = GitHubRepository(
        id=uuid.uuid4(),
        user_id=None,
        github_repository_id=999888,
        repo_name="my-react-app",
        full_name=f"{test_user}/my-react-app",
        repo_url=f"https://github.com/{test_user}/my-react-app",
        is_fork=False,
    )
    db.add(repo)
    db.commit()

    pe = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=None,
        repo_id=repo.id,
        skill_id=react_skill.id,
        evidence_type="dependency",
        file_path="package.json",
        artifact_name="package.json",
        matched_content="\"react\": \"^18.2.0\"",
        confidence_score=0.95,
    )
    db.add(pe)
    db.commit()

    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=None,
        skill_id=react_skill.id,
        confidence_score=0.95,
        evidence_level="HIGH",
        evidence_count=1,
        repository_count=1,
        skill_metadata={
            "repositories": [
                {
                    "repository_id": str(repo.id),
                    "repo_name": "my-react-app",
                    "full_name": f"{test_user}/my-react-app",
                    "repo_url": f"https://github.com/{test_user}/my-react-app",
                    "max_confidence": 0.95,
                    "evidence_count": 1,
                }
            ],
            "evidence_types": ["dependency"],
        },
    )
    db.add(demo)
    db.commit()

    try:
        # 1. Skill Gap verifies React is STRONG
        gap_res = client.get(
            f"/api/v1/gaps/{fs_role.id}?location=India&include_resume=true&include_github=true&username={test_user}"
        )
        assert gap_res.status_code == 200
        gap_react = next(s for s in gap_res.json()["data"]["skills"] if s["canonical_slug"] == "react")
        assert gap_react["status"] == "STRONG"
        assert gap_react["demonstrated"] is True

        # 2. Evidence Audit retrieves candidate GitHub artifacts
        audit_res = client.get(
            f"/api/v1/gaps/{fs_role.id}/skills/{react_skill.id}/evidence?location=India&include_resume=true&include_github=true&username={test_user}"
        )
        assert audit_res.status_code == 200
        audit_data = audit_res.json()["data"]

        assert audit_data["status"] == "STRONG"
        cand_ev = audit_data["candidate_evidence"]
        assert cand_ev["has_evidence"] is True
        assert cand_ev["github_demonstrated"] is not None
        assert cand_ev["github_demonstrated"]["evidence_level"] == "HIGH"
        assert cand_ev["github_demonstrated"]["confidence_score"] == 0.95

        # Code artifacts are present
        assert len(cand_ev["github_artifacts"]) >= 1
        artifact = cand_ev["github_artifacts"][0]
        assert artifact["repo_name"] == "my-react-app"
        assert artifact["file_path"] == "package.json"
        assert "react" in artifact["matched_content"].lower()

        # Reasoning reflects GitHub HIGH evidence
        assert "Strong because" in audit_data["reasoning"]["classification_reason"]
        assert "verified GitHub code artifacts" in audit_data["reasoning"]["classification_reason"]
        assert "No Evidence" not in audit_data["reasoning"]["classification_reason"]
    finally:
        db.delete(demo)
        db.delete(pe)
        db.delete(repo)
        db.commit()
        db.close()


def test_10_priority_calculation_consumes_strong_classification():
    """
    TEST 10:
    Priority calculation consumes the corrected classification:
    When React is STRONG due to verified GitHub evidence, severity = 0.0,
    priority_score = 0.0, and React is excluded from actionable priorities.
    """
    db = SessionLocal()
    react_skill = db.query(Skill).filter(Skill.slug == "react").first()
    fs_role = db.query(JobRole).filter(JobRole.slug == "full-stack-engineer").first()
    test_user = f"prio-react-{uuid.uuid4().hex[:8]}"

    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=None,
        skill_id=react_skill.id,
        confidence_score=1.0,
        evidence_level="HIGH",
        evidence_count=2,
        repository_count=2,
        skill_metadata={
            "repositories": [
                {
                    "repo_name": "app-one",
                    "repo_url": f"https://github.com/{test_user}/app-one",
                    "max_confidence": 1.0,
                    "evidence_count": 1,
                }
            ]
        },
    )
    db.add(demo)
    db.commit()

    try:
        # Fetch prioritized actionable gaps
        res = client.get(
            f"/api/v1/gaps/{fs_role.id}/priorities?location=India&include_resume=true&include_github=true&username={test_user}"
        )
        assert res.status_code == 200
        prio_data = res.json()["data"]

        # React MUST NOT appear in actionable priorities
        prio_skill_slugs = [g["canonical_slug"] for g in prio_data["gaps"]]
        assert "react" not in prio_skill_slugs
    finally:
        db.delete(demo)
        db.commit()
        db.close()
