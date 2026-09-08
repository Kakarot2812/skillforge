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
from app.services.skill_gap_service import (
    skill_gap_service,
    classify_skill_gap,
    STRONG_DEMONSTRATED_THRESHOLD,
    STATUS_SORT_RANK,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1-4: Foundation & Role Lookup Tests
# -----------------------------------------------------------------------------

def test_valid_role_gap_analysis():
    """1. Valid role lookup returns complete skill gap analysis with summary."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    db.close()

    res = client.get(f"/api/v1/gaps/{role.id}")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "meta" in body
    data = body["data"]
    assert data["role"]["slug"] == "backend-engineer"
    assert data["location"] == "India"
    assert "summary" in data
    assert data["summary"]["total_required_skills"] == 13
    assert len(data["skills"]) == 13


def test_nonexistent_role_returns_404():
    """2. Nonexistent role returns structured 404 NOT_FOUND."""
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/gaps/{fake_id}")
    assert res.status_code == 404
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"


def test_malformed_role_uuid_returns_422():
    """3. Malformed role UUID returns 422 VALIDATION_ERROR."""
    res = client.get("/api/v1/gaps/not-a-valid-uuid")
    assert res.status_code == 422
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_post_analyze_valid_role():
    """4. POST /api/v1/gaps/analyze executes gap analysis correctly."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "ai-ml-engineer").first()
    db.close()

    payload = {"target_role_id": str(role.id), "location": "India"}
    res = client.post("/api/v1/gaps/analyze", json=payload)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["role"]["slug"] == "ai-ml-engineer"
    assert data["summary"]["total_required_skills"] == 8


# -----------------------------------------------------------------------------
# 5-9: Skill State & Evidence Synthesis Tests
# -----------------------------------------------------------------------------

def test_no_claims_no_evidence_is_missing():
    """5. When candidate has no resume claims and no GitHub evidence, skills are MISSING."""
    db = SessionLocal()
    user = User(email=f"blank-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["summary"]["missing_count"] == 13
        assert data["summary"]["strong_count"] == 0
        assert data["summary"]["partial_count"] == 0
        for sk in data["skills"]:
            assert sk["status"] == "MISSING"
            assert sk["claimed"] is False
            assert sk["demonstrated"] is False
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            db.delete(u)
            db.commit()
        db.close()


def test_resume_claim_only_is_partial():
    """6. Candidate with resume claim but no GitHub code evidence is PARTIAL."""
    db = SessionLocal()
    user = User(email=f"claimed-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()

    skill = db.query(Skill).filter(Skill.slug == "python").first()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id

    claimed = UserClaimedSkill(
        id=uuid.uuid4(),
        user_id=user.id,
        skill_id=skill.id,
        raw_mention="Python 3.12",
        confidence_score=1.0,
    )
    db.add(claimed)
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}")
        assert res.status_code == 200
        data = res.json()["data"]
        python_item = next(s for s in data["skills"] if s["canonical_slug"] == "python")
        assert python_item["status"] == "PARTIAL"
        assert python_item["claimed"] is True
        assert python_item["claim_confidence"] == 1.0
        assert python_item["demonstrated"] is False
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            db.delete(u)
            db.commit()
        db.close()


def test_github_high_demonstrated_is_strong():
    """7. Candidate with high GitHub demonstrated score (>= 0.85) is STRONG."""
    db = SessionLocal()
    user = User(email=f"demo-high-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()

    skill = db.query(Skill).filter(Skill.slug == "fastapi").first()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id

    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=user.id,
        skill_id=skill.id,
        confidence_score=0.95,
        evidence_level="HIGH",
        evidence_count=2,
        repository_count=1,
    )
    db.add(demo)
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}")
        assert res.status_code == 200
        data = res.json()["data"]
        fastapi_item = next(s for s in data["skills"] if s["canonical_slug"] == "fastapi")
        assert fastapi_item["status"] == "STRONG"
        assert fastapi_item["demonstrated"] is True
        assert fastapi_item["demonstrated_score"] == 0.95
        assert fastapi_item["evidence_level"] == "HIGH"
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            db.delete(u)
            db.commit()
        db.close()


def test_github_low_or_medium_demonstrated_is_partial():
    """8. Demonstrated evidence below the 0.85 strong threshold is PARTIAL."""
    db = SessionLocal()
    user = User(email=f"demo-med-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()

    skill = db.query(Skill).filter(Skill.slug == "docker").first()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id

    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=user.id,
        skill_id=skill.id,
        confidence_score=0.72,
        evidence_level="MEDIUM",
        evidence_count=1,
        repository_count=1,
    )
    db.add(demo)
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}")
        assert res.status_code == 200
        data = res.json()["data"]
        docker_item = next(s for s in data["skills"] if s["canonical_slug"] == "docker")
        assert docker_item["status"] == "PARTIAL"
        assert docker_item["demonstrated"] is True
        assert docker_item["demonstrated_score"] == 0.72
        assert docker_item["evidence_level"] == "MEDIUM"
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            db.delete(u)
            db.commit()
        db.close()


