from datetime import datetime, timezone
from unittest.mock import MagicMock
import uuid
import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from app.main import app
from app.db.database import SessionLocal
from app.db.models import JobRole, Skill, MarketSkillDemandSnapshot
from app.services.demand_service import demand_service, get_market_data_freshness

client = TestClient(app)


# -----------------------------------------------------------------------------
# 1-4: Unit Tests for get_market_data_freshness Helper
# -----------------------------------------------------------------------------

def test_get_market_data_freshness_fallback_when_no_snapshots():
    """1. When no snapshots exist in DB, fallback '2026-09-01' is returned."""
    mock_db = MagicMock()
    mock_query = mock_db.query.return_value
    mock_order = mock_query.order_by.return_value
    mock_order.first.return_value = None

    freshness = get_market_data_freshness(mock_db)
    assert freshness == "2026-09-01"


def test_get_market_data_freshness_single_snapshot():
    """2. When a snapshot exists, return snapshot date as YYYY-MM-DD."""
    mock_db = MagicMock()
    mock_query = mock_db.query.return_value
    mock_order = mock_query.order_by.return_value
    dt = datetime(2026, 9, 12, 16, 24, 4, tzinfo=timezone.utc)
    mock_order.first.return_value = (dt,)

    freshness = get_market_data_freshness(mock_db)
    assert freshness == "2026-09-12"


def test_get_market_data_freshness_multiple_snapshots_picks_newest():
    """3. Queries ORDER BY snapshot_at DESC LIMIT 1 so newest snapshot is chosen."""
    mock_db = MagicMock()
    mock_query = mock_db.query.return_value
    mock_order = mock_query.order_by.return_value
    newest_dt = datetime(2026, 9, 15, 10, 0, 0, tzinfo=timezone.utc)
    mock_order.first.return_value = (newest_dt,)

    freshness = get_market_data_freshness(mock_db)
    assert freshness == "2026-09-15"
    mock_query.order_by.assert_called_once()
    mock_order.first.assert_called_once()


def test_demand_service_delegates_to_module_helper():
    """4. DemandService.get_market_data_freshness delegates to get_market_data_freshness."""
    mock_db = MagicMock()
    mock_query = mock_db.query.return_value
    mock_order = mock_query.order_by.return_value
    dt = datetime(2026, 9, 12, 16, 24, 4, tzinfo=timezone.utc)
    mock_order.first.return_value = (dt,)

    res_service = demand_service.get_market_data_freshness(mock_db)
    res_helper = get_market_data_freshness(mock_db)
    assert res_service == res_helper == "2026-09-12"


# -----------------------------------------------------------------------------
# 5-12: API Integration Tests (Verify Real DB Dynamic Freshness)
# -----------------------------------------------------------------------------

def test_list_industry_demand_dynamic_freshness():
    """5. GET /api/v1/demand returns dynamic data_freshness matching snapshot helper."""
    db = SessionLocal()
    try:
        expected_freshness = demand_service.get_market_data_freshness(db)
    finally:
        db.close()

    res = client.get("/api/v1/demand?limit=5")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["data_freshness"] == expected_freshness


def test_role_demand_detail_dynamic_freshness():
    """6. GET /api/v1/demand/{role_id} returns dynamic data_freshness."""
    db = SessionLocal()
    try:
        expected_freshness = demand_service.get_market_data_freshness(db)
        role = db.query(JobRole).first()
        assert role is not None, "A canonical job role must exist"
        role_id = str(role.id)
    finally:
        db.close()

    res = client.get(f"/api/v1/demand/{role_id}")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["data_freshness"] == expected_freshness


def test_skill_ranking_dynamic_freshness():
    """7. GET /api/v1/intelligence/skills/ranking returns dynamic data_freshness."""
    db = SessionLocal()
    try:
        expected_freshness = demand_service.get_market_data_freshness(db)
    finally:
        db.close()

    res = client.get("/api/v1/intelligence/skills/ranking?limit=10")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["data_freshness"] == expected_freshness


def test_skill_across_roles_dynamic_freshness():
    """8. GET /api/v1/intelligence/skills/{skill_id}/roles returns dynamic data_freshness."""
    db = SessionLocal()
    try:
        expected_freshness = demand_service.get_market_data_freshness(db)
        skill = db.query(Skill).first()
        assert skill is not None, "A canonical skill must exist"
        skill_id = str(skill.id)
    finally:
        db.close()

    res = client.get(f"/api/v1/intelligence/skills/{skill_id}/roles")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["data_freshness"] == expected_freshness


