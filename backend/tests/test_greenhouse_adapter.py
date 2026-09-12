"""
Unit and integration tests for SkillForge P1-H: Greenhouse Market Source Adapter.

Verifies:
A. Successful normalization (valid Greenhouse response, ID, title, description, URL, source)
B. Stable external job ID (numeric ID becomes deterministic string)
C. Optional fields handling (missing description, location, company, departments, URLs)
D. Deterministic HTML cleaning (tag stripping, entity decoding, paragraph preservation)
E. Invalid records rejection (missing ID, empty ID, missing title, empty title, non-dict)
F. HTTP error mapping (404, 429, 500 mapped to GreenhouseAPIError)
G. Response error mapping (malformed JSON, missing 'jobs' array mapped to GreenhouseResponseError)
H. Network failure mapping (timeout, connection drop mapped to GreenhouseConnectionError)
I. Configuration handling (missing board_token raises MarketSourceConfigurationError)
J. max_results bounded fetching and deterministic ordering
K. Deterministic in-memory query filtering (case-insensitive substring, no semantic alteration)
L. Registry resolution (GREENHOUSE resolves, LEVER/ASHBY rejected, unknown rejected, no fallback)
M. Preservation of source provenance and raw_data auditability
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.config import settings
from app.services.market.adapters import (
    AdzunaAdapter,
    AshbyAdapter,
    GreenhouseAPIError,
    GreenhouseAdapter,
    GreenhouseConnectionError,
    GreenhouseError,
    GreenhouseResponseError,
    LeverAdapter,
    MarketSourceAdapter,
    MarketSourceConfigurationError,
    MarketSourceError,
    MarketSourceRegistry,
    MarketSourceType,
    UnknownMarketSourceError,
    UnsupportedMarketSourceError,
    clean_greenhouse_html,
    get_market_source_adapter,
    market_source_registry,
)
from app.services.market.models import NormalizedMarketJob


# ---------------------------------------------------------------------------
# Sample Test Fixtures
# ---------------------------------------------------------------------------

SAMPLE_GREENHOUSE_JOB: Dict[str, Any] = {
    "id": 7695702,
    "internal_job_id": 3383201,
    "title": "Senior Backend Engineer",
    "company_name": "Cloudflare",
    "location": {"name": "San Francisco, CA"},
    "absolute_url": "https://boards.greenhouse.io/cloudflare/jobs/7695702",
    "updated_at": "2026-09-04T10:59:17-04:00",
    "first_published": "2026-03-09T16:05:19-04:00",
    "content": (
        "&lt;div class=&quot;content-intro&quot;&gt;&lt;h3&gt;About the Team&lt;/h3&gt;&lt;/div&gt;\n"
        "&lt;p&gt;We build distributed systems using Python and FastAPI.&lt;/p&gt;\n"
        "&lt;p&gt;Requirements:&lt;/p&gt;\n"
        "&lt;ul&gt;&lt;li&gt;5+ years Python&lt;/li&gt;&lt;li&gt;PostgreSQL experience&lt;/li&gt;&lt;/ul&gt;"
    ),
    "departments": [{"id": 101, "name": "Engineering"}],
    "offices": [{"id": 201, "name": "San Francisco", "location": "San Francisco, CA, United States"}],
}

SAMPLE_GREENHOUSE_RESPONSE: Dict[str, Any] = {
    "jobs": [
        SAMPLE_GREENHOUSE_JOB,
        {
            "id": 7695703,
            "title": "Product Designer",
            "company_name": "Cloudflare",
            "location": {"name": "London, UK"},
            "absolute_url": "https://boards.greenhouse.io/cloudflare/jobs/7695703",
            "updated_at": "2026-09-05T12:00:00Z",
            "content": "&lt;p&gt;Figma and design systems expert.&lt;/p&gt;",
            "departments": [{"id": 102, "name": "Design"}],
            "offices": [],
        },
        {
            "id": 7695704,
            "title": "Data Platform Engineer",
            "company_name": "Cloudflare",
            "location": {"name": "Austin, TX"},
            "absolute_url": "https://boards.greenhouse.io/cloudflare/jobs/7695704",
            "updated_at": "2026-09-06T14:00:00Z",
            "content": "&lt;p&gt;Kafka, Spark, and Python pipelines.&lt;/p&gt;",
            "departments": [{"id": 101, "name": "Engineering"}],
            "offices": [],
        },
    ]
}


def _create_mock_client(
    json_data: Any = None,
    status_code: int = 200,
    text: str = "",
    side_effect: Any = None,
) -> httpx.Client:
    """Helper to generate a mock httpx.Client returning controlled responses."""
    mock_client = MagicMock(spec=httpx.Client)
    if side_effect is not None:
        mock_client.get.side_effect = side_effect
    else:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.text = text if text else ("" if json_data is None else str(json_data))
        if json_data is not None:
            mock_response.json.return_value = json_data
        else:
            mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_client.get.return_value = mock_response
    return mock_client


# ===========================================================================
# A. Successful Normalization
# ===========================================================================

def test_01_successful_normalization_full_fields():
    """TEST A: GreenhouseAdapter converts a full Greenhouse posting into NormalizedMarketJob."""
    adapter = GreenhouseAdapter(board_token="cloudflare")
    job = adapter.normalize_job(SAMPLE_GREENHOUSE_JOB)

    assert job is not None
    assert isinstance(job, NormalizedMarketJob)
    assert job.source == "greenhouse"
    assert job.external_job_id == "7695702"
    assert job.title == "Senior Backend Engineer"
    assert job.company_name == "Cloudflare"
    assert job.location == "San Francisco, CA"
    assert job.category == "Engineering"
    assert job.redirect_url == "https://boards.greenhouse.io/cloudflare/jobs/7695702"
    assert job.created_at == "2026-03-09T16:05:19-04:00"
    assert job.deduplication_key == ("greenhouse", "7695702")
    assert job.raw_data == SAMPLE_GREENHOUSE_JOB

    # Description is cleaned HTML
    assert "About the Team" in (job.description or "")
    assert "Python and FastAPI" in (job.description or "")
    assert "<div" not in (job.description or "")
    assert "&lt;" not in (job.description or "")


# ===========================================================================
# B. Stable External ID
# ===========================================================================

def test_02_stable_external_id_conversion():
    """TEST B: Numeric Greenhouse IDs become deterministic non-empty strings."""
    adapter = GreenhouseAdapter()

    # Numeric integer ID
    job_num = adapter.normalize_job({"id": 1234567, "title": "Platform Engineer"})
    assert job_num is not None
    assert job_num.external_job_id == "1234567"
    assert isinstance(job_num.external_job_id, str)

    # String ID with whitespace
    job_str = adapter.normalize_job({"id": "  987654  ", "title": "SRE"})
    assert job_str is not None
    assert job_str.external_job_id == "987654"


# ===========================================================================
# C. Optional Fields Handling
# ===========================================================================

def test_03_optional_fields_missing_safely():
    """TEST C: Missing optional fields are normalized to None and never fabricated."""
    adapter = GreenhouseAdapter()
    minimal_posting = {
        "id": 99999,
        "title": "Minimal Engineer",
    }
    job = adapter.normalize_job(minimal_posting)

    assert job is not None
    assert job.external_job_id == "99999"
    assert job.title == "Minimal Engineer"
    assert job.description is None
    assert job.company_name is None
    assert job.location is None
    assert job.category is None
    assert job.contract_type is None
    assert job.contract_time is None
    assert job.created_at is None
    assert job.redirect_url is None
    assert job.raw_data == minimal_posting


def test_04_fallback_location_to_primary_office():
    """TEST C.2: When location.name is missing, adapter falls back to primary office location/name."""
    adapter = GreenhouseAdapter()
    posting_with_office = {
        "id": 111,
        "title": "Remote Engineer",
        "location": None,
        "offices": [{"id": 1, "name": "Austin Hub", "location": "Austin, Texas"}],
    }
    job = adapter.normalize_job(posting_with_office)
    assert job is not None
    assert job.location == "Austin, Texas"

    # Office with only name
    posting_office_name = {
        "id": 112,
        "title": "Remote Engineer 2",
        "location": {"name": ""},
        "offices": [{"id": 1, "name": "Berlin Office"}],
    }
    job2 = adapter.normalize_job(posting_office_name)
    assert job2 is not None
    assert job2.location == "Berlin Office"


# ===========================================================================
# D. Deterministic HTML Cleaning
# ===========================================================================

def test_05_clean_greenhouse_html_tag_stripping_and_entities():
    """TEST D: clean_greenhouse_html decodes entities, strips tags, preserves paragraph boundaries."""
    raw_html = (
        "&amp;lt;div class=&quot;header&quot;&amp;gt;&amp;lt;h2&amp;gt;Role Summary&amp;lt;/h2&amp;gt;&amp;lt;/div&amp;gt;\n"
        "&lt;p&gt;Line 1 with &amp;amp; symbols &amp;amp; &lt;strong&gt;bold&lt;/strong&gt; text.&lt;/p&gt;\n"
        "&lt;p&gt;Line 2 after paragraph break.&lt;/p&gt;\n"
        "&lt;ul&gt;\n"
        "&lt;li&gt;Item 1&lt;/li&gt;\n"
        "&lt;li&gt;Item 2&lt;/li&gt;\n"
        "&lt;/ul&gt;"
    )
    cleaned = clean_greenhouse_html(raw_html)

    assert cleaned is not None
    assert "Role Summary" in cleaned
    assert "Line 1 with & symbols & bold text." in cleaned
    assert "Line 2 after paragraph break." in cleaned
    assert "Item 1" in cleaned
    assert "Item 2" in cleaned

    # HTML tags and entities must be eliminated
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "&amp;" not in cleaned
    assert "&lt;" not in cleaned
    assert "&gt;" not in cleaned

    # Paragraph breaks preserved
    assert "\n\n" in cleaned

    # Edge cases
    assert clean_greenhouse_html(None) is None
    assert clean_greenhouse_html("") is None
    assert clean_greenhouse_html("   \n\t  ") is None


# ===========================================================================
# E. Invalid Records Rejection
# ===========================================================================

def test_06_invalid_records_rejected():
    """TEST E: Postings missing ID or title are rejected and return None."""
    adapter = GreenhouseAdapter()

    # Missing ID
    assert adapter.normalize_job({"title": "No ID Engineer"}) is None
    assert adapter.normalize_job({"id": None, "title": "No ID"}) is None
    assert adapter.normalize_job({"id": "", "title": "Empty ID"}) is None
    assert adapter.normalize_job({"id": "   ", "title": "Whitespace ID"}) is None

    # Missing Title
    assert adapter.normalize_job({"id": 101}) is None
    assert adapter.normalize_job({"id": 101, "title": None}) is None
    assert adapter.normalize_job({"id": 101, "title": ""}) is None
    assert adapter.normalize_job({"id": 101, "title": "   "}) is None

    # Unsupported non-dict types
    assert adapter.normalize_job("string_payload") is None
    assert adapter.normalize_job(["list_payload"]) is None
    assert adapter.normalize_job(12345) is None
    assert adapter.normalize_job(None) is None


# ===========================================================================
# F. HTTP Errors
# ===========================================================================

def test_07_http_errors_raise_greenhouse_api_error():
    """TEST F: HTTP 404, 429, and 500 raise typed GreenhouseAPIError."""
    # 404 Not Found
    client_404 = _create_mock_client(status_code=404, text='{"error": "Job not found"}')
    adapter = GreenhouseAdapter(board_token="nonexistent_board", client=client_404)
    with pytest.raises(GreenhouseAPIError) as exc_404:
        adapter.fetch_and_normalize_jobs()
    assert exc_404.value.status_code == 404
    assert "not found" in str(exc_404.value).lower()
    assert isinstance(exc_404.value, MarketSourceError)

    # 429 Rate Limited
    client_429 = _create_mock_client(status_code=429, text='{"error": "Rate limited"}')
    adapter_429 = GreenhouseAdapter(board_token="cloudflare", client=client_429)
    with pytest.raises(GreenhouseAPIError) as exc_429:
        adapter_429.fetch_and_normalize_jobs()
    assert exc_429.value.status_code == 429
    assert "rate limit" in str(exc_429.value).lower()

    # 500 Server Error
    client_500 = _create_mock_client(status_code=500, text="Internal Server Error")
    adapter_500 = GreenhouseAdapter(board_token="cloudflare", client=client_500)
    with pytest.raises(GreenhouseAPIError) as exc_500:
        adapter_500.fetch_and_normalize_jobs()
    assert exc_500.value.status_code == 500


# ===========================================================================
# G. Response Errors
# ===========================================================================

def test_08_response_errors_raise_greenhouse_response_error():
    """TEST G: Malformed JSON and missing 'jobs' array raise typed GreenhouseResponseError."""
    # Malformed non-JSON response
    client_bad_json = _create_mock_client(json_data=None, status_code=200, text="<html>502 Bad Gateway</html>")
    adapter = GreenhouseAdapter(board_token="cloudflare", client=client_bad_json)
    with pytest.raises(GreenhouseResponseError) as exc_json:
        adapter.fetch_and_normalize_jobs()
    assert "JSON" in str(exc_json.value)
    assert isinstance(exc_json.value, MarketSourceError)

    # Missing 'jobs' key
    client_missing_jobs = _create_mock_client(json_data={"departments": []}, status_code=200)
    adapter_missing = GreenhouseAdapter(board_token="cloudflare", client=client_missing_jobs)
    with pytest.raises(GreenhouseResponseError) as exc_shape:
        adapter_missing.fetch_and_normalize_jobs()
    assert "missing" in str(exc_shape.value).lower()


# ===========================================================================
# H. Network Failures
# ===========================================================================

def test_09_network_failures_raise_greenhouse_connection_error():
    """TEST H: Timeouts and network connection errors raise GreenhouseConnectionError."""
    # Timeout
    client_timeout = _create_mock_client(
        side_effect=httpx.TimeoutException("Connection timed out after 15.0s")
    )
    adapter = GreenhouseAdapter(board_token="cloudflare", client=client_timeout)
    with pytest.raises(GreenhouseConnectionError) as exc_timeout:
        adapter.fetch_and_normalize_jobs()
    assert "timed out" in str(exc_timeout.value).lower()
    assert isinstance(exc_timeout.value, MarketSourceError)

    # Connection error
    client_conn_error = _create_mock_client(
        side_effect=httpx.ConnectError("DNS lookup failed for boards-api.greenhouse.io")
    )
    adapter_conn = GreenhouseAdapter(board_token="cloudflare", client=client_conn_error)
    with pytest.raises(GreenhouseConnectionError) as exc_conn:
        adapter_conn.fetch_and_normalize_jobs()
    assert "failed" in str(exc_conn.value).lower()


# ===========================================================================
# I. Configuration Handling
# ===========================================================================

def test_10_configuration_handling():
    """TEST I: Missing board_token raises MarketSourceConfigurationError; configured token succeeds."""
    # Missing board_token entirely
    mock_settings_none = MagicMock()
    mock_settings_none.GREENHOUSE_BOARD_TOKEN = None
    with patch("app.services.market.adapters.greenhouse_adapter.settings", mock_settings_none):
        adapter_unconfigured = GreenhouseAdapter(board_token=None)
        assert adapter_unconfigured.is_configured is False
        with pytest.raises(MarketSourceConfigurationError) as exc_config:
            adapter_unconfigured.fetch_and_normalize_jobs()
        assert "board token is missing" in str(exc_config.value).lower()

    # Configured via environment/settings
    mock_settings_val = MagicMock()
    mock_settings_val.GREENHOUSE_BOARD_TOKEN = "env_company"
    with patch("app.services.market.adapters.greenhouse_adapter.settings", mock_settings_val):
        adapter_from_env = GreenhouseAdapter(board_token=None)
        assert adapter_from_env.is_configured is True
        mock_env_client = _create_mock_client(json_data={"jobs": []})
        adapter_from_env._client = mock_env_client
        assert adapter_from_env.fetch_and_normalize_jobs() == []

    # Configured via constructor
    adapter_configured = GreenhouseAdapter(board_token="cloudflare")
    assert adapter_configured.is_configured is True
    assert adapter_configured.source_type == MarketSourceType.GREENHOUSE
    assert adapter_configured.source_name == "greenhouse"

    # Configured via fetch argument override
    mock_client = _create_mock_client(json_data={"jobs": []})
    adapter_override = GreenhouseAdapter(board_token=None, client=mock_client)
    jobs = adapter_override.fetch_and_normalize_jobs(board_token="stripe")
    assert jobs == []


# ===========================================================================
# J. max_results and Bounded Fetching
# ===========================================================================

def test_11_max_results_bounded_fetching():
    """TEST J: max_results deterministically slices results after normalization."""
    mock_client = _create_mock_client(json_data=SAMPLE_GREENHOUSE_RESPONSE)
    adapter = GreenhouseAdapter(board_token="cloudflare", client=mock_client)

    # Fetch with max_results = 2
    jobs_bounded = adapter.fetch_and_normalize_jobs(max_results=2)
    assert len(jobs_bounded) == 2

    # Fetch with no limit (all 3 returned)
    jobs_all = adapter.fetch_and_normalize_jobs()
    assert len(jobs_all) == 3

    # Ordering is deterministic (sorted by title, external_job_id)
    titles = [j.title for j in jobs_all]
    assert titles == sorted(titles, key=lambda t: t.lower())


# ===========================================================================
# K. Query Filtering
# ===========================================================================

def test_12_deterministic_query_filtering():
    """TEST K: Query keywords filter deterministically and case-insensitively without an LLM."""
    mock_client = _create_mock_client(json_data=SAMPLE_GREENHOUSE_RESPONSE)
    adapter = GreenhouseAdapter(board_token="cloudflare", client=mock_client)

    # Filter by title keyword "Backend"
    jobs_backend = adapter.fetch_and_normalize_jobs(queries=["backend"])
    assert len(jobs_backend) == 1
    assert jobs_backend[0].title == "Senior Backend Engineer"

    # Filter by description keyword "Figma" (case-insensitive)
    jobs_figma = adapter.fetch_and_normalize_jobs(queries=["FIGMA"])
    assert len(jobs_figma) == 1
    assert jobs_figma[0].title == "Product Designer"

    # Filter by keyword matching multiple postings: "Python" matches Backend and Data Platform
    jobs_python = adapter.fetch_and_normalize_jobs(queries=["Python"])
    assert len(jobs_python) == 2
    assert {j.title for j in jobs_python} == {"Senior Backend Engineer", "Data Platform Engineer"}

    # Query with no match returns empty list without error
    jobs_none = adapter.fetch_and_normalize_jobs(queries=["NonexistentKeyword12345"])
    assert jobs_none == []

    # Empty query list returns all jobs
    jobs_empty_q = adapter.fetch_and_normalize_jobs(queries=[])
    assert len(jobs_empty_q) == 3


# ===========================================================================
# L. Registry Integration
# ===========================================================================

def test_13_registry_resolves_greenhouse_and_rejects_unsupported():
    """TEST L: Registry resolves ADZUNA and GREENHOUSE, rejects LEVER and ASHBY, and never falls back."""
    registry = MarketSourceRegistry()

    # Resolves GREENHOUSE via enum and string
    gh_adapter_enum = registry.get_adapter(MarketSourceType.GREENHOUSE)
    assert isinstance(gh_adapter_enum, GreenhouseAdapter)
    assert gh_adapter_enum.source_type == MarketSourceType.GREENHOUSE
    assert gh_adapter_enum.source_name == "greenhouse"

    gh_adapter_str = registry.get_adapter("greenhouse")
    assert isinstance(gh_adapter_str, GreenhouseAdapter)

    gh_adapter_upper = registry.get_adapter("GREENHOUSE")
    assert isinstance(gh_adapter_upper, GreenhouseAdapter)

    # is_supported returns True for GREENHOUSE
    assert registry.is_supported(MarketSourceType.GREENHOUSE) is True
    assert registry.is_supported("greenhouse") is True

    # Global convenience helper resolves GREENHOUSE
    global_gh = get_market_source_adapter("greenhouse")
    assert isinstance(global_gh, GreenhouseAdapter)

    # Resolves ADZUNA
    adzuna_adapter = registry.get_adapter(MarketSourceType.ADZUNA)
    assert isinstance(adzuna_adapter, AdzunaAdapter)
    assert registry.is_supported(MarketSourceType.ADZUNA) is True

    # Resolves LEVER (supported in P1-I)
    lever_adapter = registry.get_adapter(MarketSourceType.LEVER)
    assert isinstance(lever_adapter, LeverAdapter)
    assert registry.is_supported(MarketSourceType.LEVER) is True

    # Resolves ASHBY (supported in P1-J)
    ashby_adapter = registry.get_adapter(MarketSourceType.ASHBY)
    assert isinstance(ashby_adapter, AshbyAdapter)
    assert registry.is_supported(MarketSourceType.ASHBY) is True

    # Continues rejecting unknown sources with UnknownMarketSourceError
    with pytest.raises(UnknownMarketSourceError):
        registry.get_adapter("workday")
    assert registry.is_supported("workday") is False

    # NEVER silently falls back to Adzuna for Greenhouse or unsupported sources
    assert registry.get_adapter("greenhouse") is not adzuna_adapter
    assert not isinstance(registry.get_adapter("greenhouse"), AdzunaAdapter)


# ===========================================================================
# M. Downstream NormalizedMarketJob Compatibility
# ===========================================================================

def test_14_normalized_market_job_downstream_contract_adherence():
    """TEST M: NormalizedMarketJob from Greenhouse integrates directly into downstream contract."""
    adapter = GreenhouseAdapter()
    job = adapter.normalize_job(SAMPLE_GREENHOUSE_JOB)
    assert job is not None

    # Test to_dict serialization
    job_dict = job.to_dict()
    assert job_dict["source"] == "greenhouse"
    assert job_dict["external_job_id"] == "7695702"
    assert job_dict["title"] == "Senior Backend Engineer"
    assert job_dict["company_name"] == "Cloudflare"
    assert job_dict["location"] == "San Francisco, CA"
    assert job_dict["category"] == "Engineering"
    assert job_dict["redirect_url"] == "https://boards.greenhouse.io/cloudflare/jobs/7695702"

    # Test deduplication key
    assert job.deduplication_key == ("greenhouse", "7695702")

    # Already normalized job passes through normalize_job unchanged
    re_normalized = adapter.normalize_job(job)
    assert re_normalized is job
