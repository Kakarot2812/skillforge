import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.db.database import SessionLocal
from app.db.models import JobRole, IndustrySkillDemand, Skill

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1-7: Canonical Job Roles Tests
# -----------------------------------------------------------------------------

def test_canonical_job_roles_seeded():
    """1. Verify canonical job roles are seeded in the database."""
    db = SessionLocal()
    roles = db.query(JobRole).all()
    db.close()
    assert len(roles) >= 5
    slugs = {r.slug for r in roles}
    assert "backend-engineer" in slugs
    assert "full-stack-engineer" in slugs
    assert "frontend-engineer" in slugs
    assert "cloud-devops-engineer" in slugs
    assert "ai-ml-engineer" in slugs


def test_list_job_roles_endpoint_and_envelope():
    """2. GET /api/v1/roles returns 200 with standard envelope."""
    res = client.get("/api/v1/roles")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["total"] >= 5
    assert len(body["data"]) >= 5
    first = body["data"][0]
    assert "role_id" in first
    assert "title" in first
    assert "slug" in first
    assert "category" in first


def test_job_roles_pagination():
    """3. Pagination limits and offsets work correctly."""
    res = client.get("/api/v1/roles?limit=2&offset=1")
    assert res.status_code == 200
    body = res.json()
    assert len(body["data"]) == 2
    assert body["meta"]["limit"] == 2
    assert body["meta"]["offset"] == 1


def test_job_roles_deterministic_ordering_and_category_filter():
    """4. Roles are ordered deterministically by category ASC, title ASC and filterable by category."""
    res = client.get("/api/v1/roles?category=Engineering")
    assert res.status_code == 200
    body = res.json()
    titles = [r["title"] for r in body["data"]]
    assert all(r["category"] == "Engineering" for r in body["data"])
    assert titles == sorted(titles)