def test_compare_job_roles_dynamic_freshness():
    """9. POST /api/v1/intelligence/roles/compare returns dynamic data_freshness."""
    db = SessionLocal()
    try:
        expected_freshness = demand_service.get_market_data_freshness(db)
        roles = db.query(JobRole).limit(2).all()
        assert len(roles) >= 2, "At least two canonical job roles required"
        role_ids = [str(r.id) for r in roles]
    finally:
        db.close()

    res = client.post(
        "/api/v1/intelligence/roles/compare",
        json={"role_ids": role_ids, "location": "India"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["data_freshness"] == expected_freshness


def test_role_signals_dynamic_freshness():
    """10. GET /api/v1/intelligence/roles/{role_id}/signals returns dynamic data_freshness."""
    db = SessionLocal()
    try:
        expected_freshness = demand_service.get_market_data_freshness(db)
        role = db.query(JobRole).first()
        role_id = str(role.id)
    finally:
        db.close()

    res = client.get(f"/api/v1/intelligence/roles/{role_id}/signals")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["data_freshness"] == expected_freshness


def test_demand_trends_dynamic_freshness():
    """11. GET /api/v1/intelligence/trends returns dynamic data_freshness."""
    db = SessionLocal()
    try:
        expected_freshness = demand_service.get_market_data_freshness(db)
    finally:
        db.close()

    res = client.get("/api/v1/intelligence/trends?limit=10")
    assert res.status_code == 200
    body = res.json()
    assert body["meta"]["data_freshness"] == expected_freshness


def test_audit_demand_quality_dynamic_freshness():
    """12. GET /api/v1/demand/audit/quality returns dynamic data_freshness."""
    db = SessionLocal()
    try:
        expected_freshness = demand_service.get_market_data_freshness(db)
    finally:
        db.close()

    res = client.get("/api/v1/demand/audit/quality")
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["data_freshness"] == expected_freshness


# -----------------------------------------------------------------------------
# 13: Response Envelope Shape Invariants
# -----------------------------------------------------------------------------

def test_api_response_envelope_shapes_preserved():
    """13. Ensure public API response envelope shapes and types remain unchanged."""
    res_demand = client.get("/api/v1/demand?limit=2")
    assert res_demand.status_code == 200
    meta_demand = res_demand.json()["meta"]
    assert isinstance(meta_demand["data_freshness"], str)
    assert isinstance(meta_demand["total"], int)
    assert isinstance(meta_demand["limit"], int)
    assert isinstance(meta_demand["offset"], int)
    assert isinstance(meta_demand["location"], str)

    res_ranking = client.get("/api/v1/intelligence/skills/ranking?limit=2")
    assert res_ranking.status_code == 200
    meta_ranking = res_ranking.json()["meta"]
    assert isinstance(meta_ranking["data_freshness"], str)
    assert isinstance(meta_ranking["total"], int)
    assert isinstance(meta_ranking["location"], str)


# -----------------------------------------------------------------------------
# 14: Demand Calculations Invariants
# -----------------------------------------------------------------------------

def test_demand_calculations_unaltered():
    """14. Demand scores, sample sizes, and aggregates remain untouched."""
    db = SessionLocal()
    try:
        role = db.query(JobRole).first()
        aggregates = demand_service.get_role_demand_aggregates(db, role.id, "India")
    finally:
        db.close()

    assert "total_demanded_skills" in aggregates
    assert "average_demand_score" in aggregates
    assert 0.0 <= aggregates["average_demand_score"] <= 1.0


# -----------------------------------------------------------------------------
# 15: Frontend Badge Hardcoded Literal Verification
# -----------------------------------------------------------------------------

def test_frontend_has_no_hardcoded_badge_literal():
    """15. Frontend DemandIntelligenceExplorer badge must render dynamic state, not literal '2026-09-01'."""
    repo_root = Path(__file__).resolve().parent.parent
    frontend_explorer = repo_root.parent / "frontend" / "src" / "components" / "DemandIntelligenceExplorer.tsx"
    assert frontend_explorer.exists(), f"File {frontend_explorer} must exist"

    content = frontend_explorer.read_text(encoding="utf-8")

    # Hardcoded literal must NOT exist in the badge
    assert 'Freshness: <strong className="text-slate-800 dark:text-slate-200 font-mono">2026-09-01</strong>' not in content

    # Dynamic state must be rendered in the badge
    assert 'Freshness: <strong className="text-slate-800 dark:text-slate-200 font-mono">{dataFreshness}</strong>' in content

    # State update must be present from API meta
    assert "setDataFreshness(res.data.meta.data_freshness)" in content
