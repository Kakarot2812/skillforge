"""
Deterministic Unit and Integration Tests for Checkpoint P5-C:
VerificationService Orchestration.

Tests all 24 required behaviors:
1. successful VERIFIED flow
2. PARTIAL flow
3. UNVERIFIED flow
4. FAILED external/infrastructure flow
5. composite score calculation
6. zero-deliverable behavior
7. zero-automated-criteria behavior
8. manual criteria excluded from S_crit
9. milestone VERIFIED transition
10. PARTIAL/UNVERIFIED milestone remains IN_PROGRESS
11. previous verification history is preserved
12. commit SHA is persisted
13. MilestoneVerification details are bounded/structured
14. repository ownership rejection
15. fork rejection
16. roadmap ownership rejection
17. milestone/roadmap mismatch rejection
18. cross-candidate repository rejection
19. PAT never persisted/logged/returned
20. demonstrated-skill recomputation uses existing deterministic logic
21. ProjectVerifier is called rather than duplicated
22. GitHub refresh failure becomes FAILED
23. candidate verification failure does not become FAILED
24. no unrelated roadmap milestones are modified
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    ApprovedProject,
    CandidateRoadmap,
    DemonstratedSkill,
    GitHubRepository,
    JobRole,
    MilestoneVerification,
    ProjectEvidence,
    RoadmapMilestone,
    Skill,
    User,
)
from app.services.demonstrated_skill_service import demonstrated_skill_service
from app.services.project_verifier import compute_composite_confidence, project_verifier
from app.services.verification_service import (
    ForkedRepositoryError,
    MilestoneRoadmapMismatchError,
    RepositoryOwnershipError,
    RoadmapOwnershipError,
    VerificationInfrastructureError,
    VerificationNotFoundError,
    VerificationServiceResult,
    verification_service,
)


@pytest.fixture
def db_session():
    """Provides a transactional database session rolled back after tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def seed_data(db_session: Session):
    """Seed comprehensive test data for candidate, repos, roadmap, and milestone."""
    # 1. Users
    user_id = uuid.uuid4()
    candidate = User(
        id=user_id,
        email=f"candidate_{user_id.hex[:6]}@example.com",
        full_name="Candidate Ada",
    )
    db_session.add(candidate)

    other_user_id = uuid.uuid4()
    other_user = User(
        id=other_user_id,
        email=f"other_{other_user_id.hex[:6]}@example.com",
        full_name="Candidate Charles",
    )
    db_session.add(other_user)

    # 2. Skills & Role
    skill = db_session.query(Skill).filter(Skill.slug == "fastapi").first()
    if not skill:
        skill = Skill(id=uuid.uuid4(), name="FastAPI", slug=f"fastapi-{uuid.uuid4().hex[:4]}")
        db_session.add(skill)

    skill2 = db_session.query(Skill).filter(Skill.slug == "docker").first()
    if not skill2:
        skill2 = Skill(id=uuid.uuid4(), name="Docker", slug=f"docker-{uuid.uuid4().hex[:4]}")
        db_session.add(skill2)

    role = db_session.query(JobRole).first()
    if not role:
        role = JobRole(id=uuid.uuid4(), title="Backend Engineer", slug=f"backend-{uuid.uuid4().hex[:4]}")
        db_session.add(role)

    # 3. Approved Project with seeded 24 criteria: pydantic_v2_models and explicit_workdir
    project = ApprovedProject(
        id=uuid.uuid4(),
        skill_id=skill.id,
        role_id=role.id,
        title="Production FastAPI Microservice",
        description="Build a production-grade FastAPI microservice.",
        difficulty="INTERMEDIATE",
        deliverables=["main.py", "Dockerfile"],
        verification_criteria=["pydantic_v2_models", "explicit_workdir"],
        estimated_hours=8,
    )
    db_session.add(project)

    # 4. Repositories
    repo = GitHubRepository(
        id=uuid.uuid4(),
        user_id=candidate.id,
        repo_name="fastapi-app",
        full_name="candidate-ada/fastapi-app",
        repo_url="https://github.com/candidate-ada/fastapi-app",
        default_branch="main",
        is_fork=False,
        repo_metadata={"owner": "candidate-ada", "commit_sha": "a1b2c3d4e5f67890123456789abcdef012345678"},
    )
    db_session.add(repo)

    other_repo = GitHubRepository(
        id=uuid.uuid4(),
        user_id=other_user.id,
        repo_name="other-app",
        full_name="charles/other-app",
        repo_url="https://github.com/charles/other-app",
        default_branch="main",
        is_fork=False,
        repo_metadata={"owner": "charles"},
    )
    db_session.add(other_repo)

    forked_repo = GitHubRepository(
        id=uuid.uuid4(),
        user_id=candidate.id,
        repo_name="forked-app",
        full_name="candidate-ada/forked-app",
        repo_url="https://github.com/candidate-ada/forked-app",
        default_branch="main",
        is_fork=True,
        repo_metadata={"owner": "candidate-ada"},
    )
    db_session.add(forked_repo)

    # 5. Roadmaps
    roadmap = CandidateRoadmap(
        id=uuid.uuid4(),
        user_id=candidate.id,
        role_id=role.id,
        target_role_title=role.title,
        status="ACTIVE",
    )
    db_session.add(roadmap)

    other_roadmap = CandidateRoadmap(
        id=uuid.uuid4(),
        user_id=other_user.id,
        role_id=role.id,
        target_role_title=role.title,
        status="ACTIVE",
    )
    db_session.add(other_roadmap)

    # 6. Milestones (different skills to respect uq_roadmap_milestones_skill)
    m1 = RoadmapMilestone(
        id=uuid.uuid4(),
        roadmap_id=roadmap.id,
        skill_id=skill.id,
        order_index=1,
        status="NOT_STARTED",
        gap_status="MISSING",
        reason="Primary backend skill",
        project_id=project.id,
    )
    db_session.add(m1)

    m2_unrelated = RoadmapMilestone(
        id=uuid.uuid4(),
        roadmap_id=roadmap.id,
        skill_id=skill2.id,
        order_index=2,
        status="NOT_STARTED",
        gap_status="MISSING",
        reason="Secondary milestone",
    )
    db_session.add(m2_unrelated)

    # 7. Project Evidence for high demonstrated skill score
    evidence = ProjectEvidence(
        id=uuid.uuid4(),
        user_id=candidate.id,
        repo_id=repo.id,
        skill_id=skill.id,
        evidence_type="dependency",
        file_path="requirements.txt",
        artifact_name="requirements.txt",
        evidence_description="FastAPI dependency declared",
        confidence_score=0.90,
    )
    db_session.add(evidence)

    db_session.commit()

    return {
        "candidate": candidate,
        "other_user": other_user,
        "repo": repo,
        "other_repo": other_repo,
        "forked_repo": forked_repo,
        "roadmap": roadmap,
        "other_roadmap": other_roadmap,
        "milestone": m1,
        "unrelated_milestone": m2_unrelated,
        "project": project,
        "skill": skill,
        "skill2": skill2,
    }


