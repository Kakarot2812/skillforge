"""
Unit and integration tests for Deterministic Market Demand Aggregation (Post-MVP Checkpoint P1-E).

Verifies all 30 required specifications across:
1. Aggregation logic (single/multiple jobs, mention deduplication, independent skills, empty sets)
2. Mathematical boundaries (demand_share in [0, 1], demand_score, zero-division protection)
3. Source dimensions & isolation (source filtering, cross-source isolation, canonical skill_id identity)
4. Persistence & snapshot semantics (idempotent upserts, stale skill reconciliation, rollback)
5. Strict MVP isolation (skill_demand row count 49, values, skill gaps, priorities unchanged)
6. Security (zero credentials, no authorization headers)
7. Edge cases (0 jobs, 0 relationships, 1 job many skills, many jobs 1 skill)
"""

from datetime import datetime, timezone
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
    Skill,
    SkillGap,
)
from app.services.market.demand import (
    MarketDemandAggregator,
    MarketSkillDemandRepository,
    aggregate_market_demand,
    calculate_demand_metrics,
)
from app.services.market.models import MarketSkillDemandRecord


@pytest.fixture
def db():
    """Provides a transactional database session and cleans up test records."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Clean up test demand snapshots and test market jobs (cascades to test market_job_skills)
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
# 1. AGGREGATION LOGIC
# ===========================================================================

def test_one_skill_in_one_job_job_count_one(db: Session):
    """1. One skill in one job produces job_count 1 and demand_share 1.0."""
    skill_python = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_1", "Python Dev", "ext-001")
    _add_job_skill(db, job.id, skill_python.id, "python")

    aggregator = MarketDemandAggregator()
    metrics = aggregator.aggregate_market_demand(db, source="test_p1e_1", commit=True)

    assert metrics.sample_size == 1
    assert metrics.skills_with_demand == 1
    assert metrics.total_relationships == 1

    repo = MarketSkillDemandRepository()
    records = repo.get_demand_for_source("test_p1e_1", db)
    assert len(records) == 1
    assert records[0].skill_id == skill_python.id
    assert records[0].job_count == 1
    assert records[0].sample_size == 1
    assert records[0].demand_share == 1.0
    assert records[0].demand_score == 1.0


def test_one_skill_in_multiple_jobs_unique_job_count(db: Session):
    """2. One skill present in multiple jobs yields exact unique job count."""
    skill_python = db.query(Skill).filter(Skill.slug == "python").first()
    job1 = _create_test_job(db, "test_p1e_2", "Python Dev 1", "ext-001")
    job2 = _create_test_job(db, "test_p1e_2", "Python Dev 2", "ext-002")
    job3 = _create_test_job(db, "test_p1e_2", "Frontend Dev", "ext-003")  # No Python

    _add_job_skill(db, job1.id, skill_python.id, "python")
    _add_job_skill(db, job2.id, skill_python.id, "python")

    metrics = aggregate_market_demand(db, source="test_p1e_2", commit=True)

    assert metrics.sample_size == 3
    assert metrics.skills_with_demand == 1
    assert metrics.total_relationships == 2

    repo = MarketSkillDemandRepository()
    record = repo.get_demand_by_skill(skill_python.id, "test_p1e_2", db)
    assert record is not None
    assert record.job_count == 2
    assert record.sample_size == 3
    assert round(record.demand_share, 4) == round(2 / 3, 4)
    assert record.demand_score == round(2 / 3, 4)


def test_repeated_mentions_do_not_inflate_job_count(db: Session):
    """3. Repeated mentions in a job text do not inflate job_count beyond 1."""
    skill_python = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_3", "Python Lead", "ext-001")

    # Single canonical relationship in market_job_skills
    _add_job_skill(db, job.id, skill_python.id, "python")

    metrics = aggregate_market_demand(db, source="test_p1e_3", commit=True)
    assert metrics.sample_size == 1

    repo = MarketSkillDemandRepository()
    record = repo.get_demand_by_skill(skill_python.id, "test_p1e_3", db)
    assert record.job_count == 1
    assert record.demand_share == 1.0


def test_multiple_skills_aggregate_independently(db: Session):
    """4. Multiple distinct skills aggregate independently with their own counts."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    skill_fastapi = db.query(Skill).filter(Skill.slug == "fastapi").first()
    skill_docker = db.query(Skill).filter(Skill.slug == "docker").first()

    job1 = _create_test_job(db, "test_p1e_4", "Job 1", "ext-001")
    job2 = _create_test_job(db, "test_p1e_4", "Job 2", "ext-002")

    # Job 1 has Python & FastAPI; Job 2 has Python & Docker
    _add_job_skill(db, job1.id, skill_py.id, "python")
    _add_job_skill(db, job1.id, skill_fastapi.id, "fastapi")
    _add_job_skill(db, job2.id, skill_py.id, "python")
    _add_job_skill(db, job2.id, skill_docker.id, "docker")

    metrics = aggregate_market_demand(db, source="test_p1e_4", commit=True)

    assert metrics.sample_size == 2
    assert metrics.skills_with_demand == 3
    assert metrics.total_relationships == 4

    repo = MarketSkillDemandRepository()
    rec_py = repo.get_demand_by_skill(skill_py.id, "test_p1e_4", db)
    rec_fa = repo.get_demand_by_skill(skill_fastapi.id, "test_p1e_4", db)
    rec_dk = repo.get_demand_by_skill(skill_docker.id, "test_p1e_4", db)

    assert rec_py.job_count == 2
    assert rec_py.demand_share == 1.0

    assert rec_fa.job_count == 1
    assert rec_fa.demand_share == 0.5

    assert rec_dk.job_count == 1
    assert rec_dk.demand_share == 0.5


