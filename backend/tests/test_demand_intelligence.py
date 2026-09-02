import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.db.models import JobRole, IndustrySkillDemand, Skill
from app.services.demand_intelligence_service import (
    demand_intelligence_service,
    classify_growth,
)

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1-3: Skill Demand Ranking & Skill Across Roles Tests
# -----------------------------------------------------------------------------

def test_global_skill_demand_ranking():
    """1. Global skill demand ranking calculates weighted average across roles."""
    res = client.get("/api/v1/intelligence/skills/ranking?limit=10")
    assert res.status_code == 200
    body = res.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["total"] > 0
    data = body["data"]
    assert len(data) <= 10
    first = data[0]
    assert "skill_id" in first
    assert "demand_score" in first
    assert "average_growth_rate" in first
    assert "role_count" in first
    assert "total_sample_size" in first
    assert "trend" in first
    # Verify deterministic descending demand_score order
    scores = [d["demand_score"] for d in data]
    assert scores == sorted(scores, reverse=True)


def test_role_filtered_skill_ranking():
    """2. Role-specific ranking filters skills to the specified role."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    db.close()

    res = client.get(f"/api/v1/intelligence/skills/ranking?role_id={role.id}")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["role_id"] == str(role.id)
    data = body["data"]
    assert len(data) == 13  # Backend engineer has 13 skills seeded
    slugs = {d["canonical_slug"] for d in data}
    assert "java" in slugs
    assert "python" in slugs
    assert "fastapi" in slugs


def test_skill_across_roles():
    """3. Skill across roles returns demand profile in all roles using that skill."""
    db = SessionLocal()
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    db.close()

    res = client.get(f"/api/v1/intelligence/skills/{skill.id}/roles")
    assert res.status_code == 200
    body = res.json()
    data = body["data"]
    assert data["skill"]["slug"] == "python"
    assert data["total_roles_demanding"] >= 3  # Python is in Backend, AI/ML, Cloud/DevOps
    role_titles = [r["role_title"] for r in data["roles"]]
    assert "AI/ML Engineer" in role_titles
    assert "Backend Engineer" in role_titles
    # Verify descending demand_score ordering across roles
    scores = [r["demand_score"] for r in data["roles"]]
    assert scores == sorted(scores, reverse=True)


# -----------------------------------------------------------------------------
# 4-12: Role Comparison & Validation Tests
# -----------------------------------------------------------------------------

def test_role_comparison():
    """4. Compare two canonical roles returns roles, shared skills, and role-specific skills."""
    db = SessionLocal()
    r1 = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    r2 = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    db.close()

    payload = {"role_ids": [str(r1.id), str(r2.id)], "location": "India"}
    res = client.post("/api/v1/intelligence/roles/compare", json=payload)
    assert res.status_code == 200
    body = res.json()["data"]
    assert len(body["roles"]) == 2
    assert "shared_skills" in body
    assert "role_specific_skills" in body
    assert "comparison_summary" in body
    assert body["comparison_summary"]["compared_roles_count"] == 2


def test_shared_skill_detection():
    """5. Shared skills exist in every compared role and compute demand differentials."""
    db = SessionLocal()
    r1 = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    r2 = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    db.close()

    payload = {"role_ids": [str(r1.id), str(r2.id)]}
    res = client.post("/api/v1/intelligence/roles/compare", json=payload)
    assert res.status_code == 200
    shared = res.json()["data"]["shared_skills"]
    shared_slugs = [s["canonical_slug"] for s in shared]
    # Git and REST APIs are common to both Backend and Frontend
    assert "git" in shared_slugs
    assert "rest-apis" in shared_slugs
    for s in shared:
        assert str(r1.id) in s["demands_by_role"]
        assert str(r2.id) in s["demands_by_role"]
        assert s["demand_score_diff"] >= 0.0


def test_role_specific_skill_detection():
    """6. Role-specific skills belong to only one compared role."""
    db = SessionLocal()
    r1 = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    r2 = db.query(JobRole).filter(JobRole.slug == "frontend-engineer").first()
    db.close()

    payload = {"role_ids": [str(r1.id), str(r2.id)]}
    res = client.post("/api/v1/intelligence/roles/compare", json=payload)
    assert res.status_code == 200
    specific = res.json()["data"]["role_specific_skills"]

    backend_specific_slugs = [s["canonical_slug"] for s in specific[str(r1.id)]]
    frontend_specific_slugs = [s["canonical_slug"] for s in specific[str(r2.id)]]

    # Java, FastAPI, Spring Boot belong to backend but not frontend
    assert "java" in backend_specific_slugs
    assert "fastapi" in backend_specific_slugs
    # Tailwind CSS belongs to frontend but not backend
    assert "tailwindcss" in frontend_specific_slugs


def test_role_comparison_requires_two_roles():
    """7. Role comparison rejects fewer than 2 roles."""
    role_id = str(uuid.uuid4())
    res = client.post("/api/v1/intelligence/roles/compare", json={"role_ids": [role_id]})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_role_comparison_max_five_roles():
    """8. Role comparison rejects more than 5 roles."""
    role_ids = [str(uuid.uuid4()) for _ in range(6)]
    res = client.post("/api/v1/intelligence/roles/compare", json={"role_ids": role_ids})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_duplicate_role_ids_rejected():
    """9. Duplicate role IDs are rejected in comparison."""
    r_id = str(uuid.uuid4())
    res = client.post("/api/v1/intelligence/roles/compare", json={"role_ids": [r_id, r_id]})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_role_uuid_rejected():
    """10. Malformed role UUID returns 422 validation error."""
    res = client.post("/api/v1/intelligence/roles/compare", json={"role_ids": ["bad-uuid-1", "bad-uuid-2"]})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_missing_role_returns_404():
    """11. Non-existent role returns structured 404."""
    db = SessionLocal()
    real_role = db.query(JobRole).first()
    db.close()

    fake_id = str(uuid.uuid4())
    res = client.post("/api/v1/intelligence/roles/compare", json={"role_ids": [str(real_role.id), fake_id]})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"

    res_signals = client.get(f"/api/v1/intelligence/roles/{fake_id}/signals")
    assert res_signals.status_code == 404
    assert res_signals.json()["error"]["code"] == "NOT_FOUND"


def test_missing_skill_returns_404():
    """12. Non-existent skill returns structured 404 on skill across roles endpoint."""
    fake_skill = str(uuid.uuid4())
    res = client.get(f"/api/v1/intelligence/skills/{fake_skill}/roles")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


# -----------------------------------------------------------------------------
# 13-16: Growth Classification & Boundaries Tests
# -----------------------------------------------------------------------------

def test_growth_rising_classification():
    """13. growth_rate > 0.05 is classified as RISING."""
    assert classify_growth(0.06) == "RISING"
    assert classify_growth(0.25) == "RISING"
    assert classify_growth(0.051) == "RISING"


def test_growth_stable_classification():
    """14. -0.05 <= growth_rate <= 0.05 is classified as STABLE."""
    assert classify_growth(0.05) == "STABLE"
    assert classify_growth(0.0) == "STABLE"
    assert classify_growth(-0.05) == "STABLE"
    assert classify_growth(0.02) == "STABLE"


def test_growth_declining_classification():
    """15. growth_rate < -0.05 is classified as DECLINING."""
    assert classify_growth(-0.06) == "DECLINING"
    assert classify_growth(-0.20) == "DECLINING"


def test_growth_boundary_values():
    """16. Exact boundary values are correctly classified."""
    # Boundary +0.05 is STABLE
    assert classify_growth(0.05) == "STABLE"
    # Boundary -0.05 is STABLE
    assert classify_growth(-0.05) == "STABLE"
    # Epsilon above is RISING
    assert classify_growth(0.05001) == "RISING"
    # Epsilon below is DECLINING
    assert classify_growth(-0.05001) == "DECLINING"


# -----------------------------------------------------------------------------
# 17-19: Market Signals, Fastest Growing & Deterministic Tie-Breaking Tests
# -----------------------------------------------------------------------------

def test_role_market_signals():
    """17. Market signals endpoint returns total skills, averages, and trend counts."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    db.close()

    res = client.get(f"/api/v1/intelligence/roles/{role.id}/signals")
    assert res.status_code == 200
    body = res.json()["data"]
    metrics = body["metrics"]
    assert metrics["total_demanded_skills"] == 13
    assert metrics["average_demand_score"] == 0.58
    assert metrics["highest_demand_score"] == 0.78
    assert metrics["rising_skill_count"] >= 5
    assert len(body["top_demanded_skills"]) <= 5
    assert len(body["fastest_growing_skills"]) <= 5


