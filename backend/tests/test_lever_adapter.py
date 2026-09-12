"""
Unit and integration tests for SkillForge P1-I: Lever Market Source Adapter.

Verifies:
A. Successful normalization (valid Lever response, ID, title, description, URL, source)
B. Stable external job ID (numeric/string ID becomes deterministic string)
C. Title validation (missing or empty title rejected)
D. Deterministic HTML/list description cleaning (tag stripping, entity decoding, list boundary preservation)
E. Optional fields handling (missing description, location, company, departments, URLs, createdAt)
F. Location resolution (categories.location -> allLocations fallback -> country fallback)
G. Category resolution (department -> team fallback)
H. Timestamp conversion (epoch milliseconds to ISO UTC string)
I. HTTP error mapping (404, 429, 500 mapped to LeverAPIError)
J. Response error mapping (malformed JSON, non-list, Lever error dict mapped to LeverResponseError / LeverAPIError)
K. Network failure mapping (timeout, connection failure mapped to LeverConnectionError)
L. Configuration handling (missing site raises MarketSourceConfigurationError; valid site succeeds)
M. max_results bounded fetching and deterministic ordering by (title, external_job_id)
N. Deterministic in-memory query filtering (case-insensitive substring, no semantic alteration)
O. Registry resolution (LEVER, GREENHOUSE, ADZUNA resolve; ASHBY rejected; unknown rejected)
P. Downstream NormalizedMarketJob contract compliance and deduplication key
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.config import settings
from app.services.market.adapters import (
    AdzunaAdapter,
    GreenhouseAdapter,
    LeverAPIError,
    LeverAdapter,
    LeverConnectionError,
    LeverError,
    LeverResponseError,
    MarketSourceAdapter,
    MarketSourceConfigurationError,
    MarketSourceError,
    MarketSourceRegistry,
    MarketSourceType,
    UnknownMarketSourceError,
    UnsupportedMarketSourceError,
    clean_lever_description,
    get_market_source_adapter,
    market_source_registry,
)
from app.services.market.models import NormalizedMarketJob


# ---------------------------------------------------------------------------
# Sample Test Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LEVER_POSTING: Dict[str, Any] = {
    "id": "ac978161-6f46-4f6b-ad9e-a258e642751c",
    "text": "Senior Distributed Systems Engineer",
    "categories": {
        "commitment": "Full-time",
        "location": "London, United Kingdom",
        "department": "Engineering",
        "team": "Core Infrastructure",
        "allLocations": ["London, United Kingdom", "Remote - UK"],
    },
    "country": "GB",
    "workplaceType": "hybrid",
    "description": (
        "<div><p>Welcome to our team! We build high-throughput data pipelines using Python and Rust.</p></div>"
    ),
    "descriptionPlain": (
        "Welcome to our team! We build high-throughput data pipelines using Python and Rust."
    ),
    "lists": [
        {
            "text": "What You'll Do",
            "content": "<li>Design scalable backend microservices.</li><li>Optimize PostgreSQL queries.</li>",
        },
        {
            "text": "What We Require",
            "content": "<li>5+ years backend engineering experience.</li><li>Strong background in distributed systems.</li>",
        },
    ],
    "additional": (
        "<div><p>We are an equal opportunity employer committed to diversity and inclusion.</p></div>"
    ),
    "additionalPlain": "We are an equal opportunity employer committed to diversity and inclusion.",
    "hostedUrl": "https://jobs.lever.co/palantir/ac978161-6f46-4f6b-ad9e-a258e642751c",
    "applyUrl": "https://jobs.lever.co/palantir/ac978161-6f46-4f6b-ad9e-a258e642751c/apply",
    "createdAt": 1711403416463,
}

SAMPLE_LEVER_RESPONSE: List[Dict[str, Any]] = [
    SAMPLE_LEVER_POSTING,
    {
        "id": "b1111111-2222-3333-4444-555555555555",
        "text": "Product Designer",
        "categories": {
            "commitment": "Full-time",
            "location": "New York, NY",
            "department": "Design",
            "team": "Design Systems",
        },
        "description": "<div><p>Figma, design tokens, and user research expert.</p></div>",
        "hostedUrl": "https://jobs.lever.co/palantir/b1111111-2222-3333-4444-555555555555",
        "createdAt": 1711500000000,
    },
    {
        "id": "c2222222-3333-4444-5555-666666666666",
        "text": "Data Infrastructure Engineer",
        "categories": {
            "commitment": "Contract",
            "location": "San Francisco, CA",
            "department": "Engineering",
            "team": "Data Platform",
        },
        "description": "<div><p>Kafka, Spark, and Python streaming architecture.</p></div>",
        "hostedUrl": "https://jobs.lever.co/palantir/c2222222-3333-4444-5555-666666666666",
        "createdAt": 1711600000000,
    },
]


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
    """TEST A: LeverAdapter converts a full Lever posting into canonical NormalizedMarketJob."""
    adapter = LeverAdapter(site="palantir")
    job = adapter.normalize_job(SAMPLE_LEVER_POSTING)

    assert job is not None
    assert isinstance(job, NormalizedMarketJob)
    assert job.source == "lever"
    assert job.external_job_id == "ac978161-6f46-4f6b-ad9e-a258e642751c"
    assert job.title == "Senior Distributed Systems Engineer"
    assert job.location == "London, United Kingdom"
    assert job.category == "Engineering"
    assert job.contract_type == "Full-time"
    assert job.contract_time is None
    assert job.redirect_url == "https://jobs.lever.co/palantir/ac978161-6f46-4f6b-ad9e-a258e642751c"
    assert job.created_at == "2024-03-25T21:50:16.463000+00:00"
    assert job.deduplication_key == ("lever", "ac978161-6f46-4f6b-ad9e-a258e642751c")
    assert job.raw_data == SAMPLE_LEVER_POSTING

    # Description is assembled from opening, structured lists, and closing notes
    desc = job.description or ""
    assert "Welcome to our team! We build high-throughput data pipelines" in desc
    assert "What You'll Do" in desc
    assert "Design scalable backend microservices." in desc
    assert "What We Require" in desc
    assert "5+ years backend engineering experience." in desc
    assert "equal opportunity employer" in desc

    # HTML tags are completely removed
    assert "<div>" not in desc
    assert "<p>" not in desc
    assert "<li>" not in desc


# ===========================================================================
# B. External ID Validation
# ===========================================================================

def test_02_external_id_handling_and_rejection():
    """TEST B: External ID is normalized to string; missing/empty IDs are rejected."""
    adapter = LeverAdapter()

    # Valid string ID
    job1 = adapter.normalize_job({"id": "job-12345", "text": "Backend Dev"})
    assert job1 is not None
    assert job1.external_job_id == "job-12345"

    # Numeric integer ID converts to string
    job2 = adapter.normalize_job({"id": 987654321, "text": "Backend Dev"})
    assert job2 is not None
    assert job2.external_job_id == "987654321"
    assert isinstance(job2.external_job_id, str)

    # Whitespace trimmed
    job3 = adapter.normalize_job({"id": "  uuid-999  ", "text": "Backend Dev"})
    assert job3 is not None
    assert job3.external_job_id == "uuid-999"

    # Missing or empty IDs rejected
    assert adapter.normalize_job({"text": "No ID"}) is None
    assert adapter.normalize_job({"id": None, "text": "None ID"}) is None
    assert adapter.normalize_job({"id": "", "text": "Empty ID"}) is None
    assert adapter.normalize_job({"id": "   ", "text": "Whitespace ID"}) is None


# ===========================================================================
# C. Title Validation
# ===========================================================================

def test_03_title_handling_and_rejection():
    """TEST C: Missing or empty titles are rejected; 'text' and 'title' are supported."""
    adapter = LeverAdapter()

    # Via 'text'
    job_text = adapter.normalize_job({"id": "1", "text": "Data Scientist"})
    assert job_text is not None
    assert job_text.title == "Data Scientist"

    # Via 'title' fallback
    job_title = adapter.normalize_job({"id": "2", "title": "ML Engineer"})
    assert job_title is not None
    assert job_title.title == "ML Engineer"

    # Whitespace trimmed
    job_ws = adapter.normalize_job({"id": "3", "text": "  DevOps Engineer  "})
    assert job_ws is not None
    assert job_ws.title == "DevOps Engineer"

    # Missing or empty rejected
    assert adapter.normalize_job({"id": "4"}) is None
    assert adapter.normalize_job({"id": "5", "text": None}) is None
    assert adapter.normalize_job({"id": "6", "text": ""}) is None
    assert adapter.normalize_job({"id": "7", "text": "   "}) is None


# ===========================================================================
# D. Description Cleaning
# ===========================================================================

def test_04_clean_lever_description_assembly_and_html_cleaning():
    """TEST D: clean_lever_description decodes entities, combines lists, strips tags, preserves breaks."""
    raw_job = {
        "description": "<div>&amp;lt;h2&amp;gt;About The Role&amp;lt;/h2&amp;gt;<p>Intro paragraph with &amp;amp; symbol.</p></div>",
        "lists": [
            {
                "text": "Requirements",
                "content": "<li>Python 3.12</li><li>FastAPI &amp; Docker</li>",
            }
        ],
        "additional": "<p>Closing notes.</p>",
    }
    cleaned = clean_lever_description(raw_job)
    assert cleaned is not None

    assert "About The Role" in cleaned
    assert "Intro paragraph with & symbol." in cleaned
    assert "Requirements" in cleaned
    assert "Python 3.12" in cleaned
    assert "FastAPI & Docker" in cleaned
    assert "Closing notes." in cleaned

    # HTML tags and entities must not appear
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "&amp;" not in cleaned
    assert "&lt;" not in cleaned
    assert "&gt;" not in cleaned

    # Edge cases
    assert clean_lever_description({}) is None
    assert clean_lever_description({"description": ""}) is None
    assert clean_lever_description({"description": "   "}) is None
    assert clean_lever_description(None) is None  # type: ignore


# ===========================================================================
# E. Optional Fields Handling
# ===========================================================================

def test_05_optional_fields_missing_safely():
    """TEST E: Optional fields are safely set to None and never fabricated."""
    adapter = LeverAdapter()
    minimal_posting = {
        "id": "min-001",
        "text": "Minimal Engineer",
    }
    job = adapter.normalize_job(minimal_posting)

    assert job is not None
    assert job.external_job_id == "min-001"
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


# ===========================================================================
# F. Location Resolution
# ===========================================================================

def test_06_location_hierarchy_and_fallbacks():
    """TEST F: Location resolves from categories.location, with allLocations and country fallbacks."""
    adapter = LeverAdapter()

    # 1. Primary categories.location
    job1 = adapter.normalize_job({
        "id": "1",
        "text": "Role 1",
        "categories": {"location": "San Francisco, CA", "allLocations": ["NYC"]},
    })
    assert job1 is not None
    assert job1.location == "San Francisco, CA"

    # 2. Fallback to allLocations[0]
    job2 = adapter.normalize_job({
        "id": "2",
        "text": "Role 2",
        "categories": {"location": None, "allLocations": ["New York, NY", "Austin, TX"]},
    })
    assert job2 is not None
    assert job2.location == "New York, NY"

    # 3. Fallback to country
    job3 = adapter.normalize_job({
        "id": "3",
        "text": "Role 3",
        "country": "US",
    })
    assert job3 is not None
    assert job3.location == "US"


# ===========================================================================
# G. Category Resolution
# ===========================================================================

def test_07_category_hierarchy_and_fallbacks():
    """TEST G: Category resolves from department, falling back to team."""
    adapter = LeverAdapter()

    # Department preferred
    job1 = adapter.normalize_job({
        "id": "1",
        "text": "Role 1",
        "categories": {"department": "Security", "team": "AppSec"},
    })
    assert job1 is not None
    assert job1.category == "Security"

    # Fallback to team
    job2 = adapter.normalize_job({
        "id": "2",
        "text": "Role 2",
        "categories": {"department": None, "team": "Infrastructure"},
    })
    assert job2 is not None
    assert job2.category == "Infrastructure"


# ===========================================================================
# H. Timestamp Conversion
# ===========================================================================

def test_08_timestamp_conversion_to_iso_utc():
    """TEST H: Epoch milliseconds converted deterministically to ISO UTC string."""
    adapter = LeverAdapter()

    # Numeric ms
    job1 = adapter.normalize_job({
        "id": "1",
        "text": "Role 1",
        "createdAt": 1711403416463,
    })
    assert job1 is not None
    assert job1.created_at == "2024-03-25T21:50:16.463000+00:00"

    # Numeric string ms
    job2 = adapter.normalize_job({
        "id": "2",
        "text": "Role 2",
        "createdAt": "1711403416463",
    })
    assert job2 is not None
    assert job2.created_at == "2024-03-25T21:50:16.463000+00:00"

    # Invalid timestamp handled safely without error
    job3 = adapter.normalize_job({
        "id": "3",
        "text": "Role 3",
        "createdAt": "not-a-timestamp",
    })
    assert job3 is not None
    assert job3.created_at == "not-a-timestamp"


# ===========================================================================
# I. HTTP Error Mapping
# ===========================================================================

def test_09_http_errors_raise_lever_api_error():
    """TEST I: HTTP 404, 429, and 500 raise typed LeverAPIError."""
    # 404 Not Found
    client_404 = _create_mock_client(status_code=404, text='{"ok":false,"error":"Document not found"}')
    adapter_404 = LeverAdapter(site="unknown_site", client=client_404)
    with pytest.raises(LeverAPIError) as exc_404:
        adapter_404.fetch_and_normalize_jobs()
    assert exc_404.value.status_code == 404
    assert "not found" in str(exc_404.value).lower()
    assert isinstance(exc_404.value, MarketSourceError)

    # 429 Rate Limited
    client_429 = _create_mock_client(status_code=429, text='{"ok":false,"error":"Rate limit exceeded"}')
    adapter_429 = LeverAdapter(site="palantir", client=client_429)
    with pytest.raises(LeverAPIError) as exc_429:
        adapter_429.fetch_and_normalize_jobs()
    assert exc_429.value.status_code == 429
    assert "rate limit" in str(exc_429.value).lower()

    # 500 Server Error
    client_500 = _create_mock_client(status_code=500, text="Internal Server Error")
    adapter_500 = LeverAdapter(site="palantir", client=client_500)
    with pytest.raises(LeverAPIError) as exc_500:
        adapter_500.fetch_and_normalize_jobs()
    assert exc_500.value.status_code == 500


# ===========================================================================
# J. Response Error Mapping
# ===========================================================================

def test_10_response_errors_raise_lever_response_error():
    """TEST J: Malformed JSON, non-list response, or Lever error dict raise typed exceptions."""
    # Malformed non-JSON
    client_bad_json = _create_mock_client(json_data=None, status_code=200, text="<html>Gateway Error</html>")
    adapter_bad = LeverAdapter(site="palantir", client=client_bad_json)
    with pytest.raises(LeverResponseError) as exc_json:
        adapter_bad.fetch_and_normalize_jobs()
    assert "JSON" in str(exc_json.value)
    assert isinstance(exc_json.value, MarketSourceError)

    # Unexpected dictionary structure (not an array)
    client_dict = _create_mock_client(json_data={"unexpected": "dict"}, status_code=200)
    adapter_dict = LeverAdapter(site="palantir", client=client_dict)
    with pytest.raises(LeverResponseError) as exc_list:
        adapter_dict.fetch_and_normalize_jobs()
    assert "not a list" in str(exc_list.value).lower()

    # Lever error dictionary e.g. {"ok": false, "error": "Invalid site"}
    client_err_dict = _create_mock_client(json_data={"ok": False, "error": "Invalid site"}, status_code=200)
    adapter_err = LeverAdapter(site="bad_site", client=client_err_dict)
    with pytest.raises(LeverAPIError) as exc_api_err:
        adapter_err.fetch_and_normalize_jobs()
    assert "Invalid site" in str(exc_api_err.value)


# ===========================================================================
# K. Network Failure Mapping
# ===========================================================================

def test_11_network_failures_raise_lever_connection_error():
    """TEST K: Timeouts and network connection errors raise LeverConnectionError."""
    # Timeout
    client_timeout = _create_mock_client(
        side_effect=httpx.TimeoutException("Connection timed out after 15.0s")
    )
    adapter_timeout = LeverAdapter(site="palantir", client=client_timeout)
    with pytest.raises(LeverConnectionError) as exc_timeout:
        adapter_timeout.fetch_and_normalize_jobs()
    assert "timed out" in str(exc_timeout.value).lower()
    assert isinstance(exc_timeout.value, MarketSourceError)

    # Connection error
    client_conn_error = _create_mock_client(
        side_effect=httpx.ConnectError("DNS failure contacting api.lever.co")
    )
    adapter_conn = LeverAdapter(site="palantir", client=client_conn_error)
    with pytest.raises(LeverConnectionError) as exc_conn:
        adapter_conn.fetch_and_normalize_jobs()
    assert "failed" in str(exc_conn.value).lower()


# ===========================================================================
# L. Configuration Handling
# ===========================================================================

def test_12_configuration_handling():
    """TEST L: Missing site raises MarketSourceConfigurationError; valid site succeeds."""
    # Missing site entirely
    mock_settings_none = MagicMock()
    mock_settings_none.LEVER_SITE = None
    with patch("app.services.market.adapters.lever_adapter.settings", mock_settings_none):
        adapter_unconfigured = LeverAdapter(site=None)
        assert adapter_unconfigured.is_configured is False
        with pytest.raises(MarketSourceConfigurationError) as exc_config:
            adapter_unconfigured.fetch_and_normalize_jobs()
        assert "lever site identifier is missing" in str(exc_config.value).lower()

    # Configured via settings
    mock_settings_val = MagicMock()
    mock_settings_val.LEVER_SITE = "env_lever_site"
    with patch("app.services.market.adapters.lever_adapter.settings", mock_settings_val):
        adapter_from_env = LeverAdapter(site=None)
        assert adapter_from_env.is_configured is True
        mock_env_client = _create_mock_client(json_data=[])
        adapter_from_env._client = mock_env_client
        assert adapter_from_env.fetch_and_normalize_jobs() == []

    # Configured via constructor
    adapter_configured = LeverAdapter(site="palantir")
    assert adapter_configured.is_configured is True
    assert adapter_configured.source_type == MarketSourceType.LEVER
    assert adapter_configured.source_name == "lever"

    # Configured via fetch argument override
    mock_client = _create_mock_client(json_data=[])
    adapter_override = LeverAdapter(site=None, client=mock_client)
    jobs = adapter_override.fetch_and_normalize_jobs(site="leverdemo")
    assert jobs == []


# ===========================================================================
# M. max_results and Bounded Fetching
# ===========================================================================

def test_13_max_results_bounded_fetching():
    """TEST M: max_results deterministically slices results after normalization."""
    mock_client = _create_mock_client(json_data=SAMPLE_LEVER_RESPONSE)
    adapter = LeverAdapter(site="palantir", client=mock_client)

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
# N. Query Filtering
# ===========================================================================

def test_14_deterministic_query_filtering():
    """TEST N: Query keywords filter deterministically and case-insensitively without an LLM."""
    mock_client = _create_mock_client(json_data=SAMPLE_LEVER_RESPONSE)
    adapter = LeverAdapter(site="palantir", client=mock_client)

    # Filter by title keyword "Distributed"
    jobs_dist = adapter.fetch_and_normalize_jobs(queries=["distributed"])
    assert len(jobs_dist) == 1
    assert jobs_dist[0].title == "Senior Distributed Systems Engineer"

    # Filter by description keyword "Figma" (case-insensitive)
    jobs_figma = adapter.fetch_and_normalize_jobs(queries=["FIGMA"])
    assert len(jobs_figma) == 1
    assert jobs_figma[0].title == "Product Designer"

    # Filter by keyword matching multiple postings: "Python" matches Distributed and Data Infrastructure
    jobs_python = adapter.fetch_and_normalize_jobs(queries=["Python"])
    assert len(jobs_python) == 2
    assert {j.title for j in jobs_python} == {
        "Senior Distributed Systems Engineer",
        "Data Infrastructure Engineer",
    }

    # Query with no match returns empty list without error
    jobs_none = adapter.fetch_and_normalize_jobs(queries=["NonexistentTermXYZ"])
    assert jobs_none == []

    # Empty query list returns all jobs
    jobs_empty = adapter.fetch_and_normalize_jobs(queries=[])
    assert len(jobs_empty) == 3


# ===========================================================================
# O. Registry Integration
# ===========================================================================

def test_15_registry_resolves_lever_greenhouse_adzuna_and_rejects_ashby():
    """TEST O: Registry resolves LEVER, GREENHOUSE, ADZUNA; rejects ASHBY; rejects unknown; no fallback."""
    registry = MarketSourceRegistry()

    # Resolves LEVER via enum and string
    lever_adapter_enum = registry.get_adapter(MarketSourceType.LEVER)
    assert isinstance(lever_adapter_enum, LeverAdapter)
    assert lever_adapter_enum.source_type == MarketSourceType.LEVER
    assert lever_adapter_enum.source_name == "lever"

    lever_adapter_str = registry.get_adapter("lever")
    assert isinstance(lever_adapter_str, LeverAdapter)

    lever_adapter_upper = registry.get_adapter("LEVER")
    assert isinstance(lever_adapter_upper, LeverAdapter)

    # is_supported returns True for LEVER
    assert registry.is_supported(MarketSourceType.LEVER) is True
    assert registry.is_supported("lever") is True

    # Global convenience helper resolves LEVER
    global_lever = get_market_source_adapter("lever")
    assert isinstance(global_lever, LeverAdapter)

    # Resolves GREENHOUSE
    gh_adapter = registry.get_adapter(MarketSourceType.GREENHOUSE)
    assert isinstance(gh_adapter, GreenhouseAdapter)
    assert registry.is_supported(MarketSourceType.GREENHOUSE) is True

    # Resolves ADZUNA
    adzuna_adapter = registry.get_adapter(MarketSourceType.ADZUNA)
    assert isinstance(adzuna_adapter, AdzunaAdapter)
    assert registry.is_supported(MarketSourceType.ADZUNA) is True

    # Continues rejecting ASHBY with UnsupportedMarketSourceError
    with pytest.raises(UnsupportedMarketSourceError) as exc_ashby:
        registry.get_adapter(MarketSourceType.ASHBY)
    assert "Market source 'ashby' is not implemented yet" in str(exc_ashby.value)
    assert registry.is_supported(MarketSourceType.ASHBY) is False

    # Continues rejecting unknown sources with UnknownMarketSourceError
    with pytest.raises(UnknownMarketSourceError):
        registry.get_adapter("workday")
    assert registry.is_supported("workday") is False

    # NEVER silently falls back to another source
    assert registry.get_adapter("lever") is not adzuna_adapter
    assert registry.get_adapter("lever") is not gh_adapter


# ===========================================================================
# P. Downstream NormalizedMarketJob Compatibility
# ===========================================================================

def test_16_normalized_market_job_downstream_contract_adherence():
    """TEST P: NormalizedMarketJob from Lever integrates directly into downstream contract."""
    adapter = LeverAdapter()
    job = adapter.normalize_job(SAMPLE_LEVER_POSTING)
    assert job is not None

    # Test to_dict serialization
    job_dict = job.to_dict()
    assert job_dict["source"] == "lever"
    assert job_dict["external_job_id"] == "ac978161-6f46-4f6b-ad9e-a258e642751c"
    assert job_dict["title"] == "Senior Distributed Systems Engineer"
    assert job_dict["location"] == "London, United Kingdom"
    assert job_dict["category"] == "Engineering"
    assert job_dict["contract_type"] == "Full-time"
    assert job_dict["redirect_url"] == "https://jobs.lever.co/palantir/ac978161-6f46-4f6b-ad9e-a258e642751c"
    assert job_dict["created_at"] == "2024-03-25T21:50:16.463000+00:00"

    # Test deduplication key
    assert job.deduplication_key == ("lever", "ac978161-6f46-4f6b-ad9e-a258e642751c")

    # Already normalized job passes through normalize_job unchanged
    re_normalized = adapter.normalize_job(job)
    assert re_normalized is job
