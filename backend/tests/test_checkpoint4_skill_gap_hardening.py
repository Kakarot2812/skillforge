import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import (
    JobRole,
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


# -----------------------------------------------------------------------------
# 1-6: Input Validation & Bounds
# -----------------------------------------------------------------------------

def test_location_blank_or_whitespace_rejected():
    """1. Blank or whitespace location in query params returns 422 VALIDATION_ERROR."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}?location=%20%20%20")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "blank or whitespace" in res.json()["error"]["message"]


def test_location_excessive_length_rejected():
    """2. Location exceeding 64 characters returns 422 VALIDATION_ERROR."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    long_loc = "A" * 65
    res = client.get(f"/api/v1/gaps/{role_id}?location={long_loc}")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "exceeds maximum length" in res.json()["error"]["message"]


def test_invalid_gap_status_filter_rejected():
    """3. Invalid status query filter on GET /gaps/{role_id} returns 422."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}?status=NONEXISTENT_STATUS")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "Invalid status filter" in res.json()["error"]["message"]


def test_valid_gap_status_filter_filtering():
    """4. Valid status filter returns only matching items."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}?status=MISSING")
    assert res.status_code == 200
    skills = res.json()["data"]["skills"]
    for s in skills:
        assert s["status"] == "MISSING"


def test_invalid_priority_level_filter_rejected():
    """5. Invalid priority_level query filter on GET /priorities returns 422."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}/priorities?priority_level=CRITICAL")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "Invalid priority_level filter" in res.json()["error"]["message"]


def test_invalid_actionable_status_filter_for_priorities_rejected():
    """6. Invalid status filter on GET /priorities (e.g. STRONG, which is non-actionable) returns 422."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    # STRONG skills are strictly excluded from priorities, so filtering by STRONG is invalid
    res = client.get(f"/api/v1/gaps/{role_id}/priorities?status=STRONG")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


# -----------------------------------------------------------------------------
# 7-10: Pagination & Limit/Offset Boundaries
# -----------------------------------------------------------------------------

def test_pagination_negative_offset_rejected():
    """7. Negative offset returns 422 VALIDATION_ERROR."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}?offset=-1")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_pagination_excessive_limit_rejected():
    """8. Limit > 100 returns 422 VALIDATION_ERROR."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}?limit=101")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_pagination_limit_and_offset_slicing():
    """9. Valid limit & offset slices the returned skills deterministically."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res_all = client.get(f"/api/v1/gaps/{role_id}")
    assert res_all.status_code == 200
    all_skills = res_all.json()["data"]["skills"]

    if len(all_skills) >= 3:
        res_page1 = client.get(f"/api/v1/gaps/{role_id}?limit=2&offset=0")
        assert res_page1.status_code == 200
        page1 = res_page1.json()["data"]["skills"]
        assert len(page1) == 2
        assert page1[0]["skill_id"] == all_skills[0]["skill_id"]
        assert page1[1]["skill_id"] == all_skills[1]["skill_id"]

        res_page2 = client.get(f"/api/v1/gaps/{role_id}?limit=2&offset=2")
        assert res_page2.status_code == 200
        page2 = res_page2.json()["data"]["skills"]
        assert len(page2) >= 1
        assert page2[0]["skill_id"] == all_skills[2]["skill_id"]


def test_analyze_request_blank_location_rejected():
    """10. POST /analyze with blank location fails Pydantic validation cleanly with 422."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res = client.post(
        "/api/v1/gaps/analyze",
        json={"target_role_id": str(role_id), "location": "   "},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


# -----------------------------------------------------------------------------
# 11-14: Security, IDOR Protection & User Verification
# -----------------------------------------------------------------------------

