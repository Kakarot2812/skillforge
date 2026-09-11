"""
Unit and integration tests for Historical Market Demand Growth & 24-Hour Refresh (Post-MVP Checkpoint P1-F).

Verifies all 35 required specifications across:
1. SNAPSHOTS (1-10):
   - First snapshot inserts records
   - Second snapshot preserves first snapshot
   - Identical timestamp snapshot is idempotent
   - Conflicting identical timestamp snapshot is rejected
   - Source isolation
   - Canonical skill ID identity
   - Timestamp persistence
   - Empty snapshot
   - Zero jobs
   - Zero skill relationships

2. GROWTH (11-22):
   - Positive growth
   - Negative growth
   - Zero growth
   - Previous score zero / current positive (zero-base rule)
   - Previous score zero / current zero
   - Different sources remain isolated
   - No previous snapshot handled deterministically
   - Latest vs immediately previous snapshot
   - RISING boundary
   - STABLE boundary
   - DECLINING boundary
   - Repeated calculation deterministic

3. REFRESH & SAFETY (23-35):
   - Successful refresh
   - Refresh skipped within 24 hours
   - force=True bypasses refresh interval
   - Failed upstream fetch preserves last known-good state
   - Failed later stage does not destroy historical state
   - Historical snapshots are never deleted
   - MVP skill_demand unchanged (strictly 49 rows)
   - skill_gaps unchanged
   - priorities unchanged
   - Credentials never appear in metrics
   - Authorization headers never appear in metrics/logs
   - Refresh ordering
   - Transaction rollback
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from unittest.mock import MagicMock, patch
import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import (
    IndustrySkillDemand,
    JobRole,
    MarketJob,
    MarketJobSkill,
    MarketSkillDemand,
    MarketSkillDemandGrowth,
    MarketSkillDemandSnapshot,
    Skill,
    SkillGap,
)
from app.services.market.clients.adzuna_client import AdzunaAPIError
from app.services.market.demand.aggregator import (
    MarketDemandAggregator,
    aggregate_market_demand,
)
from app.services.market.demand.growth import (
    MarketDemandGrowthService,
    MarketSkillDemandGrowthRepository,
    calculate_growth_rate,
    classify_growth_rate,
)
from app.services.market.demand.refresh import (
    MarketDemandRefreshService,
    refresh_market_demand,
)
from app.services.market.demand.snapshots import (
    MarketDemandSnapshotConflictError,
    MarketDemandSnapshotService,
    MarketSkillDemandSnapshotRepository,
)
from app.services.market.models import (
    AdzunaIngestionResult,
    MarketDemandGrowthRecord,
    MarketDemandRefreshResult,
    MarketDemandSnapshotRecord,
    NormalizedMarketJob,
)
from app.services.market.pipeline import MarketPipelineResult


@pytest.fixture
def db():
    """Provides a transactional database session and cleans up test records."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Clean up test growth, snapshots, demand, and jobs
        session.query(MarketSkillDemandGrowth).filter(MarketSkillDemandGrowth.source.like("test_%")).delete(synchronize_session=False)
        session.query(MarketSkillDemandSnapshot).filter(MarketSkillDemandSnapshot.source.like("test_%")).delete(synchronize_session=False)
        session.query(MarketSkillDemand).filter(MarketSkillDemand.source.like("test_%")).delete(synchronize_session=False)
        session.query(MarketJob).filter(MarketJob.source.like("test_%")).delete(synchronize_session=False)
        session.commit()
        session.close()


def _create_test_job(db: Session, source: str, title: str, ext_id: str) -> MarketJob:
    """Helper to create and persist a test market job."""
    job = MarketJob(
        id=uuid.uuid4(),
        source=source,
        external_job_id=ext_id,
        title=title,
        description=f"Description for {title}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _add_job_skill(
    db: Session,
    market_job_id: uuid.UUID,
    skill_id: uuid.UUID,
    alias: str = "test-alias",
    source_field: str = "title",
) -> MarketJobSkill:
    """Helper to associate a canonical skill with a market job."""
    mjs = MarketJobSkill(
        id=uuid.uuid4(),
        market_job_id=market_job_id,
        skill_id=skill_id,
        matched_alias=alias,
        source_field=source_field,
        evidence_text=f"Evidence for {alias}",
        extraction_method="deterministic_taxonomy_match",
        confidence_score=1.0,
    )
    db.add(mjs)
    db.commit()
    db.refresh(mjs)
    return mjs


