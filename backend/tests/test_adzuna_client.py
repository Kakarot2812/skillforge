"""
Unit tests for the Adzuna API client foundation (Post-MVP P1-A).
Verifies:
- Safe request construction with authentication parameters
- Strict redaction of secrets in logs, exceptions, and repr
- Graceful handling of HTTP 4xx, 5xx, timeouts, network drops, and malformed JSON
- Controlled internal data representation preserving upstream provenance
- Parameterized market/country handling
"""

import logging
from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.services.market.clients.adzuna_client import (
    AdzunaAPIError,
    AdzunaClient,
    AdzunaConfigurationError,
    AdzunaConnectionError,
    AdzunaError,
    AdzunaJobItem,
    AdzunaResponseError,
    AdzunaSearchResponse,
    sanitize_text,
    sanitize_url,
)

# Mock credentials strictly for unit testing
MOCK_APP_ID = "mock_test_app_id_12345"
MOCK_APP_KEY = "mock_test_app_key_abcde67890"

MOCK_SUCCESSFUL_PAYLOAD = {
    "count": 142,
    "mean": 1250000.0,
    "results": [
        {
            "id": "9876543210",
            "title": "Senior Python Backend Engineer",
            "description": "Designing scalable APIs with FastAPI, PostgreSQL, and Docker in Bangalore.",
            "company": {
                "display_name": "Acme Tech Solutions"
            },
            "location": {
                "area": ["India", "Karnataka", "Bengaluru"],
                "display_name": "Bengaluru, Karnataka"
            },
            "category": {
                "label": "IT Jobs",
                "tag": "it-jobs"
            },
            "created": "2026-09-08T14:30:00Z",
            "redirect_url": "https://www.adzuna.in/land/ad/9876543210",
            "salary_min": 1200000.0,
            "salary_max": 1800000.0,
            "contract_type": "permanent",
            "contract_time": "full_time",
        },
        {
            "id": "9876543211",
            "title": "Machine Learning Engineer",
            "description": "Developing NLP and RAG pipelines using Python and PyTorch.",
            "company": {
                "display_name": "AI Innovations Lab"
            },
            "location": {
                "area": ["India", "Telangana", "Hyderabad"],
                "display_name": "Hyderabad, Telangana"
            },
            "category": {
                "label": "IT Jobs",
                "tag": "it-jobs"
            },
            "created": "2026-09-09T09:15:00Z",
            "redirect_url": "https://www.adzuna.in/land/ad/9876543211",
            "salary_min": None,
            "salary_max": None,
        },
    ],
}


# ===========================================================================
# 1. Successful API Response & Controlled Data Structures
# ===========================================================================