def test_get_job_role_by_id_success():
    """5. GET /api/v1/roles/{role_id} returns the specific canonical role."""
    list_res = client.get("/api/v1/roles?limit=1")
    first_role = list_res.json()["data"][0]
    role_id = first_role["role_id"]

    res = client.get(f"/api/v1/roles/{role_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["role_id"] == role_id
    assert body["data"]["title"] == first_role["title"]


def test_get_job_role_not_found_404():
    """6. Nonexistent role UUID returns structured 404."""
    nonexistent_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/roles/{nonexistent_id}")
    assert res.status_code == 404
    body = res.json()
    assert body["error"]["code"] == "NOT_FOUND"


def test_get_job_role_invalid_uuid():
    """7. Malformed role UUID returns 422 validation error."""
    res = client.get("/api/v1/roles/not-a-valid-uuid")
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


# -----------------------------------------------------------------------------
# 8-20: Industry Skill Demand Tests
# -----------------------------------------------------------------------------

def test_demand_records_associated_with_canonical_roles_and_skills():
    """8 & 9. Demand records link foreign keys to job_roles and canonical skills."""
    db = SessionLocal()
    demands = db.query(IndustrySkillDemand).all()
    assert len(demands) > 0
    for d in demands[:10]:
        assert d.role is not None
        assert d.skill is not None
        assert isinstance(d.role.title, str)
        assert isinstance(d.skill.name, str)
    db.close()


def test_list_industry_demand_endpoint():
    """10. GET /api/v1/demand returns 200 with standard envelope."""
    res = client.get("/api/v1/demand")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["total"] >= 40
    first = body["data"][0]
    assert "skill_id" in first
    assert "skill_name" in first
    assert "canonical_slug" in first
    assert "role_title" in first
    assert "demand_score" in first
    assert "growth_rate" in first
    assert "location" in first
    assert "data_freshness" in body["meta"]


def test_industry_demand_pagination():
    """11. Demand pagination offset and limit enforce bounds."""
    res = client.get("/api/v1/demand?limit=5&offset=5")
    assert res.status_code == 200
    body = res.json()
    assert len(body["data"]) == 5
    assert body["meta"]["limit"] == 5
    assert body["meta"]["offset"] == 5


def test_industry_demand_filtering():
    """12. Filter demand by role_id, skill_id, and location."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    db.close()

    # Filter by role
    res_role = client.get(f"/api/v1/demand?role_id={role.id}")
    assert res_role.status_code == 200
    assert all(d["role_id"] == str(role.id) for d in res_role.json()["data"])

    # Filter by skill
    res_skill = client.get(f"/api/v1/demand?skill_id={skill.id}")
    assert res_skill.status_code == 200
    assert all(d["skill_id"] == str(skill.id) for d in res_skill.json()["data"])

    # Filter by location
    res_loc = client.get("/api/v1/demand?location=India")
    assert res_loc.status_code == 200
    assert all(d["location"] == "India" for d in res_loc.json()["data"])


def test_get_role_demand_profile_breakdown():
    """13. GET /api/v1/demand/{role_id} returns complete role demand profile."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    db.close()

    res = client.get(f"/api/v1/demand/{role.id}")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert body["data"]["role"]["role_id"] == str(role.id)
    assert body["data"]["role"]["slug"] == "backend-engineer"
    skills = body["data"]["skills"]
    assert len(skills) > 0
    skill_slugs = {s["canonical_slug"] for s in skills}
    assert "java" in skill_slugs
    assert "python" in skill_slugs
    assert "docker" in skill_slugs


def test_get_role_demand_not_found_404():
    """14. GET /api/v1/demand/{role_id} returns 404 for missing role."""
    fake_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/demand/{fake_id}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


def test_demand_score_range_and_check_constraint():
    """15. Demand scores are strictly bounded in [0.0, 1.0]."""
    db = SessionLocal()
    demands = db.query(IndustrySkillDemand).all()
    for d in demands:
        assert 0.0 <= d.demand_score <= 1.0

    # Test DB check constraint rejects values outside [0.0, 1.0]
    invalid_demand = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=demands[0].role_id,
        skill_id=demands[0].skill_id,
        location="OutlierLocation",
        demand_score=1.5,  # Invalid
    )
    db.add(invalid_demand)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_duplicate_role_skill_demand_prevented():
    """16. Unique constraint prevents duplicate role-skill demand records."""
    db = SessionLocal()
    existing = db.query(IndustrySkillDemand).first()
    duplicate = IndustrySkillDemand(
        id=uuid.uuid4(),
        role_id=existing.role_id,
        skill_id=existing.skill_id,
        location=existing.location,
        demand_score=0.5,
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_demand_deterministic_ordering():
    """17. Demand records are deterministically ordered by demand_score DESC, skill.name ASC."""
    res = client.get("/api/v1/demand?limit=20")
    assert res.status_code == 200
    data = res.json()["data"]
    scores = [d["demand_score"] for d in data]
    assert scores == sorted(scores, reverse=True)


def test_demand_score_persisted_from_database():
    """18. Demand score comes from database rows, not runtime generation or LLM."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    skill = db.query(Skill).filter(Skill.slug == "docker").first()
    db_demand = (
        db.query(IndustrySkillDemand)
        .filter(IndustrySkillDemand.role_id == role.id, IndustrySkillDemand.skill_id == skill.id)
        .first()
    )
    expected_score = round(db_demand.demand_score, 2)
    db.close()

    res = client.get(f"/api/v1/demand?role_id={role.id}&skill_id={skill.id}")
    assert res.status_code == 200
    api_score = res.json()["data"][0]["demand_score"]
    assert api_score == expected_score


def test_no_user_ownership_filtering_on_global_demand():
    """19. Canonical roles and demand are global shared data; no user_id filtering is applied."""
    res = client.get("/api/v1/roles")
    assert res.status_code == 200
    assert res.json()["meta"]["total"] >= 5

    res_dem = client.get("/api/v1/demand")
    assert res_dem.status_code == 200
    assert res_dem.json()["meta"]["total"] >= 40


def test_unknown_skills_not_inserted_into_canonical_skills():
    """20. Unknown skills are not inserted into the canonical skills table."""
    db = SessionLocal()
    initial_count = db.query(Skill).count()
    # Call demand API with non-existent query parameter
    res = client.get(f"/api/v1/demand?skill_id={uuid.uuid4()}")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 0
    after_count = db.query(Skill).count()
    assert initial_count == after_count
    db.close()


# -----------------------------------------------------------------------------
# 21-23: Validation & Error Envelope Security
# -----------------------------------------------------------------------------

def test_invalid_uuid_query_parameters():
    """21. Invalid UUID query parameters return 422 validation error."""
    res = client.get("/api/v1/demand?role_id=bad-uuid")
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_pagination_parameters():
    """22. Out-of-bounds pagination values return 422 validation error."""
    # Negative offset
    res_neg = client.get("/api/v1/roles?offset=-5")
    assert res_neg.status_code == 422
    assert res_neg.json()["error"]["code"] == "VALIDATION_ERROR"

    # Limit = 0
    res_zero = client.get("/api/v1/demand?limit=0")
    assert res_zero.status_code == 422

    # Limit > 100
    res_large = client.get("/api/v1/demand?limit=101")
    assert res_large.status_code == 422


def test_error_envelope_sanitization_no_leakage():
    """23. Error envelopes conform to API_SPEC and never leak DB connection strings or SQL."""
    fake_role_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/roles/{fake_role_id}")
    assert res.status_code == 404
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "NOT_FOUND"
    assert "postgres" not in res.text.lower()
    assert "select" not in res.text.lower()
    assert "traceback" not in res.text.lower()