# ===========================================================================
# 1. SNAPSHOT TESTS (1 - 10)
# ===========================================================================

def test_1_first_snapshot_inserts_records(db: Session):
    """1. First snapshot captures current demand and inserts snapshot records."""
    source = "test_snap_1"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    assert skill is not None

    j1 = _create_test_job(db, source, "Python Dev 1", "e1")
    _add_job_skill(db, j1.id, skill.id)

    # Run P1-E aggregation
    aggregate_market_demand(db=db, source=source)

    # Capture snapshot
    snapshot_service = MarketDemandSnapshotService()
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    entities, ins, unc = snapshot_service.create_snapshot_from_current_demand(
        db=db, source=source, snapshot_at=t1
    )

    assert ins == 1
    assert unc == 0
    assert len(entities) == 1
    assert entities[0].skill_id == skill.id
    assert entities[0].demand_score == 1.0
    assert entities[0].snapshot_at == t1


def test_2_second_snapshot_preserves_first_snapshot(db: Session):
    """2. Second snapshot at a later timestamp preserves first snapshot unchanged."""
    source = "test_snap_2"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    j1 = _create_test_job(db, source, "Python Dev 1", "e1")
    _add_job_skill(db, j1.id, skill.id)
    aggregate_market_demand(db=db, source=source)

    snapshot_service = MarketDemandSnapshotService()
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    snapshot_service.create_snapshot_from_current_demand(db=db, source=source, snapshot_at=t1)

    # Add second job without python (so python demand drops to 0.50)
    _create_test_job(db, source, "Other Dev", "e2")
    aggregate_market_demand(db=db, source=source)

    t2 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    snapshot_service.create_snapshot_from_current_demand(db=db, source=source, snapshot_at=t2)

    # Both snapshots exist independently
    snap_t1 = snapshot_service.get_snapshots_at(db=db, snapshot_at=t1, source=source)
    snap_t2 = snapshot_service.get_snapshots_at(db=db, snapshot_at=t2, source=source)

    assert len(snap_t1) == 1
    assert len(snap_t2) == 1
    assert snap_t1[0].demand_score == 1.0  # preserved!
    assert snap_t2[0].demand_score == 0.5  # updated in second snapshot!
    assert snap_t1[0].id != snap_t2[0].id


def test_3_identical_timestamp_snapshot_is_idempotent(db: Session):
    """3. Resubmitting identical snapshot at same timestamp is idempotent."""
    source = "test_snap_3"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    j1 = _create_test_job(db, source, "Python Dev", "e1")
    _add_job_skill(db, j1.id, skill.id)
    aggregate_market_demand(db=db, source=source)

    snapshot_service = MarketDemandSnapshotService()
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

    # First submission
    _, ins1, unc1 = snapshot_service.create_snapshot_from_current_demand(db=db, source=source, snapshot_at=t1)
    assert ins1 == 1
    assert unc1 == 0

    # Second submission with exact same data
    _, ins2, unc2 = snapshot_service.create_snapshot_from_current_demand(db=db, source=source, snapshot_at=t1)
    assert ins2 == 0
    assert unc2 == 1

    # Total rows in table remains 1
    rows = snapshot_service.get_snapshots_at(db=db, snapshot_at=t1, source=source)
    assert len(rows) == 1


def test_4_conflicting_identical_timestamp_snapshot_is_rejected(db: Session):
    """4. Submitting conflicting data for same (source, snapshot_at) raises MarketDemandSnapshotConflictError."""
    source = "test_snap_4"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    repo = MarketSkillDemandSnapshotRepository()
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

    # Insert initial snapshot
    rec1 = MarketDemandSnapshotRecord(
        skill_id=skill.id,
        source=source,
        job_count=5,
        sample_size=10,
        demand_share=0.5,
        demand_score=0.5,
        snapshot_at=t1,
    )
    repo.persist_snapshot([rec1], source=source, snapshot_at=t1, db=db)
    db.commit()

    # Attempt to submit conflicting snapshot with different score for same timestamp
    rec_conflict = MarketDemandSnapshotRecord(
        skill_id=skill.id,
        source=source,
        job_count=9,
        sample_size=10,
        demand_share=0.9,
        demand_score=0.9,
        snapshot_at=t1,
    )

    with pytest.raises(MarketDemandSnapshotConflictError):
        repo.persist_snapshot([rec_conflict], source=source, snapshot_at=t1, db=db)

    # Historical truth preserved
    snaps = repo.get_snapshots_at(db=db, snapshot_at=t1, source=source)
    assert snaps[0].demand_score == 0.5