def test_job_with_no_skills_does_not_create_demand(db: Session):
    """5. Jobs without matched skills increase sample_size but do not create false demand."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job1 = _create_test_job(db, "test_p1e_5", "Python Dev", "ext-001")
    job2 = _create_test_job(db, "test_p1e_5", "Office Clerk", "ext-002")  # No skills

    _add_job_skill(db, job1.id, skill_py.id, "python")

    metrics = aggregate_market_demand(db, source="test_p1e_5", commit=True)

    assert metrics.sample_size == 2
    assert metrics.skills_with_demand == 1

    repo = MarketSkillDemandRepository()
    records = repo.get_demand_for_source("test_p1e_5", db)
    assert len(records) == 1
    assert records[0].job_count == 1
    assert records[0].sample_size == 2
    assert records[0].demand_share == 0.5


def test_empty_market_jobs_sample_size_zero(db: Session):
    """6. Empty market_jobs for a source yields sample_size 0 and 0 demand records."""
    metrics = aggregate_market_demand(db, source="test_p1e_empty_source", commit=True)

    assert metrics.sample_size == 0
    assert metrics.skills_with_demand == 0
    assert metrics.total_relationships == 0
    assert metrics.rows_inserted == 0


def test_empty_market_job_skills_zero_demand(db: Session):
    """7. Persisted jobs with zero skill extractions result in sample_size > 0 and 0 demand rows."""
    _create_test_job(db, "test_p1e_noskills", "General Manager", "ext-001")
    _create_test_job(db, "test_p1e_noskills", "Cook", "ext-002")

    metrics = aggregate_market_demand(db, source="test_p1e_noskills", commit=True)

    assert metrics.sample_size == 2
    assert metrics.skills_with_demand == 0
    assert metrics.total_relationships == 0

    repo = MarketSkillDemandRepository()
    assert repo.count_records(db, source="test_p1e_noskills") == 0


def test_demand_share_calculation_correct():
    """8. demand_share and demand_score calculate correctly via helper."""
    share, score = calculate_demand_metrics(job_count=25, sample_size=100)
    assert share == 0.25
    assert score == 0.25

    share, score = calculate_demand_metrics(job_count=1, sample_size=3)
    assert round(share, 4) == 0.3333
    assert score == 0.3333


def test_division_by_zero_handled_safely():
    """9. Division by zero handles safely when sample_size <= 0."""
    share, score = calculate_demand_metrics(job_count=0, sample_size=0)
    assert share == 0.0
    assert score == 0.0

    share, score = calculate_demand_metrics(job_count=5, sample_size=0)
    assert share == 0.0
    assert score == 0.0


def test_demand_values_deterministic(db: Session):
    """10. Aggregating repeatedly on unchanged data yields identical deterministic values."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_det", "Python Dev", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    m1 = aggregate_market_demand(db, source="test_p1e_det", commit=True)
    m2 = aggregate_market_demand(db, source="test_p1e_det", commit=True)

    assert m1.sample_size == m2.sample_size
    assert m1.skills_with_demand == m2.skills_with_demand
    assert m1.total_relationships == m2.total_relationships
    assert m1.top_demanded_skills == m2.top_demanded_skills


# ===========================================================================
# 2. BOUNDARIES & CONSTRAINTS
# ===========================================================================