def test_fastest_growing_skills():
    """18. Fastest growing skills are ordered by growth_rate DESC."""
    db = SessionLocal()
    role = db.query(JobRole).filter(JobRole.slug == "backend-engineer").first()
    db.close()

    res = client.get(f"/api/v1/intelligence/roles/{role.id}/signals")
    assert res.status_code == 200
    fastest = res.json()["data"]["fastest_growing_skills"]
    assert len(fastest) == 5
    growths = [s["growth_rate"] for s in fastest]
    assert growths == sorted(growths, reverse=True)
    # FastAPI has +15% growth rate
    assert fastest[0]["canonical_slug"] == "fastapi"
    assert fastest[0]["growth_rate"] == 0.15


def test_deterministic_tie_breaking():
    """19. Demand trends endpoint guarantees deterministic stable ordering."""
    res = client.get("/api/v1/intelligence/trends?limit=30")
    assert res.status_code == 200
    data = res.json()["data"]
    for i in range(len(data) - 1):
        curr = data[i]
        nxt = data[i + 1]
        assert curr["growth_rate"] >= nxt["growth_rate"]
        if curr["growth_rate"] == nxt["growth_rate"]:
            assert curr["demand_score"] >= nxt["demand_score"]
            if curr["demand_score"] == nxt["demand_score"]:
                assert curr["skill_name"] <= nxt["skill_name"]


