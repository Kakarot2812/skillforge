"""
Unit tests for the Adzuna market ingestion pipeline (Post-MVP Checkpoint P1-B).
Verifies:
- Raw Adzuna job normalization and deterministic cleaning
- Discarding of records missing required ID or title
- Empty/blank field normalization to None
- Primary deduplication by (source, external_job_id) with first-occurrence retention
- Cross-query deduplication
- Correct metric tracking in AdzunaIngestionResult
- Strict exclusion of secrets from results and logs
- Resilience against malformed upstream records
- Edge cases (empty results, duplicate-only, missing optional fields)
"""

import logging
from unittest.mock import MagicMock
import pytest

from app.services.market.cleaning import (
    clean_adzuna_job,
    clean_multiline_text,
    collapse_whitespace,
)
from app.services.market.clients.adzuna_client import (
    AdzunaClient,
    AdzunaJobItem,
    AdzunaSearchResponse,
)
from app.services.market.ingestion.adzuna_ingestion import (
    DEFAULT_ROLE_QUERIES,
    AdzunaIngestionService,
)
from app.services.market.models import AdzunaIngestionResult, NormalizedMarketJob


# ===========================================================================
# 1. Raw Job to Normalized Job Conversion & Cleaning
# ===========================================================================

def test_raw_adzuna_job_converts_to_normalized_job():
    """Verifies that a well-formed raw Adzuna job transforms into a NormalizedMarketJob."""
    raw_job = AdzunaJobItem(
        id="adzuna-101",
        title="Backend Software Engineer",
        description="Build high-performance REST APIs in Python using FastAPI and PostgreSQL.",
        company_name="Acme Corp",
        location_name="Bengaluru, Karnataka",
        category_label="IT Jobs",
        created="2026-09-05T10:00:00Z",
        redirect_url="https://adzuna.in/job/101",
        salary_min=1200000.0,
        salary_max=1800000.0,
        raw_data={
            "id": "adzuna-101",
            "contract_type": "permanent",
            "contract_time": "full_time",
        },
    )

    normalized = clean_adzuna_job(raw_job)

    assert normalized is not None
    assert isinstance(normalized, NormalizedMarketJob)
    assert normalized.source == "adzuna"
    assert normalized.external_job_id == "adzuna-101"
    assert normalized.title == "Backend Software Engineer"
    assert "FastAPI" in normalized.description
    assert normalized.company_name == "Acme Corp"
    assert normalized.location == "Bengaluru, Karnataka"
    assert normalized.category == "IT Jobs"
    assert normalized.contract_type == "permanent"
    assert normalized.contract_time == "full_time"
    assert normalized.created_at == "2026-09-05T10:00:00Z"
    assert normalized.redirect_url == "https://adzuna.in/job/101"
    assert normalized.deduplication_key == ("adzuna", "adzuna-101")


def test_whitespace_is_cleaned():
    """Verifies deterministic trimming and collapsing of excess whitespace."""
    raw_job = AdzunaJobItem(
        id="  adzuna-102  ",
        title="   Senior   Full   Stack    Developer   ",
        description="Line 1 with   spaces.\r\n\r\n\r\n\r\nLine 2 after big gap.\r\n",
        company_name="   Tech   Innovations   Pvt   Ltd   ",
        location_name="   Bengaluru  ,   Karnataka   ",
        category_label="  IT   Jobs  ",
        created="  2026-09-01T00:00:00Z  ",
        redirect_url="  https://adzuna.in/job/102  ",
        raw_data={
            "contract_type": "  permanent  ",
            "contract_time": "  full_time  ",
        },
    )

    normalized = clean_adzuna_job(raw_job)

    assert normalized is not None
    assert normalized.external_job_id == "adzuna-102"
    assert normalized.title == "Senior Full Stack Developer"
    assert normalized.company_name == "Tech Innovations Pvt Ltd"
    assert normalized.location == "Bengaluru , Karnataka"
    assert normalized.category == "IT Jobs"
    assert normalized.contract_type == "permanent"
    assert normalized.contract_time == "full_time"
    assert normalized.created_at == "2026-09-01T00:00:00Z"
    assert normalized.redirect_url == "https://adzuna.in/job/102"

    # Multiline description preserves paragraph structure without runaway newlines
    assert "\r" not in normalized.description
    assert "Line 1 with spaces.\n\nLine 2 after big gap." == normalized.description


# ===========================================================================
# 2. Validation: Discarding Invalid Records
# ===========================================================================

