import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import (
    User,
    Resume,
    JobRole,
    Skill,
    IndustrySkillDemand,
    GitHubRepository,
    ProjectEvidence,
    DemonstratedSkill,
    UserClaimedSkill,
)

client = TestClient(app)


@pytest.fixture
def setup_integration_data():
    """Sets up candidate A and candidate B with repositories and skills for integration testing."""
    db = SessionLocal()

    # 1. Ensure Backend Engineer role and canonical skills exist
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    assert role is not None, "Backend Engineer role must exist"

    fastapi_skill = db.query(Skill).filter(Skill.slug == "fastapi").first()
    assert fastapi_skill is not None, "FastAPI skill must exist"

    python_skill = db.query(Skill).filter(Skill.slug == "python").first()
    assert python_skill is not None, "Python skill must exist"

    # 2. Create distinct Candidate A and Candidate B
    cand_a_id = uuid.uuid4()
    cand_b_id = uuid.uuid4()

    user_a = User(
        id=cand_a_id,
        email=f"candidate_a_{cand_a_id.hex[:8]}@example.com",
    )
    user_b = User(
        id=cand_b_id,
        email=f"candidate_b_{cand_b_id.hex[:8]}@example.com",
    )
    db.add_all([user_a, user_b])
    db.commit()

    # 3. Create candidate A repository: mukul-00/upload-and-feed-FastApi-project
    repo_a = GitHubRepository(
        id=uuid.uuid4(),
        user_id=cand_a_id,
        repo_name="upload-and-feed-FastApi-project",
        full_name="mukul-00/upload-and-feed-FastApi-project",
        repo_url="https://github.com/mukul-00/upload-and-feed-FastApi-project",
        is_fork=False,
    )
    db.add(repo_a)
    db.commit()

    # 4. Create ProjectEvidence for Candidate A
    pe1 = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=cand_a_id,
        repo_id=repo_a.id,
        skill_id=fastapi_skill.id,
        evidence_type="dependency",
        file_path="pyproject.toml",
        artifact_name="pyproject.toml",
        matched_content="fastapi>=0.136.3",
        confidence_score=0.95,
    )
    pe2 = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=cand_a_id,
        repo_id=repo_a.id,
        skill_id=fastapi_skill.id,
        evidence_type="dependency",
        file_path="requirements.txt",
        artifact_name="requirements.txt",
        matched_content="fastapi==0.138.0",
        confidence_score=0.95,
    )
    pe3 = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=cand_a_id,
        repo_id=repo_a.id,
        skill_id=python_skill.id,
        evidence_type="repository_structure",
        file_path="main.py",
        confidence_score=0.70,
    )
    db.add_all([pe1, pe2, pe3])
    db.commit()

    # 5. Create DemonstratedSkill aggregated for Candidate A
    ds_fastapi = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=cand_a_id,
        skill_id=fastapi_skill.id,
        confidence_score=0.95,
        evidence_level="HIGH",
        evidence_count=2,
        repository_count=1,
        skill_metadata={
            "repositories": [
                {
                    "owner": "mukul-00",
                    "repo_name": "upload-and-feed-FastApi-project",
                    "full_name": "mukul-00/upload-and-feed-FastApi-project",
                    "repo_url": "https://github.com/mukul-00/upload-and-feed-FastApi-project",
                    "max_confidence": 0.95,
                    "evidence_count": 2,
                }
            ],
            "evidence_types": ["dependency"],
        },
    )
    ds_python = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=cand_a_id,
        skill_id=python_skill.id,
        confidence_score=0.70,
        evidence_level="MEDIUM",
        evidence_count=1,
        repository_count=1,
        skill_metadata={
            "repositories": [
                {
                    "owner": "mukul-00",
                    "repo_name": "upload-and-feed-FastApi-project",
                    "full_name": "mukul-00/upload-and-feed-FastApi-project",
                    "repo_url": "https://github.com/mukul-00/upload-and-feed-FastApi-project",
                    "max_confidence": 0.70,
                    "evidence_count": 1,
                }
            ],
            "evidence_types": ["repository_structure"],
        },
    )
    db.add_all([ds_fastapi, ds_python])
    db.commit()

    # 6. Candidate A resume claiming Python (0.80)
    resume_a = Resume(
        id=uuid.uuid4(),
        user_id=cand_a_id,
        file_name="resume_a.pdf",
        file_type="application/pdf",
        file_size=1024,
        storage_path="/resumes/resume_a.pdf",
        raw_text="Experienced in Python backend development",
    )
    db.add(resume_a)
    db.commit()

    claim_python = UserClaimedSkill(
        id=uuid.uuid4(),
        user_id=cand_a_id,
        resume_id=resume_a.id,
        skill_id=python_skill.id,
        confidence_score=0.80,
    )
    db.add(claim_python)
    db.commit()

    data = {
        "role_id": str(role.id),
        "cand_a_id": str(cand_a_id),
        "cand_b_id": str(cand_b_id),
        "fastapi_skill_id": str(fastapi_skill.id),
        "python_skill_id": str(python_skill.id),
        "resume_a_id": str(resume_a.id),
    }

    db.close()
    yield data

    # Cleanup
    db = SessionLocal()
    db.query(ProjectEvidence).filter(ProjectEvidence.user_id.in_([cand_a_id, cand_b_id])).delete(synchronize_session=False)
    db.query(DemonstratedSkill).filter(DemonstratedSkill.user_id.in_([cand_a_id, cand_b_id])).delete(synchronize_session=False)
    db.query(UserClaimedSkill).filter(UserClaimedSkill.user_id.in_([cand_a_id, cand_b_id])).delete(synchronize_session=False)
    db.query(Resume).filter(Resume.user_id.in_([cand_a_id, cand_b_id])).delete(synchronize_session=False)
    db.query(GitHubRepository).filter(GitHubRepository.user_id.in_([cand_a_id, cand_b_id])).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_([cand_a_id, cand_b_id])).delete(synchronize_session=False)
    db.commit()
    db.close()