# Helper mock tree and files
MOCK_TREE_VERIFIED = [
    {"path": "main.py", "type": "blob", "size": 120},
    {"path": "Dockerfile", "type": "blob", "size": 150},
]
MOCK_FILES_VERIFIED = {
    "main.py": "from pydantic import BaseModel, ConfigDict\n\nclass Item(BaseModel):\n    name: str\n    model_config = ConfigDict(frozen=True)\n",
    "Dockerfile": "FROM python:3.12-slim\nWORKDIR /app\nCMD ['uvicorn', 'main:app']\n",
}


# -----------------------------------------------------------------------------
# 1. Successful VERIFIED flow
# -----------------------------------------------------------------------------

def test_01_successful_verified_flow(db_session, seed_data):
    """
    Requirement 1, 9:
    All deliverables found, criteria >= 0.80, demonstrated skill >= 0.70, composite >= 0.85.
    Verification status becomes VERIFIED. Milestone status becomes VERIFIED.
    """
    d = seed_data
    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        result = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert result.status == "VERIFIED"
        assert result.confidence is not None
        assert result.confidence >= 0.85
        assert result.milestone_status == "VERIFIED"

        # Check DB milestone state
        refreshed_m = db_session.query(RoadmapMilestone).filter_by(id=d["milestone"].id).first()
        assert refreshed_m.status == "VERIFIED"


# -----------------------------------------------------------------------------
# 2. PARTIAL flow
# -----------------------------------------------------------------------------

def test_02_partial_flow(db_session, seed_data):
    """
    Requirement 2, 10:
    Deliverables found (score 1.0 >= 0.50), but criteria fail.
    Becomes PARTIAL, milestone transitions from NOT_STARTED to IN_PROGRESS.
    """
    d = seed_data
    mock_files_failing_crit = {
        "main.py": "# empty python code\n",
        "Dockerfile": "FROM alpine\n# no expose or workdir\n",
    }

    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: mock_files_failing_crit.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        result = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert result.status == "PARTIAL"
        assert result.milestone_status == "IN_PROGRESS"
        refreshed_m = db_session.query(RoadmapMilestone).filter_by(id=d["milestone"].id).first()
        assert refreshed_m.status == "IN_PROGRESS"