def test_5_source_isolation_snapshots(db: Session):
    """5. Snapshots from different sources remain strictly isolated."""
    source_a = "test_source_a"
    source_b = "test_source_b"
    skill = db.query(Skill).filter(Skill.slug == "python").first()

    j_a = _create_test_job(db, source_a, "Job A", "ea1")
    _add_job_skill(db, j_a.id, skill.id)
    aggregate_market_demand(db=db, source=source_a)

    j_b = _create_test_job(db, source_b, "Job B", "eb1")
    _add_job_skill(db, j_b.id, skill.id)
    aggregate_market_demand(db=db, source=source_b)

    snapshot_service = MarketDemandSnapshotService()
    t = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    snapshot_service.create_snapshot_from_current_demand(db=db, source=source_a, snapshot_at=t)
    snapshot_service.create_snapshot_from_current_demand(db=db, source=source_b, snapshot_at=t)

    snaps_a = snapshot_service.get_snapshots_at(db=db, snapshot_at=t, source=source_a)
    snaps_b = snapshot_service.get_snapshots_at(db=db, snapshot_at=t, source=source_b)

    assert len(snaps_a) == 1
    assert len(snaps_b) == 1
    assert snaps_a[0].source == source_a
    assert snaps_b[0].source == source_b
    assert snaps_a[0].id != snaps_b[0].id


def test_6_canonical_skill_id_identity(db: Session):
    """6. Snapshot strictly references canonical Skill.id UUID."""
    source = "test_snap_canonical"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    j1 = _create_test_job(db, source, "Job 1", "e1")
    _add_job_skill(db, j1.id, skill.id)
    aggregate_market_demand(db=db, source=source)

    snapshot_service = MarketDemandSnapshotService()
    entities, _, _ = snapshot_service.create_snapshot_from_current_demand(db=db, source=source)
    assert entities[0].skill_id == skill.id

    # Verify FK constraint integrity
    raw_row = db.query(MarketSkillDemandSnapshot).filter(MarketSkillDemandSnapshot.id == entities[0].id).first()
    assert raw_row.skill.name == "Python"


def test_7_timestamp_persistence(db: Session):
    """7. Snapshots persist explicit timestamps and allow retrieval in reverse chronological order."""
    source = "test_snap_timestamps"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    j1 = _create_test_job(db, source, "Job 1", "e1")
    _add_job_skill(db, j1.id, skill.id)
    aggregate_market_demand(db=db, source=source)

    snapshot_service = MarketDemandSnapshotService()
    t1 = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 8, 25, 12, 0, 0, tzinfo=timezone.utc)

    snapshot_service.create_snapshot_from_current_demand(db=db, source=source, snapshot_at=t1)
    snapshot_service.create_snapshot_from_current_demand(db=db, source=source, snapshot_at=t2)
    snapshot_service.create_snapshot_from_current_demand(db=db, source=source, snapshot_at=t3)

    timestamps = snapshot_service.get_latest_snapshot_timestamps(db=db, source=source, limit=2)
    assert len(timestamps) == 2
    assert timestamps[0] == t3
    assert timestamps[1] == t2


def test_8_empty_snapshot(db: Session):
    """8. Creating snapshot when no demand records exist creates 0 rows cleanly."""
    source = "test_snap_empty"
    snapshot_service = MarketDemandSnapshotService()
    entities, ins, unc = snapshot_service.create_snapshot_from_current_demand(db=db, source=source)
    assert len(entities) == 0
    assert ins == 0
    assert unc == 0


def test_9_zero_jobs_snapshot(db: Session):
    """9. Zero jobs in database produces empty snapshot cleanly."""
    source = "test_snap_zero_jobs"
    aggregate_market_demand(db=db, source=source)
    snapshot_service = MarketDemandSnapshotService()
    entities, ins, unc = snapshot_service.create_snapshot_from_current_demand(db=db, source=source)
    assert len(entities) == 0
    assert ins == 0