def test_01_candidate_scoped_demonstrated_evidence(setup_integration_data):
    """TEST 1: Demonstrated skills endpoint returns candidate-scoped demonstrated skills."""
    d = setup_integration_data
    res = client.get(
        "/api/v1/skills/demonstrated",
        headers={"X-User-Id": d["cand_a_id"]},
    )
    assert res.status_code == 200
    skills = {s["skill_name"]: s for s in res.json()["data"]}
    assert "FastAPI" in skills
    assert skills["FastAPI"]["confidence_score"] == 0.95
    assert skills["FastAPI"]["evidence_level"] == "HIGH"
    assert "Python" in skills
    assert skills["Python"]["confidence_score"] == 0.70
    assert skills["Python"]["evidence_level"] == "MEDIUM"


def test_02_skill_gap_calculation_sees_new_github_evidence(setup_integration_data):
    """TEST 2: Skill gap calculation for Candidate A reads newly analyzed GitHub evidence."""
    d = setup_integration_data
    res = client.get(
        f"/api/v1/gaps/{d['role_id']}?location=India&include_resume=true&include_github=true&username=mukul-00&resume_id={d['resume_a_id']}",
        headers={"X-User-Id": d["cand_a_id"]},
    )
    assert res.status_code == 200
    json_data = res.json()["data"]
    skills = {s["skill_name"]: s for s in json_data["skills"]}

    # FastAPI must be classified as STRONG because demonstrated_score 0.95 >= 0.85
    assert "FastAPI" in skills
    fastapi = skills["FastAPI"]
    assert fastapi["status"] == "STRONG"
    assert fastapi["demonstrated"] is True
    assert fastapi["demonstrated_score"] == 0.95
    assert fastapi["evidence_level"] == "HIGH"
    assert fastapi["evidence_count"] == 2
    assert fastapi["priority_score"] == 0.0

    # Python must be classified as PARTIAL (0.70 < 0.85, claimed + demonstrated)
    assert "Python" in skills
    python = skills["Python"]
    assert python["status"] == "PARTIAL"
    assert python["claimed"] is True
    assert python["demonstrated"] is True
    assert python["demonstrated_score"] == 0.70
    assert python["evidence_level"] == "MEDIUM"

    # Summary: strong_count should be at least 1
    summary = json_data["summary"]
    assert summary["strong_count"] >= 1


def test_03_prioritized_gaps_excludes_strong_fastapi(setup_integration_data):
    """TEST 3: Prioritized gaps excludes STRONG skills (FastAPI) and retains actionable gaps (Python)."""
    d = setup_integration_data
    res = client.get(
        f"/api/v1/gaps/{d['role_id']}/priorities?location=India&include_resume=true&include_github=true&username=mukul-00&resume_id={d['resume_a_id']}",
        headers={"X-User-Id": d["cand_a_id"]},
    )
    assert res.status_code == 200
    prio_gaps = res.json()["data"]["gaps"]
    gap_names = [g["skill_name"] for g in prio_gaps]

    # FastAPI is STRONG -> strictly excluded from actionable gaps
    assert "FastAPI" not in gap_names

    # Python is PARTIAL -> retained in actionable gaps
    assert "Python" in gap_names


def test_04_fastapi_audit_evidence_chain(setup_integration_data):
    """TEST 4: Skill gap evidence audit returns verified GitHub artifacts and deterministic reasoning."""
    d = setup_integration_data
    res = client.get(
        f"/api/v1/gaps/{d['role_id']}/skills/{d['fastapi_skill_id']}/evidence?location=India&include_resume=true&include_github=true&username=mukul-00&resume_id={d['resume_a_id']}",
        headers={"X-User-Id": d["cand_a_id"]},
    )
    assert res.status_code == 200
    ev = res.json()["data"]
    assert ev["status"] == "STRONG"
    candidate_ev = ev["candidate_evidence"]
    assert candidate_ev["has_evidence"] is True
    assert candidate_ev["github_demonstrated"]["confidence_score"] == 0.95
    assert candidate_ev["github_demonstrated"]["evidence_level"] == "HIGH"
    assert len(candidate_ev["github_artifacts"]) == 2
    assert "Strong because verified GitHub code artifacts demonstrate this skill" in ev["reasoning"]["classification_reason"]


def test_05_candidate_isolation_no_leakage(setup_integration_data):
    """TEST 5: Candidate B cannot see Candidate A's demonstrated evidence or strong gap status."""
    d = setup_integration_data

    # Candidate B checks demonstrated skills
    res_demo = client.get(
        "/api/v1/skills/demonstrated",
        headers={"X-User-Id": d["cand_b_id"]},
    )
    assert res_demo.status_code == 200
    assert len(res_demo.json()["data"]) == 0

    # Candidate B checks skill gaps
    res_gaps = client.get(
        f"/api/v1/gaps/{d['role_id']}?location=India&include_resume=false&include_github=true",
        headers={"X-User-Id": d["cand_b_id"]},
    )
    assert res_gaps.status_code == 200
    b_skills = {s["skill_name"]: s for s in res_gaps.json()["data"]["skills"]}
    assert b_skills["FastAPI"]["status"] == "MISSING"
    assert b_skills["FastAPI"]["demonstrated"] is False
    assert b_skills["FastAPI"]["demonstrated_score"] == 0.0
    assert res_gaps.json()["data"]["summary"]["strong_count"] == 0
