"""
Unit and integration tests for SkillForge P1-J: Ashby Market Source Adapter.

Verifies:
A. Configuration (explicit argument, constructor, settings fallback, missing/empty rejection)
B. Normalization (full valid payload, source="ashby", stable external ID, raw_data preservation)
C. External ID validation (valid UUID, missing/empty/whitespace rejection, never fabricated)
D. Title validation (valid title, missing/empty rejection)
E. Description cleaning (descriptionPlain preference, HTML fallback, block tags, entity unescaping, missing description)
F. Location mapping (primary location, postalAddress, secondaryLocations, workplaceType isolation)
G. Category mapping (department with team fallback)
H. Employment type / contract_type mapping
I. Redirect URL mapping (jobUrl with applyUrl fallback)
J. Timestamp parsing (publishedAt, createdAt, epoch ms, ISO string)
K. HTTP error mapping (404, 429, 500 mapped to AshbyAPIError)
L. Response error mapping (malformed JSON, non-dict root, missing/non-list jobs mapped to AshbyResponseError)
M. Network error mapping (timeout, connection drop mapped to AshbyConnectionError)
N. Bounded fetching (max_results limit)
O. Deterministic query filtering (case-insensitive substring over title and description)
P. Deterministic ordering ((title.lower(), external_job_id))
Q. Registry resolution (ASHBY resolves, is_supported True, register_defaults=False isolation)
R. Contract adherence (valid NormalizedMarketJob, no fabricated optional values)
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.config import settings
from app.services.market.adapters import (
    AdzunaAdapter,
    AshbyAPIError,
    AshbyAdapter,
    AshbyConnectionError,
    AshbyError,
    AshbyResponseError,
    GreenhouseAdapter,
    LeverAdapter,
    MarketSourceAdapter,
    MarketSourceConfigurationError,
    MarketSourceError,
    MarketSourceRegistry,
    MarketSourceType,
    UnknownMarketSourceError,
    UnsupportedMarketSourceError,
    clean_ashby_description,
    get_market_source_adapter,
    market_source_registry,
)
from app.services.market.adapters.ashby_adapter import (
    _extract_ashby_location,
    _format_postal_address,
    _parse_ashby_timestamp,
)
from app.services.market.models import NormalizedMarketJob


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_valid_ashby_job() -> Dict[str, Any]:
    """Provides a fully populated valid Ashby job posting dictionary."""
    return {
        "id": "d3bc1ced-3ce4-4086-a050-555055dbb1ff",
        "title": "Senior / Staff Fullstack Engineer",
        "department": "Product",
        "team": "Engineering",
        "employmentType": "FullTime",
        "location": "Europe",
        "secondaryLocations": [
            {
                "location": "Spain",
                "address": {
                    "postalAddress": {
                        "addressLocality": "Madrid",
                        "addressRegion": "Madrid",
                        "addressCountry": "Spain",
                    }
                },
            }
        ],
        "publishedAt": "2021-04-27T20:13:45.158+00:00",
        "isListed": True,
        "isRemote": True,
        "workplaceType": "Remote",
        "address": {
            "postalAddress": {
                "addressLocality": "",
                "addressRegion": "",
                "addressCountry": "European Union",
            }
        },
        "jobUrl": "https://jobs.ashbyhq.com/linear/d3bc1ced-3ce4-4086-a050-555055dbb1ff",
        "applyUrl": "https://jobs.ashbyhq.com/linear/d3bc1ced-3ce4-4086-a050-555055dbb1ff/application",
        "descriptionPlain": "We are building software for teams.\n\nRequirements:\n- Python\n- FastAPI",
        "descriptionHtml": "<p>We are building software for teams.</p><h3>Requirements:</h3><ul><li>Python</li><li>FastAPI</li></ul>",
        "company_name": "Linear",
    }


# ===========================================================================
# A. Configuration
# ===========================================================================

def test_01_configuration_resolution():
    """A. Verifies job_board configuration resolution hierarchy and validation."""
    # 1. Constructor job_board
    adapter = AshbyAdapter(job_board="linear")
    assert adapter.is_configured is True
    assert adapter._resolve_job_board() == "linear"

    # 2. Explicit argument override
    assert adapter._resolve_job_board(job_board="ashby") == "ashby"

    # 3. Settings fallback
    mock_settings = MagicMock()
    mock_settings.ASHBY_JOB_BOARD = "ramp"
    with patch("app.services.market.adapters.ashby_adapter.settings", mock_settings):
        adapter_empty = AshbyAdapter()
        assert adapter_empty.is_configured is True
        assert adapter_empty._resolve_job_board() == "ramp"

    # 4. Missing configuration raises MarketSourceConfigurationError
    mock_settings_none = MagicMock()
    mock_settings_none.ASHBY_JOB_BOARD = None
    with patch("app.services.market.adapters.ashby_adapter.settings", mock_settings_none):
        unconfigured = AshbyAdapter()
        assert unconfigured.is_configured is False
        with pytest.raises(MarketSourceConfigurationError) as exc_info:
            unconfigured._resolve_job_board()
        assert "Ashby job board identifier is missing" in str(exc_info.value)

    # 5. Empty / whitespace configuration raises MarketSourceConfigurationError
    with pytest.raises(MarketSourceConfigurationError):
        AshbyAdapter(job_board="   ")._resolve_job_board()


# ===========================================================================
# B. Full Normalization & Contract
# ===========================================================================

def test_02_successful_normalization_full_fields(sample_valid_ashby_job):
    """B. Verifies full normalization of a valid Ashby posting into NormalizedMarketJob."""
    adapter = AshbyAdapter(job_board="linear")
    job = adapter.normalize_job(sample_valid_ashby_job)

    assert job is not None
    assert isinstance(job, NormalizedMarketJob)
    assert job.source == "ashby"
    assert job.external_job_id == "d3bc1ced-3ce4-4086-a050-555055dbb1ff"
    assert job.title == "Senior / Staff Fullstack Engineer"
    assert "We are building software for teams." in job.description
    assert "FastAPI" in job.description
    assert job.company_name == "Linear"
    assert job.location == "Europe"
    assert job.category == "Product"
    assert job.contract_type == "FullTime"
    assert job.redirect_url == "https://jobs.ashbyhq.com/linear/d3bc1ced-3ce4-4086-a050-555055dbb1ff"
    assert job.created_at == "2021-04-27T20:13:45.158+00:00"
    assert job.raw_data == sample_valid_ashby_job


# ===========================================================================
# C. External ID Validation
# ===========================================================================

def test_03_external_id_validation(sample_valid_ashby_job):
    """C. Verifies stable UUID validation and rejection of missing/empty/whitespace IDs."""
    adapter = AshbyAdapter(job_board="linear")

    # Missing id
    raw_missing = dict(sample_valid_ashby_job)
    del raw_missing["id"]
    assert adapter.normalize_job(raw_missing) is None

    # None id
    raw_none = dict(sample_valid_ashby_job, id=None)
    assert adapter.normalize_job(raw_none) is None

    # Empty string id
    raw_empty = dict(sample_valid_ashby_job, id="")
    assert adapter.normalize_job(raw_empty) is None

    # Whitespace-only id
    raw_ws = dict(sample_valid_ashby_job, id="   \t\n  ")
    assert adapter.normalize_job(raw_ws) is None

    # Numeric id converted cleanly to string (never fabricated)
    raw_numeric = dict(sample_valid_ashby_job, id=987654321)
    normalized = adapter.normalize_job(raw_numeric)
    assert normalized is not None
    assert normalized.external_job_id == "987654321"


# ===========================================================================
# D. Title Validation
# ===========================================================================

def test_04_title_validation(sample_valid_ashby_job):
    """D. Verifies rejection of missing, empty, or whitespace-only job titles."""
    adapter = AshbyAdapter(job_board="linear")

    # Missing title
    raw_missing = dict(sample_valid_ashby_job)
    del raw_missing["title"]
    assert adapter.normalize_job(raw_missing) is None

    # None title
    raw_none = dict(sample_valid_ashby_job, title=None)
    assert adapter.normalize_job(raw_none) is None

    # Empty title
    raw_empty = dict(sample_valid_ashby_job, title="")
    assert adapter.normalize_job(raw_empty) is None

    # Whitespace-only title
    raw_ws = dict(sample_valid_ashby_job, title="   \n  ")
    assert adapter.normalize_job(raw_ws) is None


# ===========================================================================
# E. Description Cleaning
# ===========================================================================

def test_05_description_cleaning():
    """E. Verifies clean_ashby_description preferring descriptionPlain and falling back to HTML."""
    # 1. Preferred descriptionPlain with entities and multiline
    raw_plain = {
        "descriptionPlain": "We need Senior Engineers &amp; Leaders.\n\n&quot;SkillForge&quot; is hiring &lt;fast&gt;.",
        "descriptionHtml": "<p>Different html text</p>",
    }
    cleaned = clean_ashby_description(raw_plain)
    assert cleaned is not None
    assert 'Senior Engineers & Leaders.' in cleaned
    assert '"SkillForge" is hiring <fast>.' in cleaned

    # 2. Fallback to descriptionHtml when descriptionPlain is missing or empty
    raw_html = {
        "descriptionPlain": "   ",
        "descriptionHtml": "<div><p>Lead Developer</p><ul><li>Python &amp; Docker</li><li>FastAPI</li></ul></div>",
    }
    cleaned_html = clean_ashby_description(raw_html)
    assert cleaned_html is not None
    assert "Lead Developer" in cleaned_html
    assert "Python & Docker" in cleaned_html
    assert "FastAPI" in cleaned_html
    assert "<" not in cleaned_html
    assert ">" not in cleaned_html

    # 3. Fallback to generic description field
    raw_generic = {"description": "<p>Generic description with &lt;tags&gt;</p>"}
    assert clean_ashby_description(raw_generic) == "Generic description with <tags>"

    # 4. Missing description returns None
    assert clean_ashby_description({}) is None
    assert clean_ashby_description({"descriptionPlain": None, "descriptionHtml": ""}) is None


# ===========================================================================
# F. Location Mapping & Strict WorkplaceType Isolation
# ===========================================================================

def test_06_location_mapping_and_workplace_type_isolation():
    """F. Verifies location fallback hierarchy and STRICT isolation from workplaceType."""
    # 1. Primary location used
    job1 = {"location": "San Francisco, CA", "workplaceType": "Hybrid"}
    assert _extract_ashby_location(job1) == "San Francisco, CA"

    # 2. Primary location missing -> postalAddress used
    job2 = {
        "location": None,
        "workplaceType": "Remote",
        "address": {
            "postalAddress": {
                "addressLocality": "London",
                "addressRegion": "Greater London",
                "addressCountry": "United Kingdom",
            }
        },
    }
    assert _extract_ashby_location(job2) == "London, Greater London, United Kingdom"

    # 3. Primary location missing, postalAddress missing -> secondaryLocations[0].location used
    job3 = {
        "location": "",
        "workplaceType": "OnSite",
        "secondaryLocations": [{"location": "Austin, TX", "address": {}}],
    }
    assert _extract_ashby_location(job3) == "Austin, TX"

    # 4. secondaryLocations[0].address.postalAddress used
    job4 = {
        "location": None,
        "secondaryLocations": [
            {
                "location": "",
                "address": {
                    "postalAddress": {
                        "addressLocality": "Toronto",
                        "addressRegion": "Ontario",
                        "addressCountry": "Canada",
                    }
                },
            }
        ],
    }
    assert _extract_ashby_location(job4) == "Toronto, Ontario, Canada"

    # 5. CRITICAL: workplaceType is NEVER returned as location
    # If primary location is "Remote", it is ignored!
    job_remote = {"location": "Remote", "workplaceType": "Remote"}
    assert _extract_ashby_location(job_remote) is None

    job_hybrid = {"location": "Hybrid", "workplaceType": "Hybrid"}
    assert _extract_ashby_location(job_hybrid) is None

    job_onsite = {"location": "OnSite", "workplaceType": "OnSite"}
    assert _extract_ashby_location(job_onsite) is None

    job_on_site = {"location": "On-Site", "workplaceType": "OnSite"}
    assert _extract_ashby_location(job_on_site) is None

    # 6. If primary location is "Remote" but postalAddress has a real country -> postalAddress used
    job_remote_with_country = {
        "location": "Remote",
        "workplaceType": "Remote",
        "address": {
            "postalAddress": {
                "addressCountry": "United States",
            }
        },
    }
    assert _extract_ashby_location(job_remote_with_country) == "United States"

    # 7. Completely missing geographic data -> None (never "Remote")
    job_no_geo = {"workplaceType": "Remote", "isRemote": True}
    assert _extract_ashby_location(job_no_geo) is None


# ===========================================================================
# G. Category & Department Fallback
# ===========================================================================

def test_07_category_fallback(sample_valid_ashby_job):
    """G. Verifies department mapped to category with team fallback."""
    adapter = AshbyAdapter(job_board="linear")

    # Primary department
    raw_dept = dict(sample_valid_ashby_job, department="Product Design", team="Design")
    assert adapter.normalize_job(raw_dept).category == "Product Design"

    # Department missing -> fallback to team
    raw_team = dict(sample_valid_ashby_job, department=None, team="Infra Engineering")
    assert adapter.normalize_job(raw_team).category == "Infra Engineering"

    # Both missing -> None
    raw_none = dict(sample_valid_ashby_job, department=None, team=None)
    assert adapter.normalize_job(raw_none).category is None


# ===========================================================================
# H. Employment Type / Contract Type
# ===========================================================================

def test_08_contract_type_mapping(sample_valid_ashby_job):
    """H. Verifies employmentType mapped to contract_type."""
    adapter = AshbyAdapter(job_board="linear")

    raw_ft = dict(sample_valid_ashby_job, employmentType="FullTime")
    assert adapter.normalize_job(raw_ft).contract_type == "FullTime"

    raw_contract = dict(sample_valid_ashby_job, employmentType="Contract")
    assert adapter.normalize_job(raw_contract).contract_type == "Contract"

    raw_none = dict(sample_valid_ashby_job, employmentType=None)
    assert adapter.normalize_job(raw_none).contract_type is None


# ===========================================================================
# I. Redirect URL Fallback
# ===========================================================================

def test_09_redirect_url_fallback(sample_valid_ashby_job):
    """I. Verifies jobUrl preference with fallback to applyUrl."""
    adapter = AshbyAdapter(job_board="linear")

    # Both present -> jobUrl preferred
    assert adapter.normalize_job(sample_valid_ashby_job).redirect_url == "https://jobs.ashbyhq.com/linear/d3bc1ced-3ce4-4086-a050-555055dbb1ff"

    # jobUrl missing -> fallback to applyUrl
    raw_apply = dict(sample_valid_ashby_job, jobUrl=None)
    assert adapter.normalize_job(raw_apply).redirect_url == "https://jobs.ashbyhq.com/linear/d3bc1ced-3ce4-4086-a050-555055dbb1ff/application"

    # Both missing -> None
    raw_none = dict(sample_valid_ashby_job, jobUrl=None, applyUrl=None)
    assert adapter.normalize_job(raw_none).redirect_url is None


# ===========================================================================
# J. Timestamp Parsing
# ===========================================================================

def test_10_timestamp_parsing(sample_valid_ashby_job):
    """J. Verifies publishedAt, createdAt, epoch ms, and ISO string parsing."""
    adapter = AshbyAdapter(job_board="linear")

    # ISO string publishedAt
    raw_iso = dict(sample_valid_ashby_job, publishedAt="2024-03-04T14:29:08.532+00:00")
    assert adapter.normalize_job(raw_iso).created_at == "2024-03-04T14:29:08.532+00:00"

    # publishedAt missing -> createdAt fallback
    raw_created = dict(sample_valid_ashby_job, publishedAt=None, createdAt="2024-01-15T10:00:00Z")
    assert adapter.normalize_job(raw_created).created_at == "2024-01-15T10:00:00Z"

    # Epoch milliseconds conversion
    assert _parse_ashby_timestamp(1711403416463) == "2024-03-25T21:50:16.463000+00:00"
    assert _parse_ashby_timestamp(None) is None
    assert _parse_ashby_timestamp("") is None


# ===========================================================================
# K. HTTP Error Mapping (404, 429, 500)
# ===========================================================================

def test_11_http_errors_raise_ashby_api_error():
    """K. Verifies HTTP 404, 429, and 500 map to AshbyAPIError."""
    for status_code in (404, 429, 500, 503):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = status_code
        mock_response.text = f"Error body for {status_code}"

        mock_client = MagicMock(spec=httpx.Client)
        mock_client.get.return_value = mock_response

        adapter = AshbyAdapter(job_board="linear", client=mock_client)
        with pytest.raises(AshbyAPIError) as exc_info:
            adapter.fetch_and_normalize_jobs()

        err = exc_info.value
        assert err.status_code == status_code
        assert str(status_code) in str(err)
        assert f"Error body for {status_code}" in (err.response_body or "")


# ===========================================================================
# L. Response Error Mapping (Malformed JSON, Missing Jobs)
# ===========================================================================

def test_12_response_errors_raise_ashby_response_error():
    """L. Verifies malformed JSON and unexpected response shapes raise AshbyResponseError."""
    # 1. Non-JSON response
    mock_bad_json = MagicMock(spec=httpx.Response)
    mock_bad_json.status_code = 200
    mock_bad_json.json.side_effect = ValueError("Invalid JSON")
    mock_bad_json.text = "<html>502 Bad Gateway</html>"

    client1 = MagicMock(spec=httpx.Client)
    client1.get.return_value = mock_bad_json
    adapter1 = AshbyAdapter(job_board="linear", client=client1)

    with pytest.raises(AshbyResponseError) as exc1:
        adapter1.fetch_and_normalize_jobs()
    assert "Failed to parse Ashby response as JSON" in str(exc1.value)

    # 2. Non-dict root
    mock_list_root = MagicMock(spec=httpx.Response)
    mock_list_root.status_code = 200
    mock_list_root.json.return_value = ["not", "a", "dict"]
    mock_list_root.text = '["not", "a", "dict"]'

    client2 = MagicMock(spec=httpx.Client)
    client2.get.return_value = mock_list_root
    adapter2 = AshbyAdapter(job_board="linear", client=client2)

    with pytest.raises(AshbyResponseError) as exc2:
        adapter2.fetch_and_normalize_jobs()
    assert "not a JSON object" in str(exc2.value)

    # 3. Missing 'jobs' array
    mock_missing_jobs = MagicMock(spec=httpx.Response)
    mock_missing_jobs.status_code = 200
    mock_missing_jobs.json.return_value = {"apiVersion": "2020-04-14"}
    mock_missing_jobs.text = '{"apiVersion": "2020-04-14"}'

    client3 = MagicMock(spec=httpx.Client)
    client3.get.return_value = mock_missing_jobs
    adapter3 = AshbyAdapter(job_board="linear", client=client3)

    with pytest.raises(AshbyResponseError) as exc3:
        adapter3.fetch_and_normalize_jobs()
    assert "does not contain a 'jobs' list" in str(exc3.value)


# ===========================================================================
# M. Network Failure Mapping
# ===========================================================================

def test_13_network_failures_raise_ashby_connection_error():
    """M. Verifies timeouts and request connection errors map to AshbyConnectionError."""
    # Timeout
    client_timeout = MagicMock(spec=httpx.Client)
    client_timeout.get.side_effect = httpx.TimeoutException("Read timed out")
    adapter_timeout = AshbyAdapter(job_board="linear", client=client_timeout)

    with pytest.raises(AshbyConnectionError) as exc_timeout:
        adapter_timeout.fetch_and_normalize_jobs()
    assert "timed out" in str(exc_timeout.value)

    # Network error
    client_net = MagicMock(spec=httpx.Client)
    client_net.get.side_effect = httpx.RequestError("Connection reset by peer")
    adapter_net = AshbyAdapter(job_board="linear", client=client_net)

    with pytest.raises(AshbyConnectionError) as exc_net:
        adapter_net.fetch_and_normalize_jobs()
    assert "network connection failed" in str(exc_net.value)


# ===========================================================================
# N. Bounded Fetching (max_results)
# ===========================================================================

def test_14_max_results_bounded_fetching(sample_valid_ashby_job):
    """N. Verifies max_results slices the output cleanly and deterministically."""
    job1 = dict(sample_valid_ashby_job, id="uuid-1", title="Backend Engineer A")
    job2 = dict(sample_valid_ashby_job, id="uuid-2", title="Backend Engineer B")
    job3 = dict(sample_valid_ashby_job, id="uuid-3", title="Backend Engineer C")

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"jobs": [job1, job2, job3]}

    client = MagicMock(spec=httpx.Client)
    client.get.return_value = mock_resp

    adapter = AshbyAdapter(job_board="linear", client=client)
    bounded_jobs = adapter.fetch_and_normalize_jobs(max_results=2)

    assert len(bounded_jobs) == 2
    assert bounded_jobs[0].title == "Backend Engineer A"
    assert bounded_jobs[1].title == "Backend Engineer B"


# ===========================================================================
# O. Deterministic Query Filtering
# ===========================================================================

def test_15_deterministic_query_filtering(sample_valid_ashby_job):
    """O. Verifies case-insensitive substring search across title and description."""
    job_py = dict(
        sample_valid_ashby_job,
        id="id-1",
        title="Python Platform Architect",
        descriptionPlain="Work with distributed systems and databases.",
    )
    job_go = dict(
        sample_valid_ashby_job,
        id="id-2",
        title="Infrastructure Lead",
        descriptionPlain="Build microservices in Go and Kubernetes.",
    )

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"jobs": [job_py, job_go]}

    client = MagicMock(spec=httpx.Client)
    client.get.return_value = mock_resp

    adapter = AshbyAdapter(job_board="linear", client=client)

    # Match title
    match_title = adapter.fetch_and_normalize_jobs(queries=["python"])
    assert len(match_title) == 1
    assert match_title[0].external_job_id == "id-1"

    # Match description
    match_desc = adapter.fetch_and_normalize_jobs(queries=["kubernetes"])
    assert len(match_desc) == 1
    assert match_desc[0].external_job_id == "id-2"

    # No match
    match_none = adapter.fetch_and_normalize_jobs(queries=["rust"])
    assert len(match_none) == 0

    # Empty queries returns all
    match_empty = adapter.fetch_and_normalize_jobs(queries=[])
    assert len(match_empty) == 2


# ===========================================================================
# P. Deterministic Ordering
# ===========================================================================

def test_16_deterministic_ordering(sample_valid_ashby_job):
    """P. Verifies deterministic sorting by (title.lower(), external_job_id)."""
    job_b = dict(sample_valid_ashby_job, id="uuid-b", title="Software Engineer")
    job_a = dict(sample_valid_ashby_job, id="uuid-a", title="Backend Engineer")
    job_c = dict(sample_valid_ashby_job, id="uuid-c", title="backend engineer")

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    # Input in arbitrary scrambled order
    mock_resp.json.return_value = {"jobs": [job_b, job_c, job_a]}

    client = MagicMock(spec=httpx.Client)
    client.get.return_value = mock_resp

    adapter = AshbyAdapter(job_board="linear", client=client)
    ordered = adapter.fetch_and_normalize_jobs()

    # Ordered: ("backend engineer", "uuid-a"), ("backend engineer", "uuid-c"), ("software engineer", "uuid-b")
    assert [j.external_job_id for j in ordered] == ["uuid-a", "uuid-c", "uuid-b"]


# ===========================================================================
# Q. Registry Integration
# ===========================================================================

def test_17_registry_resolves_all_four_sources():
    """Q. Verifies default MarketSourceRegistry resolves ADZUNA, GREENHOUSE, LEVER, and ASHBY."""
    registry = MarketSourceRegistry()

    # Ashby resolves
    ashby_adapter = registry.get_adapter(MarketSourceType.ASHBY)
    assert isinstance(ashby_adapter, AshbyAdapter)
    assert ashby_adapter.source_type == MarketSourceType.ASHBY
    assert registry.is_supported(MarketSourceType.ASHBY) is True
    assert registry.is_supported("ashby") is True

    # Global convenience resolves Ashby
    global_ashby = get_market_source_adapter("ashby")
    assert isinstance(global_ashby, AshbyAdapter)

    # Other 3 sources remain operational without regression
    assert isinstance(registry.get_adapter(MarketSourceType.ADZUNA), AdzunaAdapter)
    assert isinstance(registry.get_adapter(MarketSourceType.GREENHOUSE), GreenhouseAdapter)
    assert isinstance(registry.get_adapter(MarketSourceType.LEVER), LeverAdapter)

    # Unknown source rejected
    with pytest.raises(UnknownMarketSourceError):
        registry.get_adapter("workday")
    assert registry.is_supported("workday") is False

    # Isolation: register_defaults=False treats ASHBY as unsupported
    unregistered = MarketSourceRegistry(register_defaults=False)
    with pytest.raises(UnsupportedMarketSourceError):
        unregistered.get_adapter(MarketSourceType.ASHBY)
    assert unregistered.is_supported(MarketSourceType.ASHBY) is False


# ===========================================================================
# R. Contract Adherence
# ===========================================================================

def test_18_contract_adherence(sample_valid_ashby_job):
    """R. Verifies compliance with NormalizedMarketJob and preservation of raw_data."""
    adapter = AshbyAdapter(job_board="linear")
    job = adapter.normalize_job(sample_valid_ashby_job)

    assert isinstance(job, NormalizedMarketJob)
    assert job.source == "ashby"
    assert job.raw_data == sample_valid_ashby_job

    # Optional fields missing safely (never fabricated)
    minimal_raw = {
        "id": "minimal-uuid-123",
        "title": "Minimal Title",
    }
    min_job = adapter.normalize_job(minimal_raw)
    assert min_job is not None
    assert min_job.external_job_id == "minimal-uuid-123"
    assert min_job.title == "Minimal Title"
    assert min_job.description is None
    assert min_job.company_name is None
    assert min_job.location is None
    assert min_job.category is None
    assert min_job.contract_type is None
    assert min_job.redirect_url is None
    assert min_job.created_at is None
    assert min_job.raw_data == minimal_raw