# -----------------------------------------------------------------------------
# 3. UNVERIFIED flow
# -----------------------------------------------------------------------------

def test_03_unverified_flow(db_session, seed_data):
    """
    Requirement 3:
    Zero deliverables found (0.0), zero criteria passed (0.0), zero skill (0.0) -> UNVERIFIED.
    Milestone transitions to IN_PROGRESS.
    """
    d = seed_data
    # Delete evidence to make demonstrated skill score 0.0
    db_session.query(ProjectEvidence).filter_by(user_id=d["candidate"].id).delete()
    db_session.query(DemonstratedSkill).filter_by(user_id=d["candidate"].id).delete()
    db_session.commit()

    empty_tree = [{"path": "unrelated.txt", "type": "blob", "size": 10}]

    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=empty_tree), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", return_value=None), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        result = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert result.status == "UNVERIFIED"
        assert result.milestone_status == "IN_PROGRESS"


# -----------------------------------------------------------------------------
# 4. FAILED external / infrastructure flow
# -----------------------------------------------------------------------------

def test_04_failed_infrastructure_flow(db_session, seed_data):
    """
    Requirement 4, 22:
    GitHub API failure (e.g. 504 gateway timeout) results in FAILED status.
    Milestone status is preserved (NOT_STARTED remains NOT_STARTED).
    """
    d = seed_data
    assert d["milestone"].status == "NOT_STARTED"

    with patch("app.services.verification_service.github_analyzer.analyze_repository", side_effect=HTTPException(status_code=504, detail="GitHub API gateway timeout.")):
        result = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert result.status == "FAILED"
        assert result.confidence is None
        assert result.details["failure_type"] == "infrastructure_failure"
        assert "timeout" in result.details["error"].lower()

        # Milestone status is preserved without being falsely marked completed or failed
        assert result.milestone_status == "NOT_STARTED"
        refreshed_m = db_session.query(RoadmapMilestone).filter_by(id=d["milestone"].id).first()
        assert refreshed_m.status == "NOT_STARTED"


# -----------------------------------------------------------------------------
# 5. Composite score calculation
# -----------------------------------------------------------------------------

def test_05_composite_score_calculation():
    """
    Requirement 5:
    C = 0.35 * S_deliv + 0.40 * S_crit + 0.25 * S_skill (rounded to 2 decimal places).
    """
    # Case 1: All 1.0 -> 1.0
    assert compute_composite_confidence(1.0, 1.0, 1.0) == 1.0

    # Case 2: S_deliv=1.0, S_crit=0.50, S_skill=0.60
    # 0.35(1.0) + 0.40(0.50) + 0.25(0.60) = 0.35 + 0.20 + 0.15 = 0.70
    assert compute_composite_confidence(1.0, 0.50, 0.60) == 0.70

    # Case 3: S_deliv=0.0, S_crit=0.50, S_skill=0.0
    # 0.35(0) + 0.40(0.50) + 0 = 0.20
    assert compute_composite_confidence(0.0, 0.50, 0.0) == 0.20

    # Case 4: Clamping check
    assert compute_composite_confidence(-0.5, 1.5, 0.5) == compute_composite_confidence(0.0, 1.0, 0.5)


# -----------------------------------------------------------------------------
# 6. Zero deliverable behavior
# -----------------------------------------------------------------------------

def test_06_zero_deliverables_behavior(db_session, seed_data):
    """
    Requirement 6:
    If a project defines zero required deliverables, S_deliv = 1.0.
    """
    d = seed_data
    # Clear deliverables on project
    d["project"].deliverables = []
    db_session.commit()

    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        result = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert result.details["scores"]["deliverables_score"] == 1.0
        assert result.details["deliverables"]["total_required"] == 0


# -----------------------------------------------------------------------------
# 7. Zero automated criteria behavior
# -----------------------------------------------------------------------------

def test_07_zero_automated_criteria_behavior(db_session, seed_data):
    """
    Requirement 7:
    If a project defines zero automated criteria, S_crit = 1.0.
    """
    d = seed_data
    d["project"].verification_criteria = []
    db_session.commit()

    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        result = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert result.details["scores"]["criteria_score"] == 1.0
        assert result.details["criteria"]["automated_count"] == 0


# -----------------------------------------------------------------------------
# 8. Manual criteria excluded from S_crit
# -----------------------------------------------------------------------------