def test_both_claimed_and_high_demonstrated_is_strong():
    """9. Both claimed and high demonstrated evidence classifies as STRONG."""
    db = SessionLocal()
    user = User(email=f"both-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()

    skill = db.query(Skill).filter(Skill.slug == "postgresql").first()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id

    claimed = UserClaimedSkill(
        id=uuid.uuid4(),
        user_id=user.id,
        skill_id=skill.id,
        raw_mention="PostgreSQL",
        confidence_score=1.0,
    )
    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=user.id,
        skill_id=skill.id,
        confidence_score=0.92,
        evidence_level="HIGH",
        evidence_count=3,
        repository_count=2,
    )
    db.add_all([claimed, demo])
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}")
        assert res.status_code == 200
        data = res.json()["data"]
        pg_item = next(s for s in data["skills"] if s["canonical_slug"] == "postgresql")
        assert pg_item["status"] == "STRONG"
        assert pg_item["claimed"] is True
        assert pg_item["demonstrated"] is True
        assert pg_item["demonstrated_score"] == 0.92
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            db.delete(u)
            db.commit()
        db.close()


# -----------------------------------------------------------------------------
# 10-12: Classification Threshold & Unit Tests
# -----------------------------------------------------------------------------

def test_classification_logic_unit_rules():
    """10. classify_skill_gap helper strictly adheres to STRONG/PARTIAL/MISSING rules."""
    # Strong: High demonstrated
    assert classify_skill_gap(claimed=False, claim_confidence=0.0, demonstrated=True, demonstrated_score=0.90, evidence_level="HIGH") == "STRONG"
    assert classify_skill_gap(claimed=True, claim_confidence=1.0, demonstrated=True, demonstrated_score=0.85, evidence_level="HIGH") == "STRONG"

    # Partial: Claim only
    assert classify_skill_gap(claimed=True, claim_confidence=1.0, demonstrated=False, demonstrated_score=0.0, evidence_level=None) == "PARTIAL"

    # Partial: Low/Med demonstration only
    assert classify_skill_gap(claimed=False, claim_confidence=0.0, demonstrated=True, demonstrated_score=0.70, evidence_level="MEDIUM") == "PARTIAL"
    assert classify_skill_gap(claimed=False, claim_confidence=0.0, demonstrated=True, demonstrated_score=0.50, evidence_level="LOW") == "PARTIAL"

    # Partial: Claimed + Medium demonstration (< 0.85)
    assert classify_skill_gap(claimed=True, claim_confidence=1.0, demonstrated=True, demonstrated_score=0.75, evidence_level="MEDIUM") == "PARTIAL"

    # Missing: Nothing
    assert classify_skill_gap(claimed=False, claim_confidence=0.0, demonstrated=False, demonstrated_score=0.0, evidence_level=None) == "MISSING"


def test_classification_threshold_boundary():
    """11. Strong threshold boundary at exact 0.85."""
    assert classify_skill_gap(claimed=False, claim_confidence=0.0, demonstrated=True, demonstrated_score=0.85, evidence_level=None) == "STRONG"
    assert classify_skill_gap(claimed=False, claim_confidence=0.0, demonstrated=True, demonstrated_score=0.8499, evidence_level="MEDIUM") == "PARTIAL"


# -----------------------------------------------------------------------------
# 12-14: Demand Values & Location Tests
# -----------------------------------------------------------------------------

def test_demand_values_come_from_db():
    """12. Demand scores and growth rates come directly from PostgreSQL skill_demand."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    python_demand = (
        db.query(IndustrySkillDemand)
        .join(Skill)
        .filter(IndustrySkillDemand.role_id == role.id, Skill.slug == "python")
        .first()
    )
    db.close()

    res = client.get(f"/api/v1/gaps/{role.id}")
    assert res.status_code == 200
    python_item = next(s for s in res.json()["data"]["skills"] if s["canonical_slug"] == "python")
    assert python_item["demand_score"] == python_demand.demand_score
    assert python_item["growth_rate"] == python_demand.growth_rate


def test_location_filtering_behavior():
    """13. Skill gap analysis observes geographic location scope."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    db.close()

    # Unseeded location returns 0 required skills safely
    res = client.get(f"/api/v1/gaps/{role.id}?location=NowhereLand")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["summary"]["total_required_skills"] == 0
    assert len(data["skills"]) == 0


# -----------------------------------------------------------------------------
# 14-16: Ownership Isolation & Multi-User Safety
# -----------------------------------------------------------------------------