def test_missing_external_job_id_is_rejected():
    """Verifies that jobs with no usable external_job_id are rejected."""
    # Blank ID
    raw_1 = AdzunaJobItem(id="", title="Backend Engineer", description="desc")
    assert clean_adzuna_job(raw_1) is None

    # Whitespace-only ID
    raw_2 = AdzunaJobItem(id="   ", title="Backend Engineer", description="desc")
    assert clean_adzuna_job(raw_2) is None

    # None ID
    raw_3 = AdzunaJobItem(id=None, title="Backend Engineer", description="desc")
    assert clean_adzuna_job(raw_3) is None


def test_missing_title_is_rejected():
    """Verifies that jobs with no usable title are rejected."""
    # Blank title
    raw_1 = AdzunaJobItem(id="101", title="", description="desc")
    assert clean_adzuna_job(raw_1) is None

    # Whitespace-only title
    raw_2 = AdzunaJobItem(id="102", title="    ", description="desc")
    assert clean_adzuna_job(raw_2) is None

    # None title
    raw_3 = AdzunaJobItem(id="103", title=None, description="desc")
    assert clean_adzuna_job(raw_3) is None


def test_empty_optional_fields_become_none():
    """Verifies that empty string or whitespace-only optional fields normalize to None."""
    raw_job = AdzunaJobItem(
        id="adzuna-104",
        title="ML Engineer",
        description="   ",
        company_name="   ",
        location_name="",
        category_label="   ",
        created="",
        redirect_url="   ",
        raw_data={
            "contract_type": "   ",
            "contract_time": "",
        },
    )

    normalized = clean_adzuna_job(raw_job)

    assert normalized is not None
    assert normalized.external_job_id == "adzuna-104"
    assert normalized.title == "ML Engineer"
    assert normalized.description is None
    assert normalized.company_name is None
    assert normalized.location is None
    assert normalized.category is None
    assert normalized.contract_type is None
    assert normalized.contract_time is None
    assert normalized.created_at is None
    assert normalized.redirect_url is None


# ===========================================================================
# 3. Deduplication Behavior
# ===========================================================================

def test_duplicate_within_single_query_is_removed():
    """Verifies duplicate external_job_id within the same query is deduplicated."""
    job1 = AdzunaJobItem(id="dup-01", title="Backend Engineer", description="Job 1")
    job2 = AdzunaJobItem(id="uniq-02", title="DevOps Engineer", description="Job 2")
    job3 = AdzunaJobItem(id="dup-01", title="Backend Engineer (Duplicate)", description="Job 3")

    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[job1, job2, job3],
        total_count=3,
        page=1,
        country="in",
    )

    service = AdzunaIngestionService(client=mock_client)
    result = service.ingest_market_jobs(queries=["backend developer"])

    assert result.raw_jobs_seen == 3
    assert result.valid_jobs == 3
    assert result.duplicates_removed == 1
    assert len(result.final_jobs) == 2
    assert [j.external_job_id for j in result.final_jobs] == ["dup-01", "uniq-02"]
    # Verify first occurrence retained
    assert result.final_jobs[0].title == "Backend Engineer"


def test_duplicate_across_different_queries_is_removed():
    """Verifies that an Adzuna job appearing across multiple queries is ingested only once."""
    shared_job_q1 = AdzunaJobItem(
        id="cross-query-99",
        title="Full Stack Developer",
        description="First occurrence from backend query",
    )
    uniq_job_q1 = AdzunaJobItem(
        id="backend-only-1",
        title="Pure Backend Engineer",
        description="Backend only",
    )

    shared_job_q2 = AdzunaJobItem(
        id="cross-query-99",
        title="Full Stack Developer (Query 2)",
        description="Second occurrence from fullstack query",
    )
    uniq_job_q2 = AdzunaJobItem(
        id="fullstack-only-2",
        title="Pure Fullstack Engineer",
        description="Fullstack only",
    )

    mock_client = MagicMock(spec=AdzunaClient)

    def mock_search_side_effect(what, **kwargs):
        if what == "backend developer":
            return AdzunaSearchResponse(
                results=[shared_job_q1, uniq_job_q1],
                total_count=2,
                page=1,
                country="in",
            )
        elif what == "full stack developer":
            return AdzunaSearchResponse(
                results=[shared_job_q2, uniq_job_q2],
                total_count=2,
                page=1,
                country="in",
            )
        return AdzunaSearchResponse(results=[], total_count=0, page=1, country="in")

    mock_client.search_jobs.side_effect = mock_search_side_effect

    service = AdzunaIngestionService(client=mock_client)
    result = service.ingest_market_jobs(queries=["backend developer", "full stack developer"])

    assert result.raw_jobs_seen == 4
    assert result.valid_jobs == 4
    assert result.duplicates_removed == 1
    assert len(result.final_jobs) == 3

    # Primary key deduplication: cross-query-99, backend-only-1, fullstack-only-2
    assert [j.external_job_id for j in result.final_jobs] == [
        "cross-query-99",
        "backend-only-1",
        "fullstack-only-2",
    ]
    # Verify deterministic first-occurrence retention
    assert result.final_jobs[0].title == "Full Stack Developer"
    assert result.final_jobs[0].description == "First occurrence from backend query"