def test_successful_search_response_parsing():
    """Verifies that a valid Adzuna API response parses into controlled structures."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_SUCCESSFUL_PAYLOAD
    mock_response.text = '{"count": 142}'
    mock_http_client.get.return_value = mock_response

    client = AdzunaClient(
        app_id=MOCK_APP_ID,
        app_key=MOCK_APP_KEY,
        client=mock_http_client,
    )

    response = client.search_jobs(
        what="python",
        where="Bengaluru",
        page=1,
        results_per_page=20,
        country="in",
    )

    assert isinstance(response, AdzunaSearchResponse)
    assert response.total_count == 142
    assert response.page == 1
    assert response.country == "in"
    assert len(response.results) == 2

    first_job = response.results[0]
    assert isinstance(first_job, AdzunaJobItem)
    assert first_job.id == "9876543210"
    assert first_job.title == "Senior Python Backend Engineer"
    assert "FastAPI" in first_job.description
    assert first_job.company_name == "Acme Tech Solutions"
    assert first_job.location_name == "Bengaluru, Karnataka"
    assert first_job.category_label == "IT Jobs"
    assert first_job.salary_min == 1200000.0
    assert first_job.salary_max == 1800000.0
    assert first_job.raw_data == MOCK_SUCCESSFUL_PAYLOAD["results"][0]

    # Verify second job with null salaries
    second_job = response.results[1]
    assert second_job.id == "9876543211"
    assert second_job.salary_min is None
    assert second_job.salary_max is None

    # Upstream provenance is preserved
    assert response.raw_response == MOCK_SUCCESSFUL_PAYLOAD


# ===========================================================================
# 2. Missing Credentials Handling
# ===========================================================================

def test_missing_app_id_raises_configuration_error():
    """Verifies that a missing ADZUNA_APP_ID produces an explicit configuration error."""
    client = AdzunaClient(app_id=None, app_key="valid_key_present")
    with pytest.raises(AdzunaConfigurationError) as exc_info:
        client.validate_credentials()

    err_msg = str(exc_info.value)
    assert "ADZUNA_APP_ID" in err_msg
    assert "valid_key_present" not in err_msg


def test_missing_app_key_raises_configuration_error():
    """Verifies that a missing ADZUNA_APP_KEY produces an explicit configuration error."""
    client = AdzunaClient(app_id="valid_id_present", app_key=None)
    with pytest.raises(AdzunaConfigurationError) as exc_info:
        client.validate_credentials()

    err_msg = str(exc_info.value)
    assert "ADZUNA_APP_KEY" in err_msg
    assert "valid_id_present" not in err_msg


def test_missing_both_credentials_raises_configuration_error():
    """Verifies that missing both credentials produces an explicit configuration error."""
    client = AdzunaClient(app_id=None, app_key=None)
    with pytest.raises(AdzunaConfigurationError) as exc_info:
        client.validate_credentials()

    err_msg = str(exc_info.value)
    assert "ADZUNA_APP_ID" in err_msg
    assert "ADZUNA_APP_KEY" in err_msg


def test_search_jobs_fails_immediately_if_credentials_missing():
    """Ensures search_jobs triggers configuration validation before any network call."""
    mock_http_client = MagicMock(spec=httpx.Client)
    client = AdzunaClient(app_id=None, app_key=None, client=mock_http_client)

    with pytest.raises(AdzunaConfigurationError):
        client.search_jobs(what="engineer")

    # Network client should never have been invoked
    mock_http_client.get.assert_not_called()


# ===========================================================================
# 3. HTTP Error Handling (4xx & 5xx)
# ===========================================================================

@pytest.mark.parametrize(
    "status_code,expected_message_fragment",
    [
        (400, "Adzuna API client error: HTTP 400"),
        (401, "Adzuna authentication failed"),
        (403, "Adzuna request forbidden"),
        (404, "Adzuna endpoint not found"),
        (429, "Adzuna API rate limit exceeded"),
    ],
)
def test_http_4xx_errors(status_code, expected_message_fragment):
    """Verifies clean handling of various HTTP 4xx client errors."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_res = MagicMock(spec=httpx.Response)
    mock_res.status_code = status_code
    mock_res.text = f"Error details for {status_code}"
    mock_http_client.get.return_value = mock_res

    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY, client=mock_http_client)

    with pytest.raises(AdzunaAPIError) as exc_info:
        client.search_jobs(what="python")

    err = exc_info.value
    assert err.status_code == status_code
    assert expected_message_fragment in str(err)
    assert MOCK_APP_ID not in str(err)
    assert MOCK_APP_KEY not in str(err)


@pytest.mark.parametrize("status_code", [500, 502, 503, 504])
def test_http_5xx_server_errors(status_code):
    """Verifies clean handling of upstream HTTP 5xx server errors."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_res = MagicMock(spec=httpx.Response)
    mock_res.status_code = status_code
    mock_res.text = "Internal Server Error"
    mock_http_client.get.return_value = mock_res

    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY, client=mock_http_client)

    with pytest.raises(AdzunaAPIError) as exc_info:
        client.search_jobs(what="python")

    err = exc_info.value
    assert err.status_code == status_code
    assert "server error" in str(err).lower()
    assert MOCK_APP_ID not in str(err)
    assert MOCK_APP_KEY not in str(err)


# ===========================================================================
# 4. Timeout and Network Failure Handling
# ===========================================================================

def test_timeout_exception_handling():
    """Verifies that httpx.TimeoutException maps cleanly to AdzunaConnectionError."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_http_client.get.side_effect = httpx.TimeoutException(
        f"Connect to api.adzuna.com?app_id={MOCK_APP_ID}&app_key={MOCK_APP_KEY} timed out"
    )

    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY, client=mock_http_client)

    with pytest.raises(AdzunaConnectionError) as exc_info:
        client.search_jobs(what="python")

    err_str = str(exc_info.value)
    assert "timed out" in err_str.lower()
    # Ensure sensitive credentials were not leaked
    assert MOCK_APP_ID not in err_str
    assert MOCK_APP_KEY not in err_str