def test_10_zero_skill_relationships_snapshot(db: Session):
    """10. Market jobs exist but have zero extracted skills produces empty snapshot."""
    source = "test_snap_zero_skills"
    _create_test_job(db, source, "Generic Job Without Skills", "e1")
    aggregate_market_demand(db=db, source=source)
    snapshot_service = MarketDemandSnapshotService()
    entities, ins, unc = snapshot_service.create_snapshot_from_current_demand(db=db, source=source)
    assert len(entities) == 0


# ===========================================================================
# 2. GROWTH TESTS (11 - 22)
# ===========================================================================

def test_11_positive_growth():
    """11. Positive growth calculation: 0.20 -> 0.30 is +0.5000 (RISING)."""
    rate = calculate_growth_rate(current_demand_score=0.30, previous_demand_score=0.20)
    assert rate == 0.5000
    assert classify_growth_rate(rate) == "RISING"


def test_12_negative_growth():
    """12. Negative growth calculation: 0.40 -> 0.20 is -0.5000 (DECLINING)."""
    rate = calculate_growth_rate(current_demand_score=0.20, previous_demand_score=0.40)
    assert rate == -0.5000
    assert classify_growth_rate(rate) == "DECLINING"


def test_13_zero_growth():
    """13. Zero growth calculation: 0.25 -> 0.25 is 0.0000 (STABLE)."""
    rate = calculate_growth_rate(current_demand_score=0.25, previous_demand_score=0.25)
    assert rate == 0.0000
    assert classify_growth_rate(rate) == "STABLE"


def test_14_previous_score_zero_current_positive():
    """14. Zero base rule: previous=0.0 and current > 0 yields 1.0 (RISING)."""
    rate = calculate_growth_rate(current_demand_score=0.15, previous_demand_score=0.0)
    assert rate == 1.0
    assert classify_growth_rate(rate) == "RISING"


def test_15_previous_score_zero_current_zero():
    """15. Zero base rule: previous=0.0 and current=0.0 yields 0.0 (STABLE)."""
    rate = calculate_growth_rate(current_demand_score=0.0, previous_demand_score=0.0)
    assert rate == 0.0
    assert classify_growth_rate(rate) == "STABLE"


def test_16_different_sources_remain_isolated_growth(db: Session):
    """16. Growth is strictly computed within the same source."""
    source_x = "test_src_x"
    source_y = "test_src_y"
    skill = db.query(Skill).filter(Skill.slug == "python").first()

    # Source X: 2 snapshots
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    repo = MarketSkillDemandSnapshotRepository()

    rec_x1 = MarketDemandSnapshotRecord(skill_id=skill.id, source=source_x, job_count=2, sample_size=10, demand_share=0.2, demand_score=0.20, snapshot_at=t1)
    rec_x2 = MarketDemandSnapshotRecord(skill_id=skill.id, source=source_x, job_count=3, sample_size=10, demand_share=0.3, demand_score=0.30, snapshot_at=t2)
    repo.persist_snapshot([rec_x1], source=source_x, snapshot_at=t1, db=db)
    repo.persist_snapshot([rec_x2], source=source_x, snapshot_at=t2, db=db)

    # Source Y: 1 snapshot with 0.80
    rec_y1 = MarketDemandSnapshotRecord(skill_id=skill.id, source=source_y, job_count=8, sample_size=10, demand_share=0.8, demand_score=0.80, snapshot_at=t2)
    repo.persist_snapshot([rec_y1], source=source_y, snapshot_at=t2, db=db)
    db.commit()

    growth_service = MarketDemandGrowthService()
    records_x, _, _, _ = growth_service.compute_and_persist_growth(db=db, source=source_x)
    assert len(records_x) == 1
    assert records_x[0].growth_rate == 0.5000  # (0.30 - 0.20) / 0.20, NOT influenced by Source Y's 0.80!

    records_y, _, _, _ = growth_service.compute_and_persist_growth(db=db, source=source_y)
    assert len(records_y) == 1
    assert records_y[0].growth_rate == 0.0  # single snapshot in Y -> STABLE, baseline 0.0


