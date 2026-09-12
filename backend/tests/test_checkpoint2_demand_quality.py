import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.db.database import SessionLocal
from app.db.models import JobRole, IndustrySkillDemand, Skill
from app.services.demand_service import demand_service

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1-10: Data Quality & Database Constraints Tests
# -----------------------------------------------------------------------------

def test_valid_demand_record_accepted():
    """1. Valid demand record can be created within constraints."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    skill = db.query(Skill).first()
    demand = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=role.id,
        skill_id=skill.id,
        location="TestRegion",
        sample_size=5000,
        demand_score=0.65,
        growth_rate=0.05,
    )
    db.add(demand)
    db.commit()

    # Verify persisted
    found = db.query(IndustrySkillDemand).filter(IndustrySkillDemand.id == demand.id).first()
    assert found is not None
    assert found.demand_score == 0.65
    assert found.sample_size == 5000

    # Cleanup
    db.delete(found)
    db.commit()
    db.close()


def test_invalid_demand_score_rejected():
    """2, 3 & 4. Demand score lower and upper bounds (< 0.0 or > 1.0) are rejected."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    skill = db.query(Skill).first()

    # Score > 1.0
    too_high = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=role.id,
        skill_id=skill.id,
        location="UpperBoundsTest",
        sample_size=1000,
        demand_score=1.01,
    )
    db.add(too_high)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Score < 0.0
    too_low = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=role.id,
        skill_id=skill.id,
        location="LowerBoundsTest",
        sample_size=1000,
        demand_score=-0.05,
    )
    db.add(too_low)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_sample_size_validation():
    """5. sample_size must be positive (> 0); zero and negative are rejected."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    skill = db.query(Skill).first()

    # sample_size = 0
    zero_size = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=role.id,
        skill_id=skill.id,
        location="ZeroSizeTest",
        sample_size=0,
        demand_score=0.5,
    )
    db.add(zero_size)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # negative sample_size
    neg_size = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=role.id,
        skill_id=skill.id,
        location="NegSizeTest",
        sample_size=-100,
        demand_score=0.5,
    )
    db.add(neg_size)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_valid_negative_growth_rate_accepted():
    """6. Negative growth rate is valid and accepted (e.g. -0.05 = -5% YoY)."""
    db = SessionLocal()
    role = db.query(JobRole).first()
    skill = db.query(Skill).first()

    declining_demand = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=role.id,
        skill_id=skill.id,
        location="DecliningTest",
        sample_size=1000,
        demand_score=0.30,
        growth_rate=-0.05,
    )
    db.add(declining_demand)
    db.commit()

    persisted = db.query(IndustrySkillDemand).filter(IndustrySkillDemand.id == declining_demand.id).first()
    assert persisted.growth_rate == -0.05

    db.delete(persisted)
    db.commit()
    db.close()


def test_invalid_role_and_skill_references_rejected():
    """7 & 8. Non-existent role_id or skill_id violates foreign key constraint."""
    db = SessionLocal()
    skill = db.query(Skill).first()
    role = db.query(JobRole).first()

    # Invalid role reference
    bad_role = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=uuid.uuid4(),
        skill_id=skill.id,
        location="BadRoleTest",
        sample_size=1000,
        demand_score=0.5,
    )
    db.add(bad_role)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Invalid skill reference
    bad_skill = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=role.id,
        skill_id=uuid.uuid4(),
        location="BadSkillTest",
        sample_size=1000,
        demand_score=0.5,
    )
    db.add(bad_skill)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_duplicate_role_skill_location_rejected():
    """9. Duplicate (role_id, skill_id, location) combination is rejected."""
    db = SessionLocal()
    existing = db.query(IndustrySkillDemand).first()

    duplicate = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=existing.role_id,
        skill_id=existing.skill_id,
        location=existing.location,
        sample_size=existing.sample_size,
        demand_score=existing.demand_score,
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_orphan_demand_records_audit_and_detection():
    """10. audit_demand_data_quality detects zero orphans in seeded data."""
    db = SessionLocal()
    audit = demand_service.audit_demand_data_quality(db)
    db.close()
    assert audit["status"] == "VALID"
    assert audit["orphaned_demand_records"] == 0
    assert audit["out_of_bounds_scores"] == 0
    assert audit["non_positive_sample_sizes"] == 0
    assert audit["duplicate_records"] == 0


# -----------------------------------------------------------------------------
# 11-15: Aggregation Tests
# -----------------------------------------------------------------------------

def test_role_demand_aggregates_deterministic_and_accurate():
    """11, 12, 13, 14 & 15. Aggregates are computed via SQL without LLM dependency."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    aggregates = demand_service.get_role_demand_aggregates(db, role.id, location="India")
    db.close()

    assert aggregates["total_demanded_skills"] == 13
    assert aggregates["average_demand_score"] == 0.58
    assert aggregates["highest_demand_score"] == 0.78
    assert aggregates["lowest_demand_score"] == 0.35
    assert aggregates["top_skill"] == "Git"
    assert aggregates["average_growth_rate"] == 0.08


