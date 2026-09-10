"""
Unit and integration tests for MarketJob PostgreSQL persistence (Post-MVP Checkpoint P1-C).
Verifies:
- Database model schema, constraints, and indexes for market_jobs
- PostgreSQL-native idempotent upsert via MarketJobRepository
- Unchanged duplicate detection and non-destructive partial updates
- Accurate persistence audit metrics (attempted, inserted, updated, unchanged, failed)
- End-to-end orchestration via AdzunaMarketPipeline
- Preservation of frozen MVP tables (skill_demand, skill_gaps)
- Security: strict absence of credentials in DB and logs
- Edge cases (empty lists, duplicate-only, missing optional fields, cross-source collisions)
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import IndustrySkillDemand, MarketJob, SkillGap
from app.services.market.clients.adzuna_client import AdzunaClient, AdzunaJobItem, AdzunaSearchResponse
from app.services.market.ingestion.adzuna_ingestion import AdzunaIngestionService
from app.services.market.models import NormalizedMarketJob
from app.services.market.pipeline import AdzunaMarketPipeline, MarketPipelineResult
from app.services.market.repository import MarketJobRepository, PersistenceMetrics, parse_iso_datetime


@pytest.fixture
def db():
    """Provides a transactional database session and cleans up test records."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Clean up any test market_jobs created by tests
        session.query(MarketJob).filter(MarketJob.source.like("test_%")).delete(synchronize_session=False)
        session.commit()
        session.close()


# ===========================================================================
# 1. Database Model & Constraint Verification
# ===========================================================================

