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
    UserClaimedSkill,
    DemonstratedSkill,
    SkillGap,
)
from app.services.skill_gap_service import (
    skill_gap_service,
    calculate_gap_priority,
    classify_priority_level,
    normalize_growth_signal,
    generate_gap_explanation,
    SEVERITY_WEIGHTS,
    PRIORITY_HIGH_THRESHOLD,
    PRIORITY_MEDIUM_THRESHOLD,
    ACTIONABLE_STATUS_SORT_RANK,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1-6: Pure Math, Formula, Boundary & Category Unit Tests
# -----------------------------------------------------------------------------

def test_growth_signal_normalization_and_clamping():
    """1. Normalizes growth into [0.0, 1.0] bounded signal."""
    # Zero growth gives 0.5
    assert normalize_growth_signal(0.0) == 0.5
    # Positive growth +0.10 gives (1.10) / 2 = 0.55
    assert round(normalize_growth_signal(0.10), 4) == 0.55
    # Negative growth -0.10 gives (0.90) / 2 = 0.45
    assert round(normalize_growth_signal(-0.10), 4) == 0.45
    # +1.0 growth gives 1.0
    assert normalize_growth_signal(1.0) == 1.0
    # -1.0 growth gives 0.0
    assert normalize_growth_signal(-1.0) == 0.0
    # Extreme upper clamp (> 1.0)
    assert normalize_growth_signal(2.5) == 1.0
    # Extreme lower clamp (< -1.0)
    assert normalize_growth_signal(-2.5) == 0.0


def test_priority_score_calculation_formula():
    """2. Priority score formula strictly evaluates gap severity * (0.70*demand + 0.30*growth_signal)."""
    # MISSING (weight 1.0), demand 0.80, growth 0.0 (signal 0.5)
    # expected: 1.0 * (0.70 * 0.80 + 0.30 * 0.50) = 0.56 + 0.15 = 0.71
    score = calculate_gap_priority("MISSING", 0.80, 0.0)
    assert score == 0.71

    # PARTIAL (weight 0.5), demand 0.80, growth 0.0 (signal 0.5)
    # expected: 0.5 * (0.71) = 0.355
    score_partial = calculate_gap_priority("PARTIAL", 0.80, 0.0)
    assert score_partial == 0.355

    # STRONG (weight 0.0) gives 0.0
    assert calculate_gap_priority("STRONG", 0.90, 0.20) == 0.0


def test_priority_score_boundaries_and_extremes():
    """3. Extreme values remain strictly bounded in [0.0, 1.0]."""
    # Min extreme: 0.0 demand, -1.0 growth
    assert calculate_gap_priority("MISSING", 0.0, -1.0) == 0.0
    # Max extreme: 1.0 demand, +1.0 growth
    assert calculate_gap_priority("MISSING", 1.0, 1.0) == 1.0
    # Out of range inputs clamped safely
    assert calculate_gap_priority("MISSING", 1.5, 2.0) == 1.0
    assert calculate_gap_priority("MISSING", -0.5, -3.0) == 0.0


def test_priority_category_classification_boundaries():
    """4. Priority tier classification strictly respects HIGH (>=0.67), MEDIUM (>=0.34), and LOW (<0.34)."""
    # HIGH
    assert classify_priority_level(0.67) == "HIGH"
    assert classify_priority_level(0.85) == "HIGH"
    assert classify_priority_level(1.0) == "HIGH"

    # Just below HIGH threshold is MEDIUM
    assert classify_priority_level(0.6699) == "MEDIUM"

    # MEDIUM
    assert classify_priority_level(0.34) == "MEDIUM"
    assert classify_priority_level(0.50) == "MEDIUM"

    # Just below MEDIUM threshold is LOW
    assert classify_priority_level(0.3399) == "LOW"
    assert classify_priority_level(0.10) == "LOW"
    assert classify_priority_level(0.0) == "LOW"


def test_severity_ordering_missing_vs_partial():
    """5. MISSING skill with identical demand and growth always scores higher than PARTIAL."""
    missing_score = calculate_gap_priority("MISSING", 0.60, 0.05)
    partial_score = calculate_gap_priority("PARTIAL", 0.60, 0.05)
    assert missing_score > partial_score
    assert abs(missing_score - partial_score * 2.0) < 0.001


def test_deterministic_explanation_generation():
    """6. Rule-based explanation accurately summarizes severity, demand, and growth without LLM."""
    exp1 = generate_gap_explanation("MISSING", 0.85, 0.12, "HIGH")
    assert "HIGH priority" in exp1
    assert "missing" in exp1
    assert "85%" in exp1
    assert "rapidly growing" in exp1

    exp2 = generate_gap_explanation("PARTIAL", 0.35, -0.08, "LOW")
    assert "LOW priority" in exp2
    assert "partially demonstrated" in exp2
    assert "declining" in exp2


# -----------------------------------------------------------------------------
# 7-12: API & Prioritization Endpoint Tests
# -----------------------------------------------------------------------------

def test_get_prioritized_gaps_endpoint_success():
    """7. GET /api/v1/gaps/{role_id}/priorities returns complete prioritized actionable gaps."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}/priorities")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "meta" in body
    data = body["data"]

    assert data["role"]["slug"] == "backend-engineer"
    assert data["location"] == "India"
    assert "summary" in data
    summary = data["summary"]
    assert summary["total_actionable_gaps"] > 0
    assert summary["missing_count"] + summary["partial_count"] == summary["total_actionable_gaps"]

    gaps = data["gaps"]
    assert len(gaps) == summary["total_actionable_gaps"]
    for g in gaps:
        assert g["status"] in ("MISSING", "PARTIAL")
        assert 0.0 <= g["priority_score"] <= 1.0
        assert g["priority_level"] in ("HIGH", "MEDIUM", "LOW")
        assert len(g["explanation"]) > 10


def test_strong_skills_strictly_excluded():
    """8. STRONG skills are excluded from actionable priorities."""
    db = SessionLocal()
    user = User(email=f"strong-excl-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()

    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    python_skill = db.query(Skill).filter(Skill.slug == "python").first()
    python_id = python_skill.id

    # Give user STRONG python
    demo = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=user.id,
        skill_id=python_id,
        confidence_score=0.95,
        evidence_level="HIGH",
        evidence_count=3,
        repository_count=2,
    )
    db.add(demo)
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}/priorities?user_id={user_id}")
        assert res.status_code == 200
        gaps = res.json()["data"]["gaps"]
        # Python MUST NOT be in actionable gaps
        slugs = [g["canonical_slug"] for g in gaps]
        assert "python" not in slugs
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


def test_nonexistent_role_priorities_returns_404():
    """9. Nonexistent role returns structured 404 NOT_FOUND."""
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/gaps/{fake_id}/priorities")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_malformed_role_uuid_priorities_returns_422():
    """10. Malformed role UUID returns 422 VALIDATION_ERROR."""
    res = client.get("/api/v1/gaps/invalid-uuid-format/priorities")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


# -----------------------------------------------------------------------------
# 11-14: Deterministic Ordering & Tie-Breaking Tests
# -----------------------------------------------------------------------------

def test_deterministic_prioritized_ordering_contract():
    """11. Prioritized gaps adhere strictly to: priority_score DESC, MISSING before PARTIAL, demand DESC, growth DESC, name ASC, id ASC."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}/priorities")
    assert res.status_code == 200
    gaps = res.json()["data"]["gaps"]

    for i in range(len(gaps) - 1):
        curr = gaps[i]
        nxt = gaps[i + 1]

        # 1. Primary: priority_score DESC
        if curr["priority_score"] != nxt["priority_score"]:
            assert curr["priority_score"] >= nxt["priority_score"]
            continue

        # 2. Status: MISSING before PARTIAL
        curr_status_rank = ACTIONABLE_STATUS_SORT_RANK[curr["status"]]
        nxt_status_rank = ACTIONABLE_STATUS_SORT_RANK[nxt["status"]]
        if curr_status_rank != nxt_status_rank:
            assert curr_status_rank <= nxt_status_rank
            continue

        # 3. Demand score DESC
        if curr["demand_score"] != nxt["demand_score"]:
            assert curr["demand_score"] >= nxt["demand_score"]
            continue

        # 4. Growth rate DESC
        if curr["growth_rate"] != nxt["growth_rate"]:
            assert curr["growth_rate"] >= nxt["growth_rate"]
            continue

        # 5. Skill name ASC
        if curr["skill_name"].lower() != nxt["skill_name"].lower():
            assert curr["skill_name"].lower() <= nxt["skill_name"].lower()
            continue

        # 6. Skill ID ASC
        assert str(curr["skill_id"]) <= str(nxt["skill_id"])