def test_network_request_error_handling():
    """Verifies that httpx.RequestError maps cleanly to AdzunaConnectionError."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_http_client.get.side_effect = httpx.ConnectError(
        f"Connection refused at https://api.adzuna.com/v1/api/jobs/in/search/1?app_id={MOCK_APP_ID}&app_key={MOCK_APP_KEY}"
    )

    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY, client=mock_http_client)

    with pytest.raises(AdzunaConnectionError) as exc_info:
        client.search_jobs(what="python")

    err_str = str(exc_info.value)
    assert "network connection failed" in err_str.lower()
    assert MOCK_APP_ID not in err_str
    assert MOCK_APP_KEY not in err_str


# ===========================================================================
# 5. Invalid / Non-JSON Response Handling
# ===========================================================================

def test_non_json_response_handling():
    """Verifies safe error handling when response body is not valid JSON."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_res = MagicMock(spec=httpx.Response)
    mock_res.status_code = 200
    mock_res.text = "<html><body>502 Bad Gateway Nginx</body></html>"
    mock_res.json.side_effect = ValueError("Expecting value: line 1 column 1")
    mock_http_client.get.return_value = mock_res

    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY, client=mock_http_client)

    with pytest.raises(AdzunaResponseError) as exc_info:
        client.search_jobs(what="python")

    err = exc_info.value
    assert "Failed to parse Adzuna response as JSON" in str(err)
    assert "502 Bad Gateway" in err.response_body


def test_non_dict_json_response_handling():
    """Verifies safe error handling when response JSON is a list instead of an object."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_res = MagicMock(spec=httpx.Response)
    mock_res.status_code = 200
    mock_res.text = '["job1", "job2"]'
    mock_res.json.return_value = ["job1", "job2"]
    mock_http_client.get.return_value = mock_res

    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY, client=mock_http_client)

    with pytest.raises(AdzunaResponseError) as exc_info:
        client.search_jobs(what="python")

    assert "expected JSON object" in str(exc_info.value)


def test_results_field_not_a_list_handling():
    """Verifies safe error handling when 'results' field is not a list."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_res = MagicMock(spec=httpx.Response)
    mock_res.status_code = 200
    mock_res.text = '{"results": "invalid"}'
    mock_res.json.return_value = {"results": "invalid"}
    mock_http_client.get.return_value = mock_res

    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY, client=mock_http_client)

    with pytest.raises(AdzunaResponseError) as exc_info:
        client.search_jobs(what="python")

    assert "'results' field must be a list" in str(exc_info.value)


# ===========================================================================
# 6. Security & Credential Redaction Verification
# ===========================================================================

def test_credentials_never_appear_in_logs(caplog):
    """Verifies that secrets never appear in application logs across failure scenarios."""
    mock_http_client = MagicMock(spec=httpx.Client)
    # Simulate an error response body that echo-backs the parameters
    mock_res = MagicMock(spec=httpx.Response)
    mock_res.status_code = 401
    mock_res.text = f"Unauthorized: invalid app_key={MOCK_APP_KEY} or app_id={MOCK_APP_ID}"
    mock_http_client.get.return_value = mock_res

    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY, client=mock_http_client)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(AdzunaAPIError) as exc_info:
            client.search_jobs(what="python")

    # Check exception content
    err_str = str(exc_info.value)
    assert MOCK_APP_ID not in err_str
    assert MOCK_APP_KEY not in err_str
    assert exc_info.value.response_body is not None
    assert MOCK_APP_ID not in exc_info.value.response_body
    assert MOCK_APP_KEY not in exc_info.value.response_body

    # Check all captured log output
    full_log_text = caplog.text
    assert MOCK_APP_ID not in full_log_text
    assert MOCK_APP_KEY not in full_log_text


def test_repr_does_not_leak_credentials():
    """Verifies that AdzunaClient.__repr__ does not reveal secrets."""
    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY)
    repr_str = repr(client)

    assert "AdzunaClient" in repr_str
    assert "configured=True" in repr_str
    assert MOCK_APP_ID not in repr_str
    assert MOCK_APP_KEY not in repr_str


def test_sanitize_utilities():
    """Unit tests for standalone sanitization helpers."""
    dirty_url = f"https://api.adzuna.com/v1/api/jobs/in/search/1?app_id={MOCK_APP_ID}&what=python&app_key={MOCK_APP_KEY}"
    clean_url = sanitize_url(dirty_url)

    assert MOCK_APP_ID not in clean_url
    assert MOCK_APP_KEY not in clean_url
    assert "app_id=[REDACTED]" in clean_url
    assert "app_key=[REDACTED]" in clean_url
    assert "what=python" in clean_url

    text = f"Traceback error with key {MOCK_APP_KEY} and id {MOCK_APP_ID}"
    clean_text = sanitize_text(text, secrets=[MOCK_APP_ID, MOCK_APP_KEY])
    assert MOCK_APP_ID not in clean_text
    assert MOCK_APP_KEY not in clean_text
    assert "[REDACTED]" in clean_text


# ===========================================================================
# 7. Request Construction & Authentication Parameter Verification
# ===========================================================================