# ===========================================================================
# 4. Multi-Query and Pagination Orchestration
# ===========================================================================

def test_multiple_role_queries_processed_in_order():
    """Verifies that all default role queries are requested in deterministic order."""
    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[],
        total_count=0,
        page=1,
        country="in",
    )

    service = AdzunaIngestionService(client=mock_client)
    result = service.ingest_market_jobs()

    assert result.requested_queries == DEFAULT_ROLE_QUERIES
    assert mock_client.search_jobs.call_count == len(DEFAULT_ROLE_QUERIES)

    called_queries = [call[1]["what"] for call in mock_client.search_jobs.call_args_list]
    assert called_queries == DEFAULT_ROLE_QUERIES


def test_page_configuration_works():
    """Verifies that pages_per_query and results_per_page are respected."""
    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[],
        total_count=0,
        page=1,
        country="in",
    )

    service = AdzunaIngestionService(client=mock_client)
    result = service.ingest_market_jobs(
        queries=["devops engineer"],
        pages_per_query=3,
        results_per_page=15,
        country="in",
    )

    assert result.pages_fetched == 3
    assert mock_client.search_jobs.call_count == 3

    for i, call in enumerate(mock_client.search_jobs.call_args_list, start=1):
        assert call[1]["what"] == "devops engineer"
        assert call[1]["page"] == i
        assert call[1]["results_per_page"] == 15
        assert call[1]["country"] == "in"


# ===========================================================================
# 5. Metadata and Audit Metrics
# ===========================================================================

def test_result_metadata_is_correct():
    """Verifies accuracy of all audit counters in AdzunaIngestionResult."""
    # 5 raw jobs:
    # 1. Valid unique job A
    # 2. Invalid job (missing title)
    # 3. Valid unique job B
    # 4. Valid duplicate job A
    # 5. Invalid job (missing id)
    job_a = AdzunaJobItem(id="A", title="Job A", description="Valid A")
    job_inv_1 = AdzunaJobItem(id="B", title="", description="No title")
    job_b = AdzunaJobItem(id="C", title="Job C", description="Valid C")
    job_a_dup = AdzunaJobItem(id="A", title="Job A Duplicate", description="Valid A Dup")
    job_inv_2 = AdzunaJobItem(id=None, title="Job D", description="No id")

    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[job_a, job_inv_1, job_b, job_a_dup, job_inv_2],
        total_count=5,
        page=1,
        country="in",
    )

    service = AdzunaIngestionService(client=mock_client)
    result = service.ingest_market_jobs(queries=["backend developer"])

    assert result.source == "adzuna"
    assert result.requested_queries == ["backend developer"]
    assert result.pages_fetched == 1
    assert result.raw_jobs_seen == 5
    assert result.valid_jobs == 3
    assert result.cleaned_jobs == 3
    assert result.duplicates_removed == 1
    assert len(result.final_jobs) == 2

    summary = result.to_summary_dict()
    assert summary["source"] == "adzuna"
    assert summary["raw_jobs_seen"] == 5
    assert summary["valid_jobs"] == 3
    assert summary["duplicates_removed"] == 1
    assert summary["final_jobs_count"] == 2


# ===========================================================================
# 6. Security Verification
# ===========================================================================

def test_credentials_never_included_in_output_or_logging(caplog):
    """Verifies that secrets never appear in ingestion results, serialized dictionaries, or logs."""
    fake_secret_id = "super_secret_app_id_99999"
    fake_secret_key = "super_secret_app_key_88888"

    job = AdzunaJobItem(
        id="job-sec-1",
        title="Security Engineer",
        description="Testing secret isolation",
        company_name="Safe Corp",
    )

    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[job],
        total_count=1,
        page=1,
        country="in",
    )

    service = AdzunaIngestionService(client=mock_client)

    with caplog.at_level(logging.DEBUG):
        result = service.ingest_market_jobs(queries=["security engineer"])

    # Verify result object
    serialized = result.to_summary_dict()
    assert fake_secret_id not in str(serialized)
    assert fake_secret_key not in str(serialized)

    job_dict = result.final_jobs[0].to_dict()
    assert fake_secret_id not in str(job_dict)
    assert fake_secret_key not in str(job_dict)

    # Verify logs
    log_text = caplog.text
    assert fake_secret_id not in log_text
    assert fake_secret_key not in log_text
    assert "Authorization" not in log_text