# -----------------------------------------------------------------------------
# 20-23: Pagination, Global Ownership & Regression Tests
# -----------------------------------------------------------------------------

def test_pagination_bounds():
    """20. Hardened pagination bounds on intelligence endpoints."""
    # Negative offset
    assert client.get("/api/v1/intelligence/skills/ranking?offset=-1").status_code == 422
    # Zero limit
    assert client.get("/api/v1/intelligence/skills/ranking?limit=0").status_code == 422
    # Excessive limit (> 100)
    assert client.get("/api/v1/intelligence/skills/ranking?limit=101").status_code == 422


def test_global_data_not_user_scoped():
    """21. Intelligence endpoints return canonical global data regardless of user headers."""
    res1 = client.get("/api/v1/intelligence/skills/ranking?limit=5")
    res2 = client.get("/api/v1/intelligence/skills/ranking?limit=5", headers={"X-User-Id": str(uuid.uuid4())})
    assert res1.json()["data"] == res2.json()["data"]


def test_empty_demand_dataset_behavior():
    """22. Querying for an unused location safely returns empty list with valid metadata."""
    res = client.get("/api/v1/intelligence/skills/ranking?location=Antarctica")
    assert res.status_code == 200
    body = res.json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0


def test_existing_demand_endpoints_regression():
    """23. Existing /roles and /demand endpoints continue functioning without alteration."""
    assert client.get("/api/v1/roles").status_code == 200
    assert client.get("/api/v1/demand").status_code == 200
    assert client.get("/api/v1/demand/audit/quality").status_code == 200