def test_17_no_previous_snapshot_handled_deterministically(db: Session):
    """17. If no previous snapshot exists, growth is deterministically 0.0 (STABLE) without fabrication."""
    source = "test_single_snap"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    repo = MarketSkillDemandSnapshotRepository()
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

    rec = MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=2, sample_size=10, demand_share=0.2, demand_score=0.20, snapshot_at=t1)
    repo.persist_snapshot([rec], source=source, snapshot_at=t1, db=db)
    db.commit()

    growth_service = MarketDemandGrowthService()
    records, ins, upd, unc = growth_service.compute_and_persist_growth(db=db, source=source)
    assert len(records) == 1
    assert records[0].previous_snapshot_id is None
    assert records[0].previous_demand_score == 0.0
    assert records[0].current_demand_score == 0.20
    assert records[0].growth_rate == 0.0
    assert records[0].growth_class == "STABLE"


def test_18_latest_vs_immediately_previous_snapshot(db: Session):
    """18. Growth compares latest snapshot against immediately preceding snapshot (T3 vs T2, not T1)."""
    source = "test_three_snaps"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    repo = MarketSkillDemandSnapshotRepository()

    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)  # score: 0.10
    t2 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)  # score: 0.20
    t3 = datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc)  # score: 0.25

    repo.persist_snapshot([MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=1, sample_size=10, demand_share=0.1, demand_score=0.10, snapshot_at=t1)], source=source, snapshot_at=t1, db=db)
    repo.persist_snapshot([MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=2, sample_size=10, demand_share=0.2, demand_score=0.20, snapshot_at=t2)], source=source, snapshot_at=t2, db=db)
    repo.persist_snapshot([MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=2, sample_size=8, demand_share=0.25, demand_score=0.25, snapshot_at=t3)], source=source, snapshot_at=t3, db=db)
    db.commit()

    growth_service = MarketDemandGrowthService()
    records, _, _, _ = growth_service.compute_and_persist_growth(db=db, source=source)
    assert len(records) == 1
    # Compared T3 (0.25) vs T2 (0.20) -> (0.25 - 0.20) / 0.20 = 0.05 / 0.20 = 0.25 (+25%)
    assert records[0].previous_demand_score == 0.20
    assert records[0].current_demand_score == 0.25
    assert records[0].growth_rate == 0.2500
    assert records[0].growth_class == "RISING"


def test_19_rising_boundary():
    """19. Growth classification boundary tests for RISING."""
    assert classify_growth_rate(0.06) == "RISING"
    assert classify_growth_rate(0.051) == "RISING"
    assert classify_growth_rate(0.05001) == "RISING"


def test_20_stable_boundary():
    """20. Growth classification boundary tests for STABLE."""
    assert classify_growth_rate(0.05) == "STABLE"
    assert classify_growth_rate(0.00) == "STABLE"
    assert classify_growth_rate(-0.05) == "STABLE"
    assert classify_growth_rate(0.02) == "STABLE"
    assert classify_growth_rate(-0.02) == "STABLE"


def test_21_declining_boundary():
    """21. Growth classification boundary tests for DECLINING."""
    assert classify_growth_rate(-0.05001) == "DECLINING"
    assert classify_growth_rate(-0.051) == "DECLINING"
    assert classify_growth_rate(-0.06) == "DECLINING"
    assert classify_growth_rate(-0.50) == "DECLINING"


def test_22_repeated_calculation_deterministic(db: Session):
    """22. Repeated calculation on same snapshots updates existing growth records in-place without duplicating."""
    source = "test_repeat_growth"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    repo = MarketSkillDemandSnapshotRepository()

    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    repo.persist_snapshot([MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=2, sample_size=10, demand_share=0.2, demand_score=0.20, snapshot_at=t1)], source=source, snapshot_at=t1, db=db)
    repo.persist_snapshot([MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=3, sample_size=10, demand_share=0.3, demand_score=0.30, snapshot_at=t2)], source=source, snapshot_at=t2, db=db)
    db.commit()

    growth_service = MarketDemandGrowthService()
    # First computation: inserts
    _, ins1, upd1, unc1 = growth_service.compute_and_persist_growth(db=db, source=source)
    assert ins1 == 1
    assert upd1 == 0

    # Second computation: unchanged / idempotent
    _, ins2, upd2, unc2 = growth_service.compute_and_persist_growth(db=db, source=source)
    assert ins2 == 0
    assert unc2 == 1

    # Only 1 record in growth table for this (source, skill_id)
    growth_records = growth_service.repository.get_growth_for_source(db=db, source=source)
    assert len(growth_records) == 1