def test_user_ownership_isolation():
    """14. User A's claims/evidence do not leak into User B's gap analysis."""
    db = SessionLocal()
    user_a = User(email=f"userA-{uuid.uuid4()}@example.com")
    user_b = User(email=f"userB-{uuid.uuid4()}@example.com")
    db.add_all([user_a, user_b])
    db.commit()

    skill = db.query(Skill).filter(Skill.slug == "python").first()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id

    # User A has Python demonstrated
    demo_a = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=user_a.id,
        skill_id=skill.id,
        confidence_score=0.95,
        evidence_level="HIGH",
        evidence_count=2,
    )
    db.add(demo_a)
    db.commit()
    u_a_id = user_a.id
    u_b_id = user_b.id
    db.close()

    try:
        # User A has STRONG Python
        res_a = client.get(f"/api/v1/gaps/{role_id}?user_id={u_a_id}")
        assert res_a.status_code == 200
        item_a = next(s for s in res_a.json()["data"]["skills"] if s["canonical_slug"] == "python")
        assert item_a["status"] == "STRONG"

        # User B has MISSING Python
        res_b = client.get(f"/api/v1/gaps/{role_id}?user_id={u_b_id}")
        assert res_b.status_code == 200
        item_b = next(s for s in res_b.json()["data"]["skills"] if s["canonical_slug"] == "python")
        assert item_b["status"] == "MISSING"
    finally:
        db = SessionLocal()
        ua = db.query(User).filter(User.id == u_a_id).first()
        ub = db.query(User).filter(User.id == u_b_id).first()
        if ua: db.delete(ua)
        if ub: db.delete(ub)
        db.commit()
        db.close()


def test_header_x_user_id_resolution():
    """15. X-User-Id header is properly resolved and ownership-scoped."""
    db = SessionLocal()
    user = User(email=f"hdr-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()
    role = db.query(JobRole).first()
    role_id = role.id
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}", headers={"X-User-Id": str(user_id)})
        assert res.status_code == 200
        assert res.json()["meta"]["user_id"] == str(user_id)
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


# -----------------------------------------------------------------------------
# 16-18: Idempotency & Recomputation Tests
# -----------------------------------------------------------------------------

def test_recomputation_idempotency():
    """16. Repeated computation produces identical results and creates no duplicate records."""
    db = SessionLocal()
    user = User(email=f"idemp-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    role_id = role.id
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    try:
        # First execution
        res1 = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}")
        assert res1.status_code == 200

        # Verify DB records
        db = SessionLocal()
        count1 = db.query(SkillGap).filter(SkillGap.user_id == user_id, SkillGap.role_id == role_id).count()
        assert count1 == 9  # Frontend engineer has 9 skills
        db.close()

        # Second execution
        res2 = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}")
        assert res2.status_code == 200

        # Verify record count did not multiply
        db = SessionLocal()
        count2 = db.query(SkillGap).filter(SkillGap.user_id == user_id, SkillGap.role_id == role_id).count()
        assert count2 == count1
        db.close()

        # Responses are identical
        assert res1.json()["data"]["skills"] == res2.json()["data"]["skills"]
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


def test_recomputation_updates_changed_evidence():
    """17. When evidence changes, recomputation updates status from MISSING to STRONG."""
    db = SessionLocal()
    user = User(email=f"recomp-{uuid.uuid4()}@example.com")
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    skill = db.query(Skill).filter(Skill.slug == "fastapi").first()
    skill_id = skill.id
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    try:
        # Initially MISSING
        res1 = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}")
        item1 = next(s for s in res1.json()["data"]["skills"] if s["canonical_slug"] == "fastapi")
        assert item1["status"] == "MISSING"

        # Now add demonstrated skill
        db = SessionLocal()
        demo = DemonstratedSkill(
            id=uuid.uuid4(),
            user_id=user_id,
            skill_id=skill_id,
            confidence_score=0.95,
            evidence_level="HIGH",
            evidence_count=2,
        )
        db.add(demo)
        db.commit()
        db.close()

        # Recompute -> should be STRONG now
        res2 = client.get(f"/api/v1/gaps/{role_id}?user_id={user_id}")
        item2 = next(s for s in res2.json()["data"]["skills"] if s["canonical_slug"] == "fastapi")
        assert item2["status"] == "STRONG"
        assert item2["demonstrated"] is True
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


# -----------------------------------------------------------------------------
# 18-20: Deterministic Ordering & Data Integrity
# -----------------------------------------------------------------------------

def test_deterministic_gap_ordering():
    """18. Skill gaps are ordered deterministically: MISSING first, then PARTIAL, then STRONG, then demand_score DESC."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    db.close()

    res = client.get(f"/api/v1/gaps/{role.id}")
    assert res.status_code == 200
    skills = res.json()["data"]["skills"]

    for i in range(len(skills) - 1):
        curr = skills[i]
        nxt = skills[i + 1]
        curr_rank = STATUS_SORT_RANK[curr["status"]]
        nxt_rank = STATUS_SORT_RANK[nxt["status"]]
        assert curr_rank <= nxt_rank
        if curr_rank == nxt_rank:
            assert curr["demand_score"] >= nxt["demand_score"]
            if curr["demand_score"] == nxt["demand_score"]:
                assert curr["skill_name"] <= nxt["skill_name"]


def test_invalid_header_user_id_rejected():
    """19. Invalid UUID in X-User-Id returns structured 422 error."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    db.close()

    res = client.get(f"/api/v1/gaps/{role.id}", headers={"X-User-Id": "not-a-uuid"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
