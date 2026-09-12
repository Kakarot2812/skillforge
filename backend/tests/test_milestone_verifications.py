"""
Post-MVP Checkpoint P5-B Database Persistence Tests:
Milestone Verifications (Audit History Storage).

Verifies all 17 P5-B requirements:
1. Migration upgrade succeeds
2. Migration downgrade succeeds
3. Migration upgrade can be reapplied cleanly
4. milestone_verifications table exists
5. All required columns exist and have correct types
6. Primary key on 'id' exists
7. Foreign keys exist and point to target tables (milestones, roadmaps, users, repositories)
8. Required indexes exist (single columns and compound milestone_id + created_at)
9. Confidence accepts valid boundary and interior values (0.0, 0.5, 1.0)
10. Confidence rejects values below 0.0 via check constraint
11. Confidence rejects values above 1.0 via check constraint
12. Multiple verification records can exist for the same milestone
13. Historical rows are preserved (no overwrites/upserts)
14. Required NOT NULL fields are enforced
15. JSONB details persists rich structured verification data (matching P5-A structures)
16. Status accepts the four P5 verification states (VERIFIED, PARTIAL, UNVERIFIED, FAILED) and rejects invalid states
17. Downgrade removes table and indexes cleanly
"""

import os
import uuid
import pytest
from datetime import datetime, timezone
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.db.database import SessionLocal, engine
from app.db.models import (
    CandidateRoadmap,
    GitHubRepository,
    JobRole,
    MilestoneVerification,
    RoadmapMilestone,
    Skill,
    User,
)