# ===========================================================================
# 3. REFRESH & SAFETY TESTS (23 - 35)
# ===========================================================================

def test_23_successful_refresh(db: Session):
    """23. Full refresh sequence completes successfully and returns structured metrics."""
    source = "test_refresh_succ"
    skill = db.query(Skill).filter(Skill.slug == "python").first()

    mock_pipeline = MagicMock()
    mock_pipeline.run_pipeline.return_value = MarketPipelineResult(
        source=source,
        raw_jobs_seen=2,
        valid_jobs=2,
        final_jobs_count=2,
        inserted=2,
    )

    # Insert a real test job and skill so extraction/aggregation/snapshots have data
    j = _create_test_job(db, source, "Python Lead", "e1")
    _add_job_skill(db, j.id, skill.id)

    refresh_service = MarketDemandRefreshService(pipeline=mock_pipeline)
    result = refresh_service.refresh(db=db, source=source, force=True)

    assert result.refreshed is True
    assert result.reason == "completed"
    assert result.snapshot_records_created >= 1
    assert result.growth_records_computed >= 1
    assert result.error is None


def test_24_refresh_skipped_within_24_hours(db: Session):
    """24. Refresh is skipped without network/pipeline calls if latest snapshot < 24h old and force=False."""
    source = "test_refresh_skip"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    repo = MarketSkillDemandSnapshotRepository()

    recent_time = datetime.now(timezone.utc) - timedelta(hours=2)
    repo.persist_snapshot(
        [MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=1, sample_size=5, demand_share=0.2, demand_score=0.20, snapshot_at=recent_time)],
        source=source,
        snapshot_at=recent_time,
        db=db,
    )
    db.commit()

    mock_pipeline = MagicMock()
    refresh_service = MarketDemandRefreshService(pipeline=mock_pipeline)

    result = refresh_service.refresh(db=db, source=source, force=False)

    assert result.refreshed is False
    assert result.reason == "skipped_within_24h"
    # Guaranteed NO pipeline / network calls executed!
    mock_pipeline.run_pipeline.assert_not_called()


def test_25_force_true_bypasses_refresh_interval(db: Session):
    """25. force=True bypasses the 24-hour interval policy and executes refresh."""
    source = "test_refresh_force"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    repo = MarketSkillDemandSnapshotRepository()

    recent_time = datetime.now(timezone.utc) - timedelta(hours=1)
    repo.persist_snapshot(
        [MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=1, sample_size=5, demand_share=0.2, demand_score=0.20, snapshot_at=recent_time)],
        source=source,
        snapshot_at=recent_time,
        db=db,
    )
    db.commit()

    mock_pipeline = MagicMock()
    mock_pipeline.run_pipeline.return_value = MarketPipelineResult(
        source=source, raw_jobs_seen=1, valid_jobs=1, final_jobs_count=1, inserted=1
    )

    refresh_service = MarketDemandRefreshService(pipeline=mock_pipeline)
    result = refresh_service.refresh(db=db, source=source, force=True)

    assert result.refreshed is True
    assert result.reason == "completed"
    mock_pipeline.run_pipeline.assert_called_once()


def test_26_failed_upstream_fetch_preserves_last_known_good_state(db: Session):
    """26. Upstream fetch failure preserves existing jobs, snapshots, and growth."""
    source = "test_refresh_fail_fetch"
    skill = db.query(Skill).filter(Skill.slug == "python").first()

    # Establish baseline known-good state
    j = _create_test_job(db, source, "Python Dev", "e1")
    _add_job_skill(db, j.id, skill.id)
    aggregate_market_demand(db=db, source=source)

    snap_service = MarketDemandSnapshotService()
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    snap_service.create_snapshot_from_current_demand(db=db, source=source, snapshot_at=t1)

    growth_service = MarketDemandGrowthService()
    growth_service.compute_and_persist_growth(db=db, source=source)
    db.commit()

    # Now run refresh with a failing pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.run_pipeline.side_effect = AdzunaAPIError("Simulated upstream network timeout")

    refresh_service = MarketDemandRefreshService(pipeline=mock_pipeline)
    result = refresh_service.refresh(db=db, source=source, force=True)

    assert result.refreshed is False
    assert "AdzunaAPIError" in result.reason

    # Verify baseline state is 100% preserved
    remaining_snaps = snap_service.get_snapshots_at(db=db, snapshot_at=t1, source=source)
    assert len(remaining_snaps) == 1
    assert remaining_snaps[0].demand_score == 1.0

    growth_recs = growth_service.repository.get_growth_for_source(db=db, source=source)
    assert len(growth_recs) == 1