def test_same_skill_across_multiple_jobs_counted_once_per_job(db: Session):
    """11. A skill mentioned in 4 out of 10 jobs has job_count = 4 and demand_share = 0.40."""
    skill_java = db.query(Skill).filter(Skill.slug == "java").first()

    for i in range(10):
        job = _create_test_job(db, "test_p1e_share", f"Job {i}", f"ext-{i}")
        if i < 4:
            _add_job_skill(db, job.id, skill_java.id, "java")

    metrics = aggregate_market_demand(db, source="test_p1e_share", commit=True)
    assert metrics.sample_size == 10

    repo = MarketSkillDemandRepository()
    rec = repo.get_demand_by_skill(skill_java.id, "test_p1e_share", db)
    assert rec.job_count == 4
    assert rec.sample_size == 10
    assert rec.demand_share == 0.40
    assert rec.demand_score == 0.40


def test_same_job_cannot_contribute_twice(db: Session):
    """12. Uniqueness constraint in market_job_skills prevents duplicate contribution per job."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_unique", "Python Dev", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    # Attempt to insert duplicate relationship directly
    dup_mjs = MarketJobSkill(
        id=uuid.uuid4(),
        market_job_id=job.id,
        skill_id=skill_py.id,
        matched_alias="python3",
        source_field="description",
    )
    db.add(dup_mjs)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_source_dimension_works(db: Session):
    """13. Aggregation respects the source parameter correctly."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job_adzuna = _create_test_job(db, "test_adzuna_src", "Adzuna Job", "ext-adz-01")
    job_other = _create_test_job(db, "test_other_src", "Other Job", "ext-oth-01")

    _add_job_skill(db, job_adzuna.id, skill_py.id, "python")
    _add_job_skill(db, job_other.id, skill_py.id, "python")

    # Aggregate adzuna
    m_adzuna = aggregate_market_demand(db, source="test_adzuna_src", commit=True)
    assert m_adzuna.sample_size == 1
    assert m_adzuna.source == "test_adzuna_src"

    repo = MarketSkillDemandRepository()
    rec_adz = repo.get_demand_by_skill(skill_py.id, "test_adzuna_src", db)
    assert rec_adz.source == "test_adzuna_src"
    assert rec_adz.job_count == 1


def test_unrelated_sources_remain_isolated(db: Session):
    """14. Unrelated sources remain isolated in market_skill_demand."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    skill_java = db.query(Skill).filter(Skill.slug == "java").first()

    job_a = _create_test_job(db, "test_src_a", "Job A", "ext-a1")
    job_b = _create_test_job(db, "test_src_b", "Job B", "ext-b1")

    _add_job_skill(db, job_a.id, skill_py.id, "python")
    _add_job_skill(db, job_b.id, skill_java.id, "java")

    aggregate_market_demand(db, source="test_src_a", commit=True)
    aggregate_market_demand(db, source="test_src_b", commit=True)

    repo = MarketSkillDemandRepository()
    skills_a = {r.skill.name for r in repo.get_demand_for_source("test_src_a", db)}
    skills_b = {r.skill.name for r in repo.get_demand_for_source("test_src_b", db)}

    assert skills_a == {"Python"}
    assert skills_b == {"Java"}


def test_canonical_skill_id_used_rather_than_skill_name_identity(db: Session):
    """15. Canonical skill identity binds strictly to skills.id foreign key."""
    skill_docker = db.query(Skill).filter(Skill.slug == "docker").first()
    job = _create_test_job(db, "test_p1e_fk", "Docker Dev", "ext-001")
    _add_job_skill(db, job.id, skill_docker.id, "containers")

    aggregate_market_demand(db, source="test_p1e_fk", commit=True)

    repo = MarketSkillDemandRepository()
    rec = repo.get_demand_by_skill(skill_docker.id, "test_p1e_fk", db)
    assert rec.skill_id == skill_docker.id
    assert rec.skill.name == "Docker"


# ===========================================================================
# 3. PERSISTENCE & IDEMPOTENCY
# ===========================================================================

def test_first_aggregation_inserts_rows(db: Session):
    """16. First aggregation inserts rows into market_skill_demand."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_ins", "Job", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    metrics = aggregate_market_demand(db, source="test_p1e_ins", commit=True)
    assert metrics.rows_inserted == 1
    assert metrics.rows_updated == 0
    assert metrics.rows_unchanged == 0