# -----------------------------------------------------------------------------
# 12-15: Ownership Isolation & Idempotency Tests
# -----------------------------------------------------------------------------

def test_priorities_user_ownership_isolation():
    """12. User A's evidence does not leak into User B's priorities."""
    db = SessionLocal()
    user_a = User(email=f"prio-userA-{uuid.uuid4()}@example.com")
    user_b = User(email=f"prio-userB-{uuid.uuid4()}@example.com")
    db.add_all([user_a, user_b])
    db.commit()

    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    python_skill = db.query(Skill).filter(Skill.slug == "python").first()
    python_id = python_skill.id

    # User A has HIGH Python (making it STRONG -> excluded)
    demo_a = DemonstratedSkill(
        id=uuid.uuid4(),
        user_id=user_a.id,
        skill_id=python_id,
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
        # User A should NOT have Python in priorities (it is STRONG)
        res_a = client.get(f"/api/v1/gaps/{role_id}/priorities?user_id={u_a_id}")
        assert res_a.status_code == 200
        slugs_a = [g["canonical_slug"] for g in res_a.json()["data"]["gaps"]]
        assert "python" not in slugs_a

        # User B should have Python as MISSING (it is high demand, so high priority)
        res_b = client.get(f"/api/v1/gaps/{role_id}/priorities?user_id={u_b_id}")
        assert res_b.status_code == 200
        slugs_b = [g["canonical_slug"] for g in res_b.json()["data"]["gaps"]]
        assert "python" in slugs_b
    finally:
        db = SessionLocal()
        ua = db.query(User).filter(User.id == u_a_id).first()
        ub = db.query(User).filter(User.id == u_b_id).first()
        if ua: db.delete(ua)
        if ub: db.delete(ub)
        db.commit()
        db.close()


def test_priorities_idempotency_and_no_duplicates():
    """13. Repeated calls to /priorities do not multiply records or change scores."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "ai-ml-engineer").first()
    role_id = role.id
    db.close()

    res1 = client.get(f"/api/v1/gaps/{role_id}/priorities")
    assert res1.status_code == 200
    data1 = res1.json()["data"]

    res2 = client.get(f"/api/v1/gaps/{role_id}/priorities")
    assert res2.status_code == 200
    data2 = res2.json()["data"]

    assert data1["summary"] == data2["summary"]
    assert len(data1["gaps"]) == len(data2["gaps"])
    for g1, g2 in zip(data1["gaps"], data2["gaps"]):
        assert g1["skill_id"] == g2["skill_id"]
        assert g1["priority_score"] == g2["priority_score"]
        assert g1["priority_level"] == g2["priority_level"]


def test_header_x_user_id_priorities_resolution():
    """14. Header X-User-Id properly scopes the priorities request."""
    db = SessionLocal()
    user = User(email=f"hdr-prio-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()
    role = db.query(JobRole).first()
    role_id = role.id
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}/priorities", headers={"X-User-Id": str(user_id)})
        assert res.status_code == 200
        assert res.json()["meta"]["user_id"] == str(user_id)
        assert res.json()["meta"]["scoring_version"] == "v1"
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


def test_empty_actionable_gaps_set():
    """15. When candidate has all skills demonstrated at STRONG level, returns 0 actionable gaps gracefully."""
    db = SessionLocal()
    user = User(email=f"all-strong-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()

    role = db.query(JobRole).filter(JobRole.slug == "ai-ml-engineer").first()
    role_id = role.id
    demands = db.query(IndustrySkillDemand).filter(IndustrySkillDemand.role_id == role_id).all()

    # Give user STRONG in all demanded skills
    for d in demands:
        demo = DemonstratedSkill(
            id=uuid.uuid4(),
            user_id=user.id,
            skill_id=d.skill_id,
            confidence_score=0.95,
            evidence_level="HIGH",
            evidence_count=3,
        )
        db.add(demo)
    db.commit()
    user_id = user.id
    db.close()

    try:
        res = client.get(f"/api/v1/gaps/{role_id}/priorities?user_id={user_id}")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["summary"]["total_actionable_gaps"] == 0
        assert data["summary"]["high_priority_count"] == 0
        assert data["summary"]["medium_priority_count"] == 0
        assert data["summary"]["low_priority_count"] == 0
        assert len(data["gaps"]) == 0
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()