def test_request_construction_sends_required_parameters():
    """Verifies that requests are constructed with correct endpoints, query parameters, and headers."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_res = MagicMock(spec=httpx.Response)
    mock_res.status_code = 200
    mock_res.json.return_value = {"count": 0, "results": []}
    mock_res.text = "{}"
    mock_http_client.get.return_value = mock_res

    client = AdzunaClient(
        app_id=MOCK_APP_ID,
        app_key=MOCK_APP_KEY,
        client=mock_http_client,
    )

    client.search_jobs(
        what="fastapi developer",
        where="Bengaluru",
        page=3,
        results_per_page=35,
        country="in",
        sort_by="date",
        max_days_old=14,
        category="it-jobs",
    )

    mock_http_client.get.assert_called_once()
    call_args = mock_http_client.get.call_args
    endpoint = call_args[0][0]
    kwargs = call_args[1]

    # Verify endpoint path
    assert endpoint == "https://api.adzuna.com/v1/api/jobs/in/search/3"

    # Verify query parameters
    params = kwargs["params"]
    assert params["app_id"] == MOCK_APP_ID
    assert params["app_key"] == MOCK_APP_KEY
    assert params["what"] == "fastapi developer"
    assert params["where"] == "Bengaluru"
    assert params["results_per_page"] == 35
    assert params["sort_by"] == "date"
    assert params["max_days_old"] == 14
    assert params["category"] == "it-jobs"
    assert params["content-type"] == "application/json"

    # Verify headers
    headers = kwargs["headers"]
    assert headers["Accept"] == "application/json"
    assert "SkillForge-AI-MarketClient" in headers["User-Agent"]


# ===========================================================================
# 8. Country / Market Parameterization
# ===========================================================================

def test_market_parameterization_defaults_to_india():
    """Verifies default country code is India 'in' and is configurable."""
    mock_http_client = MagicMock(spec=httpx.Client)
    mock_res = MagicMock(spec=httpx.Response)
    mock_res.status_code = 200
    mock_res.json.return_value = {"count": 0, "results": []}
    mock_res.text = "{}"
    mock_http_client.get.return_value = mock_res

    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY, client=mock_http_client)

    # Default call (India)
    client.search_jobs()
    endpoint_in = mock_http_client.get.call_args[0][0]
    assert "/jobs/in/search/1" in endpoint_in

    # Explicit alternative country call (e.g., UK)
    client.search_jobs(country="gb")
    endpoint_gb = mock_http_client.get.call_args[0][0]
    assert "/jobs/gb/search/1" in endpoint_gb


def test_invalid_country_code_raises_value_error():
    """Verifies that malformed country codes raise ValueError."""
    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY)

    with pytest.raises(ValueError) as exc_info:
        client.search_jobs(country="india")
    assert "2-letter ISO code" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        client.search_jobs(country="")
    assert "2-letter ISO code" in str(exc_info.value)


# ===========================================================================
# 9. Pagination Validation
# ===========================================================================

@pytest.mark.parametrize("invalid_page", [0, -1, -10])
def test_invalid_page_raises_value_error(invalid_page):
    """Verifies that page numbers < 1 are rejected."""
    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY)
    with pytest.raises(ValueError) as exc_info:
        client.search_jobs(page=invalid_page)
    assert "page must be an integer >= 1" in str(exc_info.value)


@pytest.mark.parametrize("invalid_rpp", [0, -1, 51, 100])
def test_invalid_results_per_page_raises_value_error(invalid_rpp):
    """Verifies results_per_page outside [1, 50] are rejected."""
    client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY)
    with pytest.raises(ValueError) as exc_info:
        client.search_jobs(results_per_page=invalid_rpp)
    assert "between 1 and 50" in str(exc_info.value)


# ===========================================================================
# 10. Context Manager Support
# ===========================================================================

def test_context_manager_lifecycle():
    """Verifies that AdzunaClient supports with statement and closes underlying client."""
    mock_http_client = MagicMock(spec=httpx.Client)

    with AdzunaClient(
        app_id=MOCK_APP_ID,
        app_key=MOCK_APP_KEY,
        client=mock_http_client,
    ) as client:
        assert client.is_configured is True

    # When an external client is injected, it is not owned, so client.close() leaves it to caller
    # Let's test client ownership behavior
    owned_client = AdzunaClient(app_id=MOCK_APP_ID, app_key=MOCK_APP_KEY)
    assert owned_client._owns_client is True
    with patch.object(owned_client._client, "close") as mock_close:
        owned_client.close()
        mock_close.assert_called_once()