def test_repeated_aggregation_is_idempotent(db: Session):
    """17. Repeated aggregation over identical data produces 0 inserts and reports unchanged rows."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_idem", "Job", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    m1 = aggregate_market_demand(db, source="test_p1e_idem", commit=True)
    assert m1.rows_inserted == 1

    m2 = aggregate_market_demand(db, source="test_p1e_idem", commit=True)
    assert m2.rows_inserted == 0
    assert m2.rows_updated == 0
    assert m2.rows_unchanged == 1
    assert m2.rows_deleted == 0


def test_changed_market_job_relationships_update_computed_result(db: Session):
    """18. New jobs added update the demand snapshot via PostgreSQL ON CONFLICT DO UPDATE."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job1 = _create_test_job(db, "test_p1e_upd", "Job 1", "ext-001")
    _add_job_skill(db, job1.id, skill_py.id, "python")

    # Initial run: 1 job, 100% demand
    m1 = aggregate_market_demand(db, source="test_p1e_upd", commit=True)
    assert m1.rows_inserted == 1

    # Add second job without Python: sample_size becomes 2, demand becomes 50%
    _create_test_job(db, "test_p1e_upd", "Job 2", "ext-002")
    m2 = aggregate_market_demand(db, source="test_p1e_upd", commit=True)
    assert m2.rows_updated == 1
    assert m2.sample_size == 2

    repo = MarketSkillDemandRepository()
    rec = repo.get_demand_by_skill(skill_py.id, "test_p1e_upd", db)
    assert rec.sample_size == 2
    assert rec.demand_share == 0.5


def test_removed_stale_relationships_disappear_from_current_snapshot(db: Session):
    """19. Skills no longer present in any job are reconciled and deleted from snapshot."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    skill_redis = db.query(Skill).filter(Skill.slug == "redis").first()

    job = _create_test_job(db, "test_p1e_recon", "Job", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")
    mjs_redis = _add_job_skill(db, job.id, skill_redis.id, "redis")

    # First run: Python and Redis present
    m1 = aggregate_market_demand(db, source="test_p1e_recon", commit=True)
    assert m1.skills_with_demand == 2

    # Remove Redis from market_job_skills
    db.delete(mjs_redis)
    db.commit()

    # Re-run aggregation: Redis must be purged
    m2 = aggregate_market_demand(db, source="test_p1e_recon", commit=True)
    assert m2.skills_with_demand == 1
    assert m2.rows_deleted == 1

    repo = MarketSkillDemandRepository()
    skills_remaining = {r.skill.name for r in repo.get_demand_for_source("test_p1e_recon", db)}
    assert skills_remaining == {"Python"}


def test_transaction_rollback_works(db: Session):
    """20. Database session rollback cleanly aborts uncommitted demand changes."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_rb", "Job", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    aggregator = MarketDemandAggregator()
    aggregator.aggregate_market_demand(db, source="test_p1e_rb", commit=False)
    db.rollback()

    repo = MarketSkillDemandRepository()
    assert repo.count_records(db, source="test_p1e_rb") == 0


# ===========================================================================
# 4. MVP ISOLATION REGRESSION
# ===========================================================================

def test_skill_demand_row_count_unchanged(db: Session):
    """21. Aggregating market demand does not modify MVP skill_demand row count (strictly 49)."""
    mvp_count_before = db.query(IndustrySkillDemand).count()
    assert mvp_count_before == 49

    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_iso", "Job", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    aggregate_market_demand(db, source="test_p1e_iso", commit=True)

    mvp_count_after = db.query(IndustrySkillDemand).count()
    assert mvp_count_after == mvp_count_before == 49


def test_skill_demand_values_unchanged(db: Session):
    """22. Aggregating market demand does not alter demand_score, sample_size, or growth_rate in skill_demand."""
    before_records = [
        (d.id, d.role_id, d.skill_id, d.demand_score, d.sample_size, d.growth_rate)
        for d in db.query(IndustrySkillDemand).all()
    ]

    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_iso_vals", "Job", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    aggregate_market_demand(db, source="test_p1e_iso_vals", commit=True)

    after_records = [
        (d.id, d.role_id, d.skill_id, d.demand_score, d.sample_size, d.growth_rate)
        for d in db.query(IndustrySkillDemand).all()
    ]
    assert before_records == after_records


def test_skill_gaps_unchanged(db: Session):
    """23. Aggregating market demand does not modify SkillGap records."""
    gaps_before = [(g.id, g.user_id, g.role_id, g.skill_id, g.status) for g in db.query(SkillGap).all()]

    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_iso_gaps", "Job", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    aggregate_market_demand(db, source="test_p1e_iso_gaps", commit=True)

    gaps_after = [(g.id, g.user_id, g.role_id, g.skill_id, g.status) for g in db.query(SkillGap).all()]
    assert gaps_before == gaps_after


def test_priority_values_unchanged(db: Session):
    """24. Aggregating market demand does not alter candidate priority scores."""
    priorities_before = [(g.id, g.priority_score, g.priority_level) for g in db.query(SkillGap).all()]

    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_iso_prio", "Job", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    aggregate_market_demand(db, source="test_p1e_iso_prio", commit=True)

    priorities_after = [(g.id, g.priority_score, g.priority_level) for g in db.query(SkillGap).all()]
    assert priorities_before == priorities_after