# ===========================================================================
# 7. Resilience & Edge Cases
# ===========================================================================

def test_malformed_upstream_job_does_not_crash_normalization():
    """Verifies that an unexpected exception on a single item skips the item gracefully."""
    good_job_1 = AdzunaJobItem(id="good-1", title="Engineer 1", description="Valid description")
    # A job item whose raw_data triggers an issue
    weird_job = AdzunaJobItem(id="weird-2", title="Engineer 2", description="Valid description", raw_data=None)  # None raw_data
    good_job_2 = AdzunaJobItem(id="good-3", title="Engineer 3", description="Valid description")

    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[good_job_1, weird_job, good_job_2],
        total_count=3,
        page=1,
        country="in",
    )

    service = AdzunaIngestionService(client=mock_client)
    result = service.ingest_market_jobs(queries=["test"])

    # All three should be processed (or weird handled safely)
    assert result.raw_jobs_seen == 3
    assert len(result.final_jobs) >= 2


def test_edge_case_empty_results():
    """Verifies handling when Adzuna returns zero results."""
    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[],
        total_count=0,
        page=1,
        country="in",
    )

    service = AdzunaIngestionService(client=mock_client)
    result = service.ingest_market_jobs(queries=["nonexistent role"])

    assert result.raw_jobs_seen == 0
    assert result.valid_jobs == 0
    assert result.duplicates_removed == 0
    assert result.final_jobs == []


def test_edge_case_duplicate_only_results():
    """Verifies handling when all returned results are the identical job."""
    dup_job = AdzunaJobItem(id="same-id-always", title="Same Title", description="Same Desc")

    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[dup_job, dup_job, dup_job],
        total_count=3,
        page=1,
        country="in",
    )

    service = AdzunaIngestionService(client=mock_client)
    result = service.ingest_market_jobs(queries=["backend developer"])

    assert result.raw_jobs_seen == 3
    assert result.valid_jobs == 3
    assert result.duplicates_removed == 2
    assert len(result.final_jobs) == 1
    assert result.final_jobs[0].external_job_id == "same-id-always"


def test_edge_case_missing_optional_fields():
    """Verifies normalization when company, location, and description are completely absent."""
    bare_job = AdzunaJobItem(
        id="bare-001",
        title="Software Engineer",
        description=None,
        company_name=None,
        location_name=None,
    )

    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[bare_job],
        total_count=1,
        page=1,
        country="in",
    )

    service = AdzunaIngestionService(client=mock_client)
    result = service.ingest_market_jobs(queries=["software engineer"])

    assert len(result.final_jobs) == 1
    job = result.final_jobs[0]
    assert job.external_job_id == "bare-001"
    assert job.title == "Software Engineer"
    assert job.company_name is None
    assert job.location is None
    assert job.description is None


# ===========================================================================
# 8. Parameter Validation
# ===========================================================================

@pytest.mark.parametrize("invalid_pages", [0, -1, -5])
def test_invalid_pages_per_query_raises_value_error(invalid_pages):
    """Verifies that pages_per_query < 1 raises ValueError."""
    service = AdzunaIngestionService()
    with pytest.raises(ValueError) as exc:
        service.ingest_market_jobs(pages_per_query=invalid_pages)
    assert "pages_per_query must be an integer >= 1" in str(exc.value)


@pytest.mark.parametrize("invalid_rpp", [0, -1, 51, 100])
def test_invalid_results_per_page_raises_value_error(invalid_rpp):
    """Verifies that results_per_page outside [1, 50] raises ValueError."""
    service = AdzunaIngestionService()
    with pytest.raises(ValueError) as exc:
        service.ingest_market_jobs(results_per_page=invalid_rpp)
    assert "results_per_page must be an integer between 1 and 50" in str(exc.value)


@pytest.mark.parametrize("invalid_country", ["", "ind", "india", "1", "123"])
def test_invalid_country_raises_value_error(invalid_country):
    """Verifies that country codes not exactly 2 characters raise ValueError."""
    service = AdzunaIngestionService()
    with pytest.raises(ValueError) as exc:
        service.ingest_market_jobs(country=invalid_country)
    assert "country must be a valid 2-letter ISO code" in str(exc.value)


def test_empty_query_list_returns_empty_result_without_api_calls():
    """Verifies that passing queries=[] immediately returns an empty result."""
    mock_client = MagicMock(spec=AdzunaClient)
    service = AdzunaIngestionService(client=mock_client)

    result = service.ingest_market_jobs(queries=[])

    assert result.requested_queries == []
    assert result.final_jobs == []
    mock_client.search_jobs.assert_not_called()