def test_08_manual_criteria_excluded_from_s_crit(db_session, seed_data):
    """
    Requirement 8:
    Manual-review criteria are recorded under manual_review_criteria and excluded from S_crit denominator.
    """
    d = seed_data
    d["project"].verification_criteria = ["explicit_workdir", "manual_code_review_style"]
    db_session.commit()

    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        result = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        crit_details = result.details["criteria"]
        assert crit_details["total_criteria"] == 2
        assert crit_details["automated_count"] == 1
        assert crit_details["manual_review_count"] == 1
        # Passed 1 of 1 automated -> criteria score is 1.0
        assert crit_details["criteria_score"] == 1.0


# -----------------------------------------------------------------------------
# 9-10. Milestone status transitions
# -----------------------------------------------------------------------------

def test_09_10_milestone_transitions(db_session, seed_data):
    """
    Requirement 9, 10:
    VERIFIED sets milestone status to VERIFIED.
    PARTIAL / UNVERIFIED from NOT_STARTED sets milestone to IN_PROGRESS.
    """
    d = seed_data
    # Initially NOT_STARTED
    assert d["milestone"].status == "NOT_STARTED"

    # 1. Partial test
    mock_files_failing_crit = {"main.py": "x = 1", "Dockerfile": "FROM alpine"}
    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: mock_files_failing_crit.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        res_partial = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )
        assert res_partial.status == "PARTIAL"
        assert res_partial.milestone_status == "IN_PROGRESS"

    # 2. Now verify fully -> transitions to VERIFIED
    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        res_verified = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )
        assert res_verified.status == "VERIFIED"
        assert res_verified.milestone_status == "VERIFIED"


# -----------------------------------------------------------------------------
# 11. Previous verification history is preserved
# -----------------------------------------------------------------------------

def test_11_previous_verification_history_preserved(db_session, seed_data):
    """
    Requirement 11:
    Multiple verification attempts for the same milestone append historical records.
    """
    d = seed_data
    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        res1 = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        res2 = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        records = (
            db_session.query(MilestoneVerification)
            .filter_by(milestone_id=d["milestone"].id)
            .order_by(MilestoneVerification.created_at.asc())
            .all()
        )
        assert len(records) == 2
        assert records[0].id == res1.id
        assert records[1].id == res2.id


# -----------------------------------------------------------------------------
# 12. Commit SHA is persisted
# -----------------------------------------------------------------------------

def test_12_commit_sha_persisted(db_session, seed_data):
    """
    Requirement 12:
    Commit SHA used for verification is written to milestone_verifications.commit_sha.
    """
    d = seed_data
    expected_sha = "f00b4r1234567890abcdef1234567890abcdef12"

    with patch.object(verification_service, "_resolve_commit_sha", return_value=expected_sha), \
         patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        res = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert res.commit_sha == expected_sha
        row = db_session.query(MilestoneVerification).filter_by(id=res.id).first()
        assert row.commit_sha == expected_sha


# -----------------------------------------------------------------------------
# 13. Details are bounded and structured
# -----------------------------------------------------------------------------

def test_13_details_bounded_and_structured(db_session, seed_data):
    """
    Requirement 13:
    Details dictionary contains structured sections (deliverables, criteria, scores)
    and does not dump full source files.
    """
    d = seed_data
    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        res = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        details = res.details
        assert "deliverables" in details
        assert "criteria" in details
        assert "scores" in details
        assert "evaluation" in details
        assert "commit_sha" in details

        # Verify snippets are bounded
        for result in details["criteria"]["results"]:
            if result["matched_snippet"]:
                assert len(result["matched_snippet"]) <= 256


# -----------------------------------------------------------------------------
# 14-18. Security & Ownership Rejections
# -----------------------------------------------------------------------------

def test_14_repository_ownership_username_mismatch_rejected(db_session, seed_data):
    """Requirement 14: Connected GitHub username mismatch is rejected."""
    d = seed_data
    with pytest.raises(RepositoryOwnershipError):
        verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="malicious-impersonator",
        )


def test_15_fork_rejection(db_session, seed_data):
    """Requirement 15: Forked repositories are rejected."""
    d = seed_data
    with pytest.raises(ForkedRepositoryError):
        verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["forked_repo"].id,
        )


def test_16_roadmap_ownership_rejection(db_session, seed_data):
    """Requirement 16: Roadmap belonging to another user is rejected."""
    d = seed_data
    with pytest.raises(RoadmapOwnershipError):
        verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["other_roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
        )


def test_17_milestone_roadmap_mismatch_rejection(db_session, seed_data):
    """Requirement 17: Milestone not belonging to specified roadmap is rejected."""
    d = seed_data
    with pytest.raises(MilestoneRoadmapMismatchError):
        verification_service.verify_milestone(
            db=db_session,
            user_id=d["other_user"].id,
            roadmap_id=d["other_roadmap"].id,
            milestone_id=d["milestone"].id,  # belongs to d["roadmap"]
            repository_id=d["other_repo"].id,
        )