# ===========================================================================
# 5. SECURITY
# ===========================================================================

def test_credentials_never_enter_demand_records(db: Session):
    """25. Credentials, secret tokens, and API keys are never stored in market_skill_demand."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_sec", "Python Developer", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    aggregate_market_demand(db, source="test_p1e_sec", commit=True)

    repo = MarketSkillDemandRepository()
    record = repo.get_demand_by_skill(skill_py.id, "test_p1e_sec", db)
    dumped = str(record.__dict__)

    assert "ADZUNA_APP_ID" not in dumped
    assert "ADZUNA_APP_KEY" not in dumped
    assert "Authorization" not in dumped
    assert "Bearer" not in dumped


def test_authorization_headers_never_enter_demand_records():
    """26. Schema of market_skill_demand strictly lacks authorization or credential columns."""
    columns = {c.name for c in MarketSkillDemand.__table__.columns}
    assert "headers" not in columns
    assert "auth" not in columns
    assert "token" not in columns
    assert "api_key" not in columns


# ===========================================================================
# 6. EDGE CASES
# ===========================================================================

def test_edge_case_zero_jobs(db: Session):
    """27. Source with zero jobs aggregates cleanly without throwing ZeroDivisionError."""
    metrics = aggregate_market_demand(db, source="test_zero_jobs", commit=True)
    assert metrics.sample_size == 0
    assert metrics.skills_with_demand == 0


def test_edge_case_zero_skill_relationships(db: Session):
    """28. Jobs with zero skill relationships produce zero demand records."""
    _create_test_job(db, "test_p1e_zerorel", "Job 1", "ext-01")
    _create_test_job(db, "test_p1e_zerorel", "Job 2", "ext-02")

    metrics = aggregate_market_demand(db, source="test_p1e_zerorel", commit=True)
    assert metrics.sample_size == 2
    assert metrics.skills_with_demand == 0


def test_edge_case_one_job_with_many_skills(db: Session):
    """29. A single job with 5 skills aggregates all 5 skills to demand_share = 1.0."""
    skills = db.query(Skill).limit(5).all()
    job = _create_test_job(db, "test_p1e_manyskills", "Full Stack", "ext-001")

    for s in skills:
        _add_job_skill(db, job.id, s.id, s.name.lower())

    metrics = aggregate_market_demand(db, source="test_p1e_manyskills", commit=True)
    assert metrics.sample_size == 1
    assert metrics.skills_with_demand == 5
    assert metrics.total_relationships == 5

    repo = MarketSkillDemandRepository()
    records = repo.get_demand_for_source("test_p1e_manyskills", db)
    assert len(records) == 5
    assert all(r.demand_share == 1.0 for r in records)


def test_edge_case_many_jobs_with_one_skill(db: Session):
    """30. 20 jobs each with the same skill yields job_count = 20, demand_share = 1.0."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()

    for i in range(20):
        job = _create_test_job(db, "test_p1e_manyjobs", f"Job {i}", f"ext-{i}")
        _add_job_skill(db, job.id, skill_py.id, "python")

    metrics = aggregate_market_demand(db, source="test_p1e_manyjobs", commit=True)
    assert metrics.sample_size == 20
    assert metrics.skills_with_demand == 1

    repo = MarketSkillDemandRepository()
    rec = repo.get_demand_by_skill(skill_py.id, "test_p1e_manyjobs", db)
    assert rec.job_count == 20
    assert rec.sample_size == 20
    assert rec.demand_share == 1.0


def test_metrics_summary_dictionary_integrity(db: Session):
    """31. MarketDemandAggregationMetrics serializes cleanly to summary dictionary."""
    skill_py = db.query(Skill).filter(Skill.slug == "python").first()
    job = _create_test_job(db, "test_p1e_dict", "Python Dev", "ext-001")
    _add_job_skill(db, job.id, skill_py.id, "python")

    metrics = aggregate_market_demand(db, source="test_p1e_dict", commit=True)
    summary = metrics.to_summary_dict()

    assert summary["source"] == "test_p1e_dict"
    assert summary["sample_size"] == 1
    assert summary["skills_with_demand"] == 1
    assert summary["persistence"]["inserts"] == 1
    assert len(summary["top_demanded_skills"]) == 1
    assert summary["top_demanded_skills"][0][0] == "Python"
    assert summary["top_demanded_skills"][0][1] == 1
    assert summary["top_demanded_skills"][0][2] == 1.0