def test_27_failed_later_stage_does_not_destroy_historical_state(db: Session):
    """27. Failure in a later stage (e.g. extraction) triggers rollback and preserves history."""
    source = "test_refresh_fail_later"
    skill = db.query(Skill).filter(Skill.slug == "python").first()

    snap_service = MarketDemandSnapshotService()
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)
    snap_repo = MarketSkillDemandSnapshotRepository()
    snap_repo.persist_snapshot(
        [MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=2, sample_size=5, demand_share=0.4, demand_score=0.40, snapshot_at=t1)],
        source=source,
        snapshot_at=t1,
        db=db,
    )
    db.commit()

    mock_pipeline = MagicMock()
    mock_pipeline.run_pipeline.return_value = MarketPipelineResult(source=source, final_jobs_count=1)

    mock_extraction = MagicMock()
    mock_extraction.process_persisted_jobs.side_effect = RuntimeError("Database serialization conflict")

    refresh_service = MarketDemandRefreshService(
        pipeline=mock_pipeline,
        extraction_service=mock_extraction,
    )
    result = refresh_service.refresh(db=db, source=source, force=True)

    assert result.refreshed is False
    assert "RuntimeError" in result.reason

    # Historical snapshot unchanged
    snaps = snap_service.get_snapshots_at(db=db, snapshot_at=t1, source=source)
    assert len(snaps) == 1
    assert snaps[0].demand_score == 0.40


def test_28_historical_snapshots_are_never_deleted(db: Session):
    """28. Verifies failure safety never invokes DELETE on market_skill_demand_snapshots."""
    source = "test_snap_no_delete"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    t1 = datetime(2026, 9, 1, 10, 0, 0, tzinfo=timezone.utc)

    snap_repo = MarketSkillDemandSnapshotRepository()
    snap_repo.persist_snapshot(
        [MarketDemandSnapshotRecord(skill_id=skill.id, source=source, job_count=1, sample_size=5, demand_share=0.2, demand_score=0.20, snapshot_at=t1)],
        source=source,
        snapshot_at=t1,
        db=db,
    )
    db.commit()

    # Fail intentionally
    mock_pipeline = MagicMock()
    mock_pipeline.run_pipeline.side_effect = Exception("Catastrophic error")

    refresh_service = MarketDemandRefreshService(pipeline=mock_pipeline)
    refresh_service.refresh(db=db, source=source, force=True)

    total_snapshots = snap_repo.count_snapshot_rows(db=db, source=source)
    assert total_snapshots == 1


def test_29_mvp_skill_demand_strictly_isolated_49_rows(db: Session):
    """29. MVP skill_demand table must remain strictly 49 rows and unchanged."""
    # Capture MVP baseline
    rows = db.query(IndustrySkillDemand).all()
    assert len(rows) == 49, f"Expected exactly 49 MVP skill_demand rows, found {len(rows)}"

    # Run snapshot and growth operations
    source = "test_snap_mvp_iso"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    j = _create_test_job(db, source, "Python Dev", "e1")
    _add_job_skill(db, j.id, skill.id)
    aggregate_market_demand(db=db, source=source)

    snap_service = MarketDemandSnapshotService()
    snap_service.create_snapshot_from_current_demand(db=db, source=source)
    growth_service = MarketDemandGrowthService()
    growth_service.compute_and_persist_growth(db=db, source=source)

    # Re-verify MVP table
    rows_after = db.query(IndustrySkillDemand).all()
    assert len(rows_after) == 49
    for r in rows_after:
        assert r.demand_score >= 0.0
        assert r.sample_size > 0


def test_30_skill_gaps_unchanged(db: Session):
    """30. P1-F operations do not touch or alter candidate skill_gaps."""
    initial_gap_count = db.query(SkillGap).count()

    source = "test_snap_gaps_iso"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    j = _create_test_job(db, source, "Python Dev", "e1")
    _add_job_skill(db, j.id, skill.id)
    aggregate_market_demand(db=db, source=source)

    snap_service = MarketDemandSnapshotService()
    snap_service.create_snapshot_from_current_demand(db=db, source=source)

    assert db.query(SkillGap).count() == initial_gap_count