@pytest.fixture
def alembic_cfg():
    """Alembic configuration referencing the backend alembic.ini."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ini_path = os.path.join(backend_dir, "alembic.ini")
    cfg = Config(ini_path)
    cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
    return cfg


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
def seed_test_hierarchy(db_session):
    """
    Creates the prerequisite relational hierarchy:
    User -> GitHubRepository
    User + JobRole -> CandidateRoadmap
    CandidateRoadmap + Skill -> RoadmapMilestone
    """
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=f"verifier_test_{user_id.hex[:8]}@example.com",
        full_name="Verification Auditor",
    )
    db_session.add(user)

    repo = GitHubRepository(
        id=uuid.uuid4(),
        user_id=user.id,
        repo_name="audit-project",
        full_name=f"test/{user_id.hex[:8]}-audit-project",
        repo_url=f"https://github.com/test/{user_id.hex[:8]}-audit-project",
    )
    db_session.add(repo)

    role = db_session.query(JobRole).first()
    if not role:
        role = JobRole(
            id=uuid.uuid4(),
            title="Backend Systems Engineer",
            slug=f"backend-systems-{uuid.uuid4().hex[:6]}",
            category="Engineering",
        )
        db_session.add(role)

    skill = db_session.query(Skill).first()
    if not skill:
        skill = Skill(
            id=uuid.uuid4(),
            name="Distributed Systems",
            slug=f"dist-sys-{uuid.uuid4().hex[:6]}",
        )
        db_session.add(skill)

    roadmap = CandidateRoadmap(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=role.id,
        target_role_title=role.title,
        status="ACTIVE",
    )
    db_session.add(roadmap)

    milestone = RoadmapMilestone(
        id=uuid.uuid4(),
        roadmap_id=roadmap.id,
        skill_id=skill.id,
        order_index=1,
        status="NOT_STARTED",
        gap_status="MISSING",
        reason="Core competency requirement",
    )
    db_session.add(milestone)
    db_session.commit()

    return {
        "user": user,
        "repo": repo,
        "roadmap": roadmap,
        "milestone": milestone,
    }


# -----------------------------------------------------------------------------
# 1-3. Migration Lifecycle Tests (Upgrade -> Downgrade -> Re-upgrade)
# -----------------------------------------------------------------------------

def test_migration_0018_lifecycle_upgrade_downgrade_reupgrade(alembic_cfg):
    """
    Requirements 1, 2, 3, 17:
    Verify migration upgrade succeeds, downgrade removes objects cleanly,
    and upgrade can be reapplied without error.
    """
    try:
        # 1. Downgrade to 0017
        command.downgrade(alembic_cfg, "0017_roadmap_and_resources")

        # Table must be absent after downgrade
        inspector = inspect(engine)
        assert "milestone_verifications" not in inspector.get_table_names()

        # 2. Upgrade to 0018
        command.upgrade(alembic_cfg, "0018_milestone_verifications")
        inspector = inspect(engine)
        assert "milestone_verifications" in inspector.get_table_names()

        # 3. Clean second downgrade
        command.downgrade(alembic_cfg, "0017_roadmap_and_resources")
        inspector = inspect(engine)
        assert "milestone_verifications" not in inspector.get_table_names()

        # 4. Reapply cleanly
        command.upgrade(alembic_cfg, "0018_milestone_verifications")
        inspector = inspect(engine)
        assert "milestone_verifications" in inspector.get_table_names()
    finally:
        # Restore migration state to current head so database schema matches application models
        command.upgrade(alembic_cfg, "head")


# -----------------------------------------------------------------------------
# 4-8. Schema, Columns, Primary Key, Foreign Keys, Indexes
# -----------------------------------------------------------------------------

def test_table_exists_and_columns_valid():
    """Requirements 4, 5: milestone_verifications exists with required columns."""
    inspector = inspect(engine)
    assert "milestone_verifications" in inspector.get_table_names()

    cols = {c["name"]: c for c in inspector.get_columns("milestone_verifications")}
    expected_columns = {
        "id",
        "milestone_id",
        "roadmap_id",
        "user_id",
        "repository_id",
        "commit_sha",
        "status",
        "confidence",
        "details",
        "created_at",
    }
    assert expected_columns.issubset(set(cols.keys()))

    # Nullability invariants
    assert cols["id"]["nullable"] is False
    assert cols["milestone_id"]["nullable"] is False
    assert cols["roadmap_id"]["nullable"] is False
    assert cols["user_id"]["nullable"] is False
    assert cols["repository_id"]["nullable"] is False
    assert cols["commit_sha"]["nullable"] is False
    assert cols["status"]["nullable"] is False
    assert cols["confidence"]["nullable"] is True
    assert cols["details"]["nullable"] is False
    assert cols["created_at"]["nullable"] is False


def test_primary_key_exists():
    """Requirement 6: Primary key is on 'id'."""
    inspector = inspect(engine)
    pk = inspector.get_pk_constraint("milestone_verifications")
    assert pk["constrained_columns"] == ["id"]


def test_foreign_keys_exist():
    """Requirement 7: Foreign keys to milestone, roadmap, user, repository exist."""
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("milestone_verifications")
    fk_map = {fk["referred_table"]: fk["constrained_columns"] for fk in fks}

    assert "roadmap_milestones" in fk_map
    assert fk_map["roadmap_milestones"] == ["milestone_id"]

    assert "candidate_roadmaps" in fk_map
    assert fk_map["candidate_roadmaps"] == ["roadmap_id"]

    assert "users" in fk_map
    assert fk_map["users"] == ["user_id"]

    assert "github_repositories" in fk_map
    assert fk_map["github_repositories"] == ["repository_id"]


def test_indexes_exist():
    """Requirement 8: Required single and compound indexes exist."""
    inspector = inspect(engine)
    indexes = inspector.get_indexes("milestone_verifications")
    idx_cols = [tuple(idx["column_names"]) for idx in indexes]

    assert ("milestone_id",) in idx_cols
    assert ("roadmap_id",) in idx_cols
    assert ("user_id",) in idx_cols
    assert ("repository_id",) in idx_cols
    assert ("status",) in idx_cols
    assert ("created_at",) in idx_cols
    assert ("milestone_id", "created_at") in idx_cols


# -----------------------------------------------------------------------------
# 9-11. Confidence Boundary and Check Constraint Tests
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("val", [0.0, 0.5, 1.0, None])
def test_confidence_valid_values(db_session, seed_test_hierarchy, val):
    """Requirement 9: Confidence accepts 0.0, 0.5, 1.0 and None."""
    data = seed_test_hierarchy
    row = MilestoneVerification(
        milestone_id=data["milestone"].id,
        roadmap_id=data["roadmap"].id,
        user_id=data["user"].id,
        repository_id=data["repo"].id,
        commit_sha="a" * 40,
        status="VERIFIED",
        confidence=val,
        details={"score": val},
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    assert row.confidence == val


def test_confidence_rejects_negative_value(db_session, seed_test_hierarchy):
    """Requirement 10: Confidence < 0.0 is rejected by check constraint."""
    data = seed_test_hierarchy
    row = MilestoneVerification(
        milestone_id=data["milestone"].id,
        roadmap_id=data["roadmap"].id,
        user_id=data["user"].id,
        repository_id=data["repo"].id,
        commit_sha="a" * 40,
        status="VERIFIED",
        confidence=-0.01,
        details={},
    )
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_confidence_rejects_excessive_value(db_session, seed_test_hierarchy):
    """Requirement 11: Confidence > 1.0 is rejected by check constraint."""
    data = seed_test_hierarchy
    row = MilestoneVerification(
        milestone_id=data["milestone"].id,
        roadmap_id=data["roadmap"].id,
        user_id=data["user"].id,
        repository_id=data["repo"].id,
        commit_sha="a" * 40,
        status="VERIFIED",
        confidence=1.01,
        details={},
    )
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# -----------------------------------------------------------------------------
# 12-13. Multi-attempt History and Preservation Tests
# -----------------------------------------------------------------------------

def test_multiple_verifications_for_same_milestone_allowed(db_session, seed_test_hierarchy):
    """Requirement 12, 13: Multiple verifications for the same milestone are preserved (audit history)."""
    data = seed_test_hierarchy
    m_id = data["milestone"].id

    attempts = [
        ("1" * 40, "UNVERIFIED", 0.2),
        ("2" * 40, "PARTIAL", 0.6),
        ("3" * 40, "VERIFIED", 1.0),
    ]

    for sha, status, conf in attempts:
        record = MilestoneVerification(
            milestone_id=m_id,
            roadmap_id=data["roadmap"].id,
            user_id=data["user"].id,
            repository_id=data["repo"].id,
            commit_sha=sha,
            status=status,
            confidence=conf,
            details={"attempt": sha},
        )
        db_session.add(record)
        db_session.commit()

    rows = (
        db_session.query(MilestoneVerification)
        .filter_by(milestone_id=m_id)
        .order_by(MilestoneVerification.created_at.asc())
        .all()
    )
    assert len(rows) == 3
    assert [r.commit_sha for r in rows] == ["1" * 40, "2" * 40, "3" * 40]
    assert [r.status for r in rows] == ["UNVERIFIED", "PARTIAL", "VERIFIED"]


# -----------------------------------------------------------------------------
# 14. NOT NULL Constraints Enforcement
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("missing_field", [
    "milestone_id",
    "roadmap_id",
    "user_id",
    "repository_id",
    "commit_sha",
    "status",
])
def test_not_null_fields_enforced(db_session, seed_test_hierarchy, missing_field):
    """Requirement 14: Required fields cannot be NULL."""
    data = seed_test_hierarchy
    kwargs = {
        "milestone_id": data["milestone"].id,
        "roadmap_id": data["roadmap"].id,
        "user_id": data["user"].id,
        "repository_id": data["repo"].id,
        "commit_sha": "f" * 40,
        "status": "VERIFIED",
        "confidence": 0.95,
        "details": {},
    }
    kwargs[missing_field] = None

    row = MilestoneVerification(**kwargs)
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# -----------------------------------------------------------------------------
# 15. JSONB Structured Verification Details
# -----------------------------------------------------------------------------

def test_jsonb_details_persistence(db_session, seed_test_hierarchy):
    """
    Requirement 15: JSONB details stores rich deterministic verification audit output
    matching P5-A structures (deliverables, criteria, scores, snippets).
    """
    data = seed_test_hierarchy
    structured_details = {
        "deliverables": {
            "total_required": 2,
            "passed_count": 2,
            "missing_count": 0,
            "ambiguous_count": 0,
            "deliverables_score": 1.0,
            "matches": [
                {"deliverable": "main.py", "status": "PASSED", "matched_path": "main.py"},
                {"deliverable": "Dockerfile", "status": "PASSED", "matched_path": "Dockerfile"},
            ],
        },
        "criteria": {
            "total_criteria": 3,
            "automated_count": 3,
            "passed_count": 3,
            "failed_count": 0,
            "criteria_score": 1.0,
            "results": [
                {
                    "criterion_key": "dockerfile_expose",
                    "status": "PASSED",
                    "matched_file": "Dockerfile",
                    "matched_snippet": "EXPOSE 8000",
                }
            ],
        },
        "deliverables_score": 1.0,
        "criteria_score": 1.0,
        "is_deliverables_satisfied": True,
        "is_criteria_satisfied": True,
        "composite_confidence": 0.95,
    }

    row = MilestoneVerification(
        milestone_id=data["milestone"].id,
        roadmap_id=data["roadmap"].id,
        user_id=data["user"].id,
        repository_id=data["repo"].id,
        commit_sha="c" * 40,
        status="VERIFIED",
        confidence=0.95,
        details=structured_details,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)

    assert row.details["deliverables"]["deliverables_score"] == 1.0
    assert row.details["criteria"]["results"][0]["criterion_key"] == "dockerfile_expose"
    assert row.details["composite_confidence"] == 0.95


# -----------------------------------------------------------------------------
# 16. Status Vocabulary & Check Constraint
# -----------------------------------------------------------------------------

@pytest.mark.parametrize("status_val", ["VERIFIED", "PARTIAL", "UNVERIFIED", "FAILED"])
def test_status_valid_vocabulary(db_session, seed_test_hierarchy, status_val):
    """Requirement 16: Status accepts VERIFIED, PARTIAL, UNVERIFIED, FAILED."""
    data = seed_test_hierarchy
    row = MilestoneVerification(
        milestone_id=data["milestone"].id,
        roadmap_id=data["roadmap"].id,
        user_id=data["user"].id,
        repository_id=data["repo"].id,
        commit_sha="d" * 40,
        status=status_val,
        confidence=0.8,
        details={},
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    assert row.status == status_val


def test_status_rejects_unknown_vocabulary(db_session, seed_test_hierarchy):
    """Requirement 16: Status rejects unknown / arbitrary statuses via check constraint."""
    data = seed_test_hierarchy
    row = MilestoneVerification(
        milestone_id=data["milestone"].id,
        roadmap_id=data["roadmap"].id,
        user_id=data["user"].id,
        repository_id=data["repo"].id,
        commit_sha="e" * 40,
        status="PASS",  # Invalid status (not in ('VERIFIED', 'PARTIAL', 'UNVERIFIED', 'FAILED'))
        confidence=0.8,
        details={},
    )
    db_session.add(row)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