def test_query_and_header_user_mismatch_returns_403():
    """11. Mismatch between query user_id and X-User-Id header triggers IDOR 403 FORBIDDEN."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    u1 = User(email=f"u1-{uuid.uuid4()}@example.com")
    u2 = User(email=f"u2-{uuid.uuid4()}@example.com")
    db.add_all([u1, u2])
    db.commit()
    u1_id = u1.id
    u2_id = u2.id
    db.close()

    try:
        res = client.get(
            f"/api/v1/gaps/{role_id}?user_id={u1_id}",
            headers={"X-User-Id": str(u2_id)},
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"
        assert "Cross-user access denied" in res.json()["error"]["message"]
    finally:
        db = SessionLocal()
        for uid in [u1_id, u2_id]:
            u = db.query(User).filter(User.id == uid).first()
            if u: db.delete(u)
        db.commit()
        db.close()


def test_analyze_payload_and_header_user_mismatch_returns_403():
    """12. POST /analyze payload user_id mismatch with X-User-Id triggers IDOR 403 FORBIDDEN."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    u1 = User(email=f"u1-post-{uuid.uuid4()}@example.com")
    u2 = User(email=f"u2-post-{uuid.uuid4()}@example.com")
    db.add_all([u1, u2])
    db.commit()
    u1_id = u1.id
    u2_id = u2.id
    db.close()

    try:
        res = client.post(
            "/api/v1/gaps/analyze",
            json={"target_role_id": str(role_id), "user_id": str(u1_id)},
            headers={"X-User-Id": str(u2_id)},
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"
        assert "Cross-user access denied" in res.json()["error"]["message"]
    finally:
        db = SessionLocal()
        for uid in [u1_id, u2_id]:
            u = db.query(User).filter(User.id == uid).first()
            if u: db.delete(u)
        db.commit()
        db.close()


def test_nonexistent_user_id_returns_404():
    """13. Supplying an unknown user_id returns 404 NOT_FOUND cleanly without 500 error."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    fake_user_id = uuid.uuid4()
    res = client.get(f"/api/v1/gaps/{role_id}?user_id={fake_user_id}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"
    assert "not found" in res.json()["error"]["message"]


def test_evidence_endpoint_user_mismatch_returns_403():
    """14. GET evidence endpoint with mismatched user_id and X-User-Id returns 403 FORBIDDEN."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    skill = db.query(Skill).first()
    role_id = role.id
    skill_id = skill.id
    u1 = User(email=f"ev-u1-{uuid.uuid4()}@example.com")
    u2 = User(email=f"ev-u2-{uuid.uuid4()}@example.com")
    db.add_all([u1, u2])
    db.commit()
    u1_id = u1.id
    u2_id = u2.id
    db.close()

    try:
        res = client.get(
            f"/api/v1/gaps/{role_id}/skills/{skill_id}/evidence?user_id={u1_id}",
            headers={"X-User-Id": str(u2_id)},
        )
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"
    finally:
        db = SessionLocal()
        for uid in [u1_id, u2_id]:
            u = db.query(User).filter(User.id == uid).first()
            if u: db.delete(u)
        db.commit()
        db.close()


# -----------------------------------------------------------------------------
# 15-18: Idempotency & Stale Reconciliation
# -----------------------------------------------------------------------------

def test_analyze_recomputation_idempotency_and_zero_duplicate_rows():
    """15. Consecutive POST /analyze executions do not inflate row count or alter scores."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    user = User(email=f"idemp-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    try:
        # First analyze
        res1 = client.post("/api/v1/gaps/analyze", json={"target_role_id": str(role_id), "user_id": str(user_id)})
        assert res1.status_code == 200
        count1 = res1.json()["data"]["summary"]["total_required_skills"]

        db = SessionLocal()
        db_count1 = db.query(SkillGap).filter(SkillGap.user_id == user_id, SkillGap.role_id == role_id).count()
        db.close()
        assert db_count1 == count1

        # Second analyze
        res2 = client.post("/api/v1/gaps/analyze", json={"target_role_id": str(role_id), "user_id": str(user_id)})
        assert res2.status_code == 200
        count2 = res2.json()["data"]["summary"]["total_required_skills"]

        db = SessionLocal()
        db_count2 = db.query(SkillGap).filter(SkillGap.user_id == user_id, SkillGap.role_id == role_id).count()
        db.close()
        assert db_count2 == count1
        assert count2 == count1
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


def test_reconciliation_reflects_newly_added_candidate_evidence():
    """16. Newly added candidate claims immediately flip MISSING to PARTIAL/STRONG upon re-analysis."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    role_id = role.id
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    skill_id = skill.id
    user = User(email=f"flip-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    try:
        # Initial analyze: Python is MISSING
        res1 = client.post("/api/v1/gaps/analyze", json={"target_role_id": str(role_id), "user_id": str(user_id)})
        assert res1.status_code == 200
        py1 = next(s for s in res1.json()["data"]["skills"] if s["skill_id"] == str(skill_id))
        assert py1["status"] == "MISSING"

        # Candidate claims Python
        db = SessionLocal()
        claim = UserClaimedSkill(
            id=uuid.uuid4(), user_id=user_id, skill_id=skill_id,
            raw_mention="Python 3.12 Backend Specialist", confidence_score=1.0
        )
        db.add(claim)
        db.commit()
        db.close()

        # Second analyze: Python is immediately PARTIAL
        res2 = client.post("/api/v1/gaps/analyze", json={"target_role_id": str(role_id), "user_id": str(user_id)})
        assert res2.status_code == 200
        py2 = next(s for s in res2.json()["data"]["skills"] if s["skill_id"] == str(skill_id))
        assert py2["status"] == "PARTIAL"
        assert py2["claimed"] is True
    finally:
        db = SessionLocal()
        u = db.query(User).filter(User.id == user_id).first()
        if u: db.delete(u); db.commit()
        db.close()


def test_deterministic_ordering_stability_across_calls():
    """17. Repeated calls return strictly identical ordering for priorities and gaps."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res1 = client.get(f"/api/v1/gaps/{role_id}/priorities")
    res2 = client.get(f"/api/v1/gaps/{role_id}/priorities")
    assert res1.status_code == 200
    assert res2.status_code == 200

    gaps1 = [g["skill_id"] for g in res1.json()["data"]["gaps"]]
    gaps2 = [g["skill_id"] for g in res2.json()["data"]["gaps"]]
    assert gaps1 == gaps2


def test_anonymous_user_returns_global_market_perspective():
    """18. Anonymous user (no user_id) receives 200 OK with valid global market requirements."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    role_id = role.id
    db.close()

    res = client.get(f"/api/v1/gaps/{role_id}")
    assert res.status_code == 200
    meta = res.json()["meta"]
    assert meta["user_id"] is None
    assert meta["scoring_version"] == "v1"