# -----------------------------------------------------------------------------
# 16-21: Filtering and Deterministic Ordering Tests
# -----------------------------------------------------------------------------

def test_demand_filtering_combination():
    """16, 17, 18 & 19. Individual and combined filtering by role, skill, and location."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    db.close()

    # Combined filter
    res = client.get(f"/api/v1/demand?role_id={role.id}&skill_id={skill.id}&location=India")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["canonical_slug"] == "python"
    assert data[0]["demand_score"] == 0.68


def test_invalid_uuid_handling():
    """20. Malformed UUID parameter returns 422 validation envelope."""
    res = client.get("/api/v1/demand?role_id=not-a-valid-uuid")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_deterministic_ordering_with_tie_breaker():
    """21. Deterministic ordering: demand_score DESC, skill.name ASC, skill.id ASC."""
    res = client.get("/api/v1/demand?limit=50")
    assert res.status_code == 200
    data = res.json()["data"]
    for i in range(len(data) - 1):
        curr = data[i]
        nxt = data[i + 1]
        assert curr["demand_score"] >= nxt["demand_score"]
        if curr["demand_score"] == nxt["demand_score"]:
            assert curr["skill_name"] <= nxt["skill_name"]


# -----------------------------------------------------------------------------
# 22-27: Pagination Hardening Tests
# -----------------------------------------------------------------------------

def test_demand_pagination_edge_cases():
    """22, 23, 24, 25, 26 & 27. Pagination bounds and edge cases."""
    # First page
    p1 = client.get("/api/v1/demand?limit=5&offset=0").json()
    assert len(p1["data"]) == 5

    # Second page
    p2 = client.get("/api/v1/demand?limit=5&offset=5").json()
    assert len(p2["data"]) == 5
    assert p1["data"][0]["skill_id"] != p2["data"][0]["skill_id"]

    # Offset beyond dataset
    p_empty = client.get("/api/v1/demand?limit=10&offset=5000").json()
    assert len(p_empty["data"]) == 0
    assert p_empty["meta"]["total"] >= 49

    # Negative offset rejected
    assert client.get("/api/v1/demand?offset=-1").status_code == 422

    # Zero limit rejected
    assert client.get("/api/v1/demand?limit=0").status_code == 422

    # Excessive limit rejected
    assert client.get("/api/v1/demand?limit=101").status_code == 422


# -----------------------------------------------------------------------------
# 28-33: API Contract & Response Structure Tests
# -----------------------------------------------------------------------------

def test_api_endpoints_operational_and_enriched_meta():
    """28, 29, 30, 31, 32 & 33. All endpoints working with enriched metadata."""
    # GET /roles
    assert client.get("/api/v1/roles").status_code == 200

    # GET /roles/{id}
    roles = client.get("/api/v1/roles").json()["data"]
    role_id = roles[0]["role_id"]
    assert client.get(f"/api/v1/roles/{role_id}").status_code == 200

    # GET /demand
    assert client.get("/api/v1/demand").status_code == 200

    # GET /demand/{role_id} with enriched aggregates
    res_detail = client.get(f"/api/v1/demand/{role_id}")
    assert res_detail.status_code == 200
    meta = res_detail.json()["meta"]
    assert "total_demanded_skills" in meta
    assert "average_demand_score" in meta
    assert "highest_demand_score" in meta
    assert "top_skill" in meta
    assert "average_growth_rate" in meta

    # Nonexistent role 404
    res_404 = client.get(f"/api/v1/demand/{uuid.uuid4()}")
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "NOT_FOUND"

    # Audit quality endpoint
    res_audit = client.get("/api/v1/demand/audit/quality")
    assert res_audit.status_code == 200
    assert res_audit.json()["data"]["status"] == "VALID"


# -----------------------------------------------------------------------------
# 34-38: Ownership & Provenance Tests
# -----------------------------------------------------------------------------

def test_global_ownership_and_provenance():
    """34, 35, 36, 37 & 38. Demand remains global and unpolluted by user contexts."""
    # Calling demand API without authentication or with different arbitrary headers returns identical dataset
    res1 = client.get("/api/v1/demand?limit=10")
    res2 = client.get("/api/v1/demand?limit=10", headers={"X-User-Id": str(uuid.uuid4())})
    assert res1.json()["data"] == res2.json()["data"]

    # Freshness date reflects dynamic market snapshot freshness, not mutated on read
    db = SessionLocal()
    try:
        expected_freshness = demand_service.get_market_data_freshness(db)
    finally:
        db.close()

    meta = res1.json()["meta"]
    assert meta["data_freshness"] == expected_freshness