def test_18_cross_candidate_repository_rejection(db_session, seed_data):
    """Requirement 18: Repository owned by another user is rejected."""
    d = seed_data
    with pytest.raises(RepositoryOwnershipError):
        verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["other_repo"].id,  # owned by other_user
        )


# -----------------------------------------------------------------------------
# 19. PAT never persisted, logged, or returned
# -----------------------------------------------------------------------------

def test_19_pat_never_persisted_or_returned(db_session, seed_data):
    """
    Requirement 19:
    A sensitive PAT passed to verify_milestone is never persisted in DB details or returned.
    """
    d = seed_data
    secret_pat = "ghp_SECRET_TOKEN_999888777"

    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        res = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            token=secret_pat,
            github_username="candidate-ada",
        )

        # Check in memory result
        res_str = str(res.model_dump())
        assert secret_pat not in res_str

        # Check DB row
        row = db_session.query(MilestoneVerification).filter_by(id=res.id).first()
        db_details_str = str(row.details)
        assert secret_pat not in db_details_str


# -----------------------------------------------------------------------------
# 20. Demonstrated-skill recomputation uses existing deterministic logic
# -----------------------------------------------------------------------------

def test_20_demonstrated_skill_recomputation(db_session, seed_data):
    """
    Requirement 20:
    Demonstrated skill recomputation is executed via existing DemonstratedSkillService.
    """
    d = seed_data
    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())), \
         patch.object(demonstrated_skill_service, "recompute_demonstrated_skill", wraps=demonstrated_skill_service.recompute_demonstrated_skill) as mock_skill_srv:

        # Use actual demonstrated_skill_service
        res = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert mock_skill_srv.called
        demo_skill = db_session.query(DemonstratedSkill).filter_by(user_id=d["candidate"].id, skill_id=d["skill"].id).first()
        assert demo_skill is not None
        assert demo_skill.confidence_score >= 0.70


# -----------------------------------------------------------------------------
# 21. ProjectVerifier is called rather than duplicated
# -----------------------------------------------------------------------------

def test_21_project_verifier_called(db_session, seed_data):
    """
    Requirement 21:
    ProjectVerifier.verify is invoked by VerificationService.
    """
    d = seed_data
    with patch.object(project_verifier, "verify", wraps=project_verifier.verify) as mock_pv_verify, \
         patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert mock_pv_verify.called
        assert mock_pv_verify.call_count == 1


# -----------------------------------------------------------------------------
# 22-23. Candidate failure vs Infrastructure failure distinction
# -----------------------------------------------------------------------------

def test_22_23_candidate_failure_does_not_become_failed_status(db_session, seed_data):
    """
    Requirement 22, 23:
    Candidate failing criteria/deliverables produces PARTIAL or UNVERIFIED, NEVER FAILED.
    FAILED is reserved strictly for infrastructure/external failures.
    """
    d = seed_data
    # Empty repo tree -> candidate fails project
    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=[]), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", return_value=None), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        res = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )

        assert res.status in ("PARTIAL", "UNVERIFIED")
        assert res.status != "FAILED"


# -----------------------------------------------------------------------------
# 24. No unrelated roadmap milestones are modified
# -----------------------------------------------------------------------------

def test_24_no_unrelated_milestones_modified(db_session, seed_data):
    """
    Requirement 24:
    Verifying milestone 1 leaves milestone 2 completely untouched in NOT_STARTED state.
    """
    d = seed_data
    assert d["unrelated_milestone"].status == "NOT_STARTED"

    with patch("app.services.verification_service.github_analyzer.fetch_repo_tree", return_value=MOCK_TREE_VERIFIED), \
         patch("app.services.verification_service.github_analyzer.fetch_file_content", side_effect=lambda fn, p, token=None: MOCK_FILES_VERIFIED.get(p)), \
         patch("app.services.verification_service.github_analyzer.analyze_repository", return_value=([], set())):

        res = verification_service.verify_milestone(
            db=db_session,
            user_id=d["candidate"].id,
            roadmap_id=d["roadmap"].id,
            milestone_id=d["milestone"].id,
            repository_id=d["repo"].id,
            github_username="candidate-ada",
        )
        assert res.status == "VERIFIED"

        refreshed_m2 = db_session.query(RoadmapMilestone).filter_by(id=d["unrelated_milestone"].id).first()
        assert refreshed_m2.status == "NOT_STARTED"