def test_market_jobs_model_creates_correctly(db: Session):
    """Verifies that MarketJob table and model accept and persist all required fields."""
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    job = MarketJob(
        id=job_id,
        source="test_adzuna",
        external_job_id="ext-001",
        title="Senior Python Engineer",
        description="FastAPI & PostgreSQL backend engineering.",
        company_name="Acme Tech",
        location="Bengaluru, Karnataka",
        category="IT Jobs",
        contract_type="permanent",
        contract_time="full_time",
        created_at=now,
        redirect_url="https://adzuna.in/job/ext-001",
        raw_data={"origin": "test"},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    assert job.id == job_id
    assert job.source == "test_adzuna"
    assert job.external_job_id == "ext-001"
    assert job.title == "Senior Python Engineer"
    assert job.description == "FastAPI & PostgreSQL backend engineering."
    assert job.company_name == "Acme Tech"
    assert job.location == "Bengaluru, Karnataka"
    assert job.category == "IT Jobs"
    assert job.contract_type == "permanent"
    assert job.contract_time == "full_time"
    assert job.created_at is not None
    assert job.redirect_url == "https://adzuna.in/job/ext-001"
    assert job.raw_data == {"origin": "test"}
    assert job.ingested_at is not None
    assert job.updated_at is not None


def test_unique_constraint_source_external_job_id_enforced(db: Session):
    """Verifies that direct insertion of duplicate (source, external_job_id) raises IntegrityError."""
    job1 = MarketJob(
        id=uuid.uuid4(),
        source="test_adzuna",
        external_job_id="unique-check-100",
        title="Job 1",
    )
    db.add(job1)
    db.commit()

    job2 = MarketJob(
        id=uuid.uuid4(),
        source="test_adzuna",
        external_job_id="unique-check-100",  # Duplicate key in same source
        title="Job 2 with same key",
    )
    db.add(job2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ===========================================================================
# 2. Repository Idempotent Upsert Verification
# ===========================================================================

def test_repository_insert_new_job(db: Session):
    """Verifies that a new NormalizedMarketJob inserts cleanly."""
    repo = MarketJobRepository()
    job = NormalizedMarketJob(
        source="test_adzuna",
        external_job_id="repo-insert-1",
        title="Backend Developer",
        description="FastAPI service",
        company_name="Cloud Corp",
        location="Hyderabad, India",
    )

    job_id, status = repo.persist_job(job, db)
    db.commit()

    assert job_id is not None
    assert status == "inserted"

    persisted = repo.get_job("test_adzuna", "repo-insert-1", db)
    assert persisted is not None
    assert persisted.title == "Backend Developer"
    assert persisted.company_name == "Cloud Corp"


def test_repository_duplicate_is_idempotent_and_unchanged(db: Session):
    """Verifies that re-persisting identical data reports 'unchanged' and creates no duplicate row."""
    repo = MarketJobRepository()
    job = NormalizedMarketJob(
        source="test_adzuna",
        external_job_id="repo-idempotent-2",
        title="DevOps Engineer",
        description="Docker & Kubernetes",
        company_name="Scale Tech",
    )

    # First persistence -> inserted
    _, status1 = repo.persist_job(job, db)
    db.commit()
    assert status1 == "inserted"

    # Second persistence with exact same data -> unchanged
    _, status2 = repo.persist_job(job, db)
    db.commit()
    assert status2 == "unchanged"

    # Row count remains exactly 1
    count = db.query(MarketJob).filter(
        MarketJob.source == "test_adzuna",
        MarketJob.external_job_id == "repo-idempotent-2",
    ).count()
    assert count == 1


def test_repository_valid_incoming_data_updates_existing_job(db: Session):
    """Verifies that changed fields update the record while None values preserve existing data."""
    repo = MarketJobRepository()

    initial_job = NormalizedMarketJob(
        source="test_adzuna",
        external_job_id="repo-update-3",
        title="Frontend Developer",
        description="React and TypeScript",
        company_name="Design Systems Inc",
        location="Pune, India",
    )
    repo.persist_job(initial_job, db)
    db.commit()

    # Updated job: title changed, description updated, company_name is None (should not overwrite)
    updated_job = NormalizedMarketJob(
        source="test_adzuna",
        external_job_id="repo-update-3",
        title="Senior Frontend Developer",  # Changed title
        description="Next.js, React, and TypeScript",  # Changed description
        company_name=None,  # Incoming None must NOT erase "Design Systems Inc"
        location="Pune, India",
    )
    _, status = repo.persist_job(updated_job, db)
    db.commit()

    assert status == "updated"

    persisted = repo.get_job("test_adzuna", "repo-update-3", db)
    assert persisted is not None
    assert persisted.title == "Senior Frontend Developer"
    assert persisted.description == "Next.js, React, and TypeScript"
    # Preserved existing company_name via COALESCE
    assert persisted.company_name == "Design Systems Inc"


def test_repository_multiple_different_jobs_batch_persist(db: Session):
    """Verifies batch persistence of multiple jobs with accurate audit counters."""
    repo = MarketJobRepository()
    jobs = [
        NormalizedMarketJob(
            source="test_adzuna",
            external_job_id=f"batch-job-{i}",
            title=f"Engineer {i}",
            company_name=f"Company {i}",
        )
        for i in range(5)
    ]

    metrics = repo.persist_jobs(jobs, db)

    assert isinstance(metrics, PersistenceMetrics)
    assert metrics.attempted == 5
    assert metrics.inserted == 5
    assert metrics.updated == 0
    assert metrics.unchanged == 0
    assert metrics.failed == 0

    assert repo.count_jobs(db, source="test_adzuna") == 5


def test_repository_metrics_with_mixed_batch(db: Session):
    """Verifies persistence metrics across a mix of new, updated, and unchanged jobs."""
    repo = MarketJobRepository()

    # Pre-populate two jobs
    job_a = NormalizedMarketJob(source="test_adzuna", external_job_id="mix-A", title="Job A")
    job_b = NormalizedMarketJob(source="test_adzuna", external_job_id="mix-B", title="Job B Original")
    repo.persist_jobs([job_a, job_b], db)

    # Batch with:
    # 1. job_a unchanged
    # 2. job_b updated
    # 3. job_c new (inserted)
    batch = [
        NormalizedMarketJob(source="test_adzuna", external_job_id="mix-A", title="Job A"),  # Unchanged
        NormalizedMarketJob(source="test_adzuna", external_job_id="mix-B", title="Job B Updated"),  # Updated
        NormalizedMarketJob(source="test_adzuna", external_job_id="mix-C", title="Job C New"),  # Inserted
    ]

    metrics = repo.persist_jobs(batch, db)
    assert metrics.attempted == 3
    assert metrics.inserted == 1
    assert metrics.updated == 1
    assert metrics.unchanged == 1
    assert metrics.failed == 0


def test_transaction_rollback_on_failure(db: Session):
    """Verifies that an error in batch persistence raises and leaves no partial uncommitted state."""
    repo = MarketJobRepository()
    valid_job = NormalizedMarketJob(source="test_adzuna", external_job_id="rb-1", title="Valid Job")
    invalid_job = NormalizedMarketJob(source="", external_job_id="", title="")  # Will trigger ValueError

    with pytest.raises(ValueError):
        repo.persist_jobs([valid_job, invalid_job], db)

    # Rollback session and verify valid_job was not committed
    db.rollback()
    assert repo.get_job("test_adzuna", "rb-1", db) is None


# ===========================================================================
# 3. Pipeline Orchestration (P1-B -> P1-C)
# ===========================================================================

def test_pipeline_end_to_end_orchestration(db: Session):
    """Verifies AdzunaMarketPipeline connecting P1-B ingestion to P1-C persistence."""
    job1 = AdzunaJobItem(id="pipe-1", title="Backend Developer", description="API design")
    job2 = AdzunaJobItem(id="pipe-2", title="Full Stack Developer", description="Web apps")
    # Duplicate of pipe-1 in second query
    job1_dup = AdzunaJobItem(id="pipe-1", title="Backend Developer", description="API design")

    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.side_effect = [
        AdzunaSearchResponse(results=[job1], total_count=1, page=1, country="in"),
        AdzunaSearchResponse(results=[job2, job1_dup], total_count=2, page=1, country="in"),
    ]

    ingestion_service = AdzunaIngestionService(client=mock_client)
    repo = MarketJobRepository()
    pipeline = AdzunaMarketPipeline(ingestion_service=ingestion_service, repository=repo)

    result = pipeline.run_pipeline(
        db=db,
        queries=["backend developer", "full stack developer"],
        country="in",
    )

    assert isinstance(result, MarketPipelineResult)
    assert result.source == "adzuna"
    assert result.raw_jobs_seen == 3
    assert result.valid_jobs == 3
    assert result.duplicates_removed == 1  # P1-B deduplication
    assert result.final_jobs_count == 2
    assert result.attempted == 2
    assert result.inserted == 2
    assert result.updated == 0
    assert result.unchanged == 0
    assert result.failed == 0

    # Verify rows in PostgreSQL
    persisted1 = repo.get_job("adzuna", "pipe-1", db)
    persisted2 = repo.get_job("adzuna", "pipe-2", db)
    assert persisted1 is not None
    assert persisted2 is not None

    # Clean up test rows
    db.query(MarketJob).filter(MarketJob.external_job_id.in_(["pipe-1", "pipe-2"])).delete(synchronize_session=False)
    db.commit()


# ===========================================================================
# 4. MVP Isolation Verification
# ===========================================================================

def test_persistence_does_not_modify_skill_demand(db: Session):
    """Verifies that market job persistence leaves MVP skill_demand table strictly intact."""
    # Count rows before
    demand_count_before = db.query(IndustrySkillDemand).count()

    repo = MarketJobRepository()
    job = NormalizedMarketJob(
        source="test_adzuna",
        external_job_id="mvp-isolation-job",
        title="Python Engineer",
    )
    repo.persist_job(job, db)
    db.commit()

    demand_count_after = db.query(IndustrySkillDemand).count()
    assert demand_count_before == demand_count_after


def test_persistence_does_not_modify_skill_gaps(db: Session):
    """Verifies that market job persistence leaves MVP skill_gaps table strictly intact."""
    gap_count_before = db.query(SkillGap).count()

    repo = MarketJobRepository()
    job = NormalizedMarketJob(
        source="test_adzuna",
        external_job_id="gap-isolation-job",
        title="Full Stack Engineer",
    )
    repo.persist_job(job, db)
    db.commit()

    gap_count_after = db.query(SkillGap).count()
    assert gap_count_before == gap_count_after


# ===========================================================================
# 5. Security Verification
# ===========================================================================

def test_credentials_and_headers_never_persisted(db: Session):
    """Verifies that secrets or request headers are not stored in the database."""
    repo = MarketJobRepository()
    job = NormalizedMarketJob(
        source="test_adzuna",
        external_job_id="sec-check-1",
        title="Security Engineer",
        raw_data={"title": "Security Engineer", "location": "Bengaluru"},
    )
    repo.persist_job(job, db)
    db.commit()

    record = repo.get_job("test_adzuna", "sec-check-1", db)
    assert record is not None

    record_dict = {
        "source": record.source,
        "external_job_id": record.external_job_id,
        "title": record.title,
        "raw_data": record.raw_data,
    }
    dumped = str(record_dict)

    # Must contain no credentials or sensitive tokens
    assert "ADZUNA_APP_ID" not in dumped
    assert "ADZUNA_APP_KEY" not in dumped
    assert "Authorization" not in dumped
    assert "Bearer" not in dumped


# ===========================================================================
# 6. Edge Cases
# ===========================================================================

def test_edge_case_empty_job_list(db: Session):
    """Verifies that persisting an empty job list completes cleanly with zero metrics."""
    repo = MarketJobRepository()
    metrics = repo.persist_jobs([], db)
    assert metrics.attempted == 0
    assert metrics.inserted == 0
    assert metrics.failed == 0


def test_edge_case_duplicate_only_input(db: Session):
    """Verifies persistence when all records in input list have the identical key."""
    repo = MarketJobRepository()
    dup_job = NormalizedMarketJob(
        source="test_adzuna",
        external_job_id="same-key-always",
        title="Identical Job",
    )

    metrics = repo.persist_jobs([dup_job, dup_job, dup_job], db)
    assert metrics.attempted == 3
    assert metrics.inserted == 1
    assert metrics.unchanged == 2
    assert metrics.updated == 0

    count = db.query(MarketJob).filter(
        MarketJob.source == "test_adzuna",
        MarketJob.external_job_id == "same-key-always",
    ).count()
    assert count == 1


def test_edge_case_missing_optional_fields(db: Session):
    """Verifies that a job with only required fields persists with NULL optional columns."""
    repo = MarketJobRepository()
    minimal_job = NormalizedMarketJob(
        source="test_adzuna",
        external_job_id="minimal-job-001",
        title="Minimal Role",
    )
    _, status = repo.persist_job(minimal_job, db)
    db.commit()
    assert status == "inserted"

    record = repo.get_job("test_adzuna", "minimal-job-001", db)
    assert record is not None
    assert record.description is None
    assert record.company_name is None
    assert record.location is None
    assert record.contract_type is None
    assert record.redirect_url is None


def test_edge_case_same_external_job_id_different_sources(db: Session):
    """Verifies that identical external_job_id from different sources remains distinct."""
    repo = MarketJobRepository()
    job_src_a = NormalizedMarketJob(
        source="test_source_a",
        external_job_id="shared-id-123",
        title="Source A Job",
    )
    job_src_b = NormalizedMarketJob(
        source="test_source_b",
        external_job_id="shared-id-123",  # Same ID, different source
        title="Source B Job",
    )

    repo.persist_job(job_src_a, db)
    repo.persist_job(job_src_b, db)
    db.commit()

    rec_a = repo.get_job("test_source_a", "shared-id-123", db)
    rec_b = repo.get_job("test_source_b", "shared-id-123", db)

    assert rec_a is not None
    assert rec_b is not None
    assert rec_a.id != rec_b.id
    assert rec_a.title == "Source A Job"
    assert rec_b.title == "Source B Job"


def test_parse_iso_datetime_utility():
    """Unit tests for parse_iso_datetime utility."""
    assert parse_iso_datetime(None) is None
    assert parse_iso_datetime("") is None
    assert parse_iso_datetime("not-a-date") is None

    parsed = parse_iso_datetime("2026-09-08T14:30:00Z")
    assert parsed is not None
    assert parsed.year == 2026
    assert parsed.month == 9
    assert parsed.day == 8
    assert parsed.hour == 14
    assert parsed.tzinfo is not None