def test_31_candidate_priorities_unchanged(db: Session):
    """31. P1-F operations do not touch or alter candidate priorities."""
    priorities_before = [
        (g.id, g.priority_score, g.priority_level) for g in db.query(SkillGap).all()
    ]

    source = "test_snap_priorities_iso"
    skill = db.query(Skill).filter(Skill.slug == "python").first()
    j = _create_test_job(db, source, "Python Dev", "e1")
    _add_job_skill(db, j.id, skill.id)
    aggregate_market_demand(db=db, source=source)

    growth_service = MarketDemandGrowthService()
    growth_service.compute_and_persist_growth(db=db, source=source)

    priorities_after = [
        (g.id, g.priority_score, g.priority_level) for g in db.query(SkillGap).all()
    ]
    assert priorities_before == priorities_after


def test_32_credentials_never_appear_in_metrics():
    """32. Audit metrics dictionary contains zero credentials, keys, or secrets."""
    res = MarketDemandRefreshResult(
        source="adzuna",
        refreshed=True,
        jobs_ingested=10,
        snapshot_records_created=5,
        growth_records_computed=5,
    )
    summary = res.to_summary_dict()
    serialized = str(summary).lower()

    assert "app_id" not in serialized
    assert "app_key" not in serialized
    assert "password" not in serialized
    assert "secret" not in serialized


def test_33_authorization_headers_never_appear_in_metrics_logs():
    """33. Authorization headers or bearer tokens never appear in refresh result."""
    res = MarketDemandRefreshResult(
        source="adzuna",
        refreshed=False,
        reason="failed: TimeoutError",
        error="TimeoutError",
    )
    summary = res.to_summary_dict()
    serialized = str(summary).lower()

    assert "bearer" not in serialized
    assert "authorization" not in serialized
    assert "token" not in serialized


def test_34_refresh_ordering(db: Session):
    """34. Verifies refresh stages execute in strictly ordered sequence."""
    order_tracker: List[str] = []

    mock_pipeline = MagicMock()
    mock_pipeline.run_pipeline.side_effect = lambda *args, **kwargs: order_tracker.append("pipeline") or MarketPipelineResult()

    mock_extraction = MagicMock()
    mock_extraction.process_persisted_jobs.side_effect = lambda *args, **kwargs: order_tracker.append("extraction") or MagicMock(skills_matched=0)

    mock_aggregator = MagicMock()
    mock_aggregator.aggregate_market_demand.side_effect = lambda *args, **kwargs: order_tracker.append("aggregation") or MagicMock(skills_with_demand=0)

    mock_snapshot = MagicMock()
    mock_snapshot.get_latest_snapshot_timestamps.return_value = []
    mock_snapshot.create_snapshot_from_current_demand.side_effect = lambda *args, **kwargs: order_tracker.append("snapshot") or ([], 0, 0)

    mock_growth = MagicMock()
    mock_growth.compute_and_persist_growth.side_effect = lambda *args, **kwargs: order_tracker.append("growth") or ([], 0, 0, 0)

    service = MarketDemandRefreshService(
        pipeline=mock_pipeline,
        extraction_service=mock_extraction,
        aggregator=mock_aggregator,
        snapshot_service=mock_snapshot,
        growth_service=mock_growth,
    )
    service.refresh(db=db, force=True)

    assert order_tracker == ["pipeline", "extraction", "aggregation", "snapshot", "growth"]


def test_35_transaction_rollback_on_failure(db: Session):
    """35. On unexpected exception during refresh, db.rollback() is invoked."""
    mock_db = MagicMock(spec=Session)
    mock_pipeline = MagicMock()
    mock_pipeline.run_pipeline.side_effect = RuntimeError("Fatal crash")

    mock_snapshot = MagicMock()
    mock_snapshot.get_latest_snapshot_timestamps.return_value = []

    service = MarketDemandRefreshService(pipeline=mock_pipeline, snapshot_service=mock_snapshot)
    res = service.refresh(db=mock_db, force=True)

    assert res.refreshed is False
    mock_db.rollback.assert_called_once()
