"""
Adzuna API client foundation for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-A.

Provides a secure, isolated HTTP client for the Adzuna Job Search API.
Adheres to SkillForge AI architecture:
- Explicit credentials via environment / configuration.
- Strict secret redaction across all URLs, logs, and exceptions.
- Preserves raw upstream data for downstream P1 processing.
- No database persistence or demand recalculation at this stage.
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Union
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AdzunaError(Exception):
    """Base exception for all Adzuna client errors."""
    pass


class AdzunaConfigurationError(AdzunaError):
    """Raised when required Adzuna credentials (ADZUNA_APP_ID or ADZUNA_APP_KEY) are missing or blank."""
    pass


class AdzunaConnectionError(AdzunaError):
    """Raised on network failures, connection drops, or timeouts when communicating with Adzuna."""
    pass


class AdzunaAPIError(AdzunaError):
    """Raised when Adzuna API returns an HTTP 4xx or 5xx error."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AdzunaResponseError(AdzunaError):
    """Raised when Adzuna returns an unparseable, malformed, or non-JSON response."""

    def __init__(
        self,
        message: str,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.response_body = response_body


# ---------------------------------------------------------------------------
# Sanitization Utilities
# ---------------------------------------------------------------------------

def sanitize_url(url: Union[str, httpx.URL]) -> str:
    """
    Sanitizes a URL string by masking sensitive query parameters (app_id, app_key).
    Prevents secret exposure in tracebacks, logs, and exception strings.
    """
    url_str = str(url)
    url_str = re.sub(r"([?&]app_id=)[^&]+", r"\1[REDACTED]", url_str, flags=re.IGNORECASE)
    url_str = re.sub(r"([?&]app_key=)[^&]+", r"\1[REDACTED]", url_str, flags=re.IGNORECASE)
    return url_str


def sanitize_text(text: Optional[str], secrets: Optional[List[Optional[str]]] = None) -> str:
    """
    Replaces sensitive credential substrings and URL parameters with [REDACTED].
    """
    if not text:
        return ""
    result = sanitize_url(text)
    if secrets:
        for secret in secrets:
            if secret and len(secret.strip()) > 0:
                result = result.replace(secret.strip(), "[REDACTED]")
    return result


# ---------------------------------------------------------------------------
# Controlled Response Containers
# ---------------------------------------------------------------------------

@dataclass
class AdzunaJobItem:
    """
    Controlled internal representation of a single Adzuna job search result.
    Preserves all raw upstream fields in `raw_data` for downstream P1 processing
    (cleaning, deduplication, and skill extraction).
    """
    id: str
    title: str
    description: str
    company_name: Optional[str] = None
    location_name: Optional[str] = None
    category_label: Optional[str] = None
    created: Optional[str] = None
    redirect_url: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AdzunaSearchResponse:
    """
    Controlled internal representation of an Adzuna search API response.
    Retains pagination metadata, total result count, and raw response dictionary.
    """
    results: List[AdzunaJobItem]
    total_count: int
    page: int
    country: str
    raw_response: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Adzuna API Client
# ---------------------------------------------------------------------------

_UNSET = object()


class AdzunaClient:
    """
    Client for interacting with the Adzuna Job Search API.
    Post-MVP Phase 1, Checkpoint P1-A foundation.

    Features:
    - Lazy credential validation on invocation.
    - Synchronous HTTP client adhering to existing backend conventions.
    - Full secret redaction in logs and errors.
    - Parametrized country / market support (defaults to India 'in').
    - Controlled internal response structures retaining upstream provenance.
    """

    DEFAULT_COUNTRY: str = "in"
    DEFAULT_TIMEOUT_SECONDS: float = 15.0

    def __init__(
        self,
        app_id: Any = _UNSET,
        app_key: Any = _UNSET,
        base_url: Any = _UNSET,
        client: Optional[httpx.Client] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._app_id = getattr(settings, "ADZUNA_APP_ID", None) if app_id is _UNSET else app_id
        self._app_key = getattr(settings, "ADZUNA_APP_KEY", None) if app_key is _UNSET else app_key
        raw_base = getattr(settings, "ADZUNA_API_BASE_URL", "https://api.adzuna.com/v1/api") if base_url is _UNSET else base_url
        self._base_url = raw_base.rstrip("/") if raw_base else "https://api.adzuna.com/v1/api"
        self._timeout = timeout
        self._client = client or httpx.Client(timeout=self._timeout)
        self._owns_client = client is None

    @property
    def is_configured(self) -> bool:
        """Returns True if both ADZUNA_APP_ID and ADZUNA_APP_KEY are populated."""
        return bool(
            self._app_id and self._app_id.strip() and
            self._app_key and self._app_key.strip()
        )

    def validate_credentials(self) -> None:
        """
        Validates that required Adzuna credentials are configured.
        Raises AdzunaConfigurationError with an explicit error message if not.
        """
        has_id = bool(self._app_id and self._app_id.strip())
        has_key = bool(self._app_key and self._app_key.strip())

        if not has_id and not has_key:
            raise AdzunaConfigurationError(
                "Adzuna credentials missing: both ADZUNA_APP_ID and ADZUNA_APP_KEY "
                "must be configured via environment variables or settings."
            )
        if not has_id:
            raise AdzunaConfigurationError(
                "Adzuna credentials missing: ADZUNA_APP_ID must be configured via environment variables or settings."
            )
        if not has_key:
            raise AdzunaConfigurationError(
                "Adzuna credentials missing: ADZUNA_APP_KEY must be configured via environment variables or settings."
            )

    def search_jobs(
        self,
        what: Optional[str] = None,
        where: Optional[str] = None,
        page: int = 1,
        results_per_page: int = 20,
        country: str = DEFAULT_COUNTRY,
        sort_by: Optional[str] = None,
        max_days_old: Optional[int] = None,
        category: Optional[str] = None,
    ) -> AdzunaSearchResponse:
        """
        Performs a job search request against the Adzuna API.

        Args:
            what: Keyword query or job title (e.g. 'python developer').
            where: Geographic location (e.g. 'Bengaluru', 'India').
            page: Page number (1-indexed, must be >= 1).
            results_per_page: Results count per page (1 to 50).
            country: 2-letter ISO country code (e.g. 'in' for India, 'gb' for UK).
            sort_by: Sorting preference (e.g. 'date').
            max_days_old: Maximum age of job postings in days.
            category: Adzuna category tag (e.g. 'it-jobs').

        Returns:
            AdzunaSearchResponse containing parsed AdzunaJobItem list and raw metadata.

        Raises:
            AdzunaConfigurationError: If credentials are missing.
            AdzunaConnectionError: If network/timeout issues occur.
            AdzunaAPIError: If Adzuna responds with HTTP 4xx or 5xx.
            AdzunaResponseError: If response format or JSON is invalid.
            ValueError: If pagination parameters are invalid.
        """
        self.validate_credentials()

        if page < 1:
            raise ValueError("page must be an integer >= 1")
        if results_per_page < 1 or results_per_page > 50:
            raise ValueError("results_per_page must be an integer between 1 and 50")

        country_code = country.strip().lower()
        if not country_code or len(country_code) != 2:
            raise ValueError("country must be a valid 2-letter ISO code (e.g., 'in')")

        endpoint = f"{self._base_url}/jobs/{country_code}/search/{page}"

        # Construct request parameters
        params: Dict[str, Any] = {
            "app_id": self._app_id.strip(),  # type: ignore
            "app_key": self._app_key.strip(),  # type: ignore
            "results_per_page": results_per_page,
            "content-type": "application/json",
        }
        if what and what.strip():
            params["what"] = what.strip()
        if where and where.strip():
            params["where"] = where.strip()
        if sort_by and sort_by.strip():
            params["sort_by"] = sort_by.strip()
        if max_days_old is not None and max_days_old >= 0:
            params["max_days_old"] = max_days_old
        if category and category.strip():
            params["category"] = category.strip()

        headers = {
            "Accept": "application/json",
            "User-Agent": "SkillForge-AI-MarketClient/0.1.0",
        }

        logger.debug(
            "Dispatching Adzuna search request to country=%s, page=%d, what=%s",
            country_code,
            page,
            what,
        )

        secrets = [self._app_id, self._app_key]

        try:
            res = self._client.get(endpoint, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            safe_detail = sanitize_text(str(exc), secrets=secrets)
            logger.warning("Adzuna request timed out after %ss: %s", self._timeout, safe_detail)
            raise AdzunaConnectionError(
                f"Adzuna API request timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            safe_detail = sanitize_text(str(exc), secrets=secrets)
            logger.warning("Adzuna network request failed: %s", safe_detail)
            raise AdzunaConnectionError(
                f"Adzuna API network connection failed: {safe_detail}"
            ) from exc

        # Handle HTTP status codes
        if res.status_code >= 400:
            safe_body = sanitize_text(res.text, secrets=secrets)[:500]
            if res.status_code == 401:
                detail = "Adzuna authentication failed: invalid ADZUNA_APP_ID or ADZUNA_APP_KEY."
            elif res.status_code == 403:
                detail = "Adzuna request forbidden or access quota exceeded."
            elif res.status_code == 404:
                detail = f"Adzuna endpoint not found: country '{country_code}', page {page}."
            elif res.status_code == 429:
                detail = "Adzuna API rate limit exceeded. Please throttle requests."
            elif 400 <= res.status_code < 500:
                detail = f"Adzuna API client error: HTTP {res.status_code}."
            else:
                detail = (
                    f"Adzuna API server error: HTTP {res.status_code}. "
                    "The remote service may be temporarily unavailable."
                )

            logger.error("Adzuna API returned HTTP %d: %s", res.status_code, detail)
            raise AdzunaAPIError(
                message=detail,
                status_code=res.status_code,
                response_body=safe_body,
            )

        # Parse JSON safely
        try:
            data = res.json()
        except Exception as exc:
            safe_body = sanitize_text(res.text, secrets=secrets)[:500]
            logger.error("Failed to parse Adzuna response as JSON: %s", exc)
            raise AdzunaResponseError(
                f"Failed to parse Adzuna response as JSON: {exc}",
                response_body=safe_body,
            ) from exc

        if not isinstance(data, dict):
            safe_body = sanitize_text(res.text, secrets=secrets)[:500]
            raise AdzunaResponseError(
                "Invalid Adzuna response format: expected JSON object.",
                response_body=safe_body,
            )

        raw_results = data.get("results", [])
        if not isinstance(raw_results, list):
            safe_body = sanitize_text(res.text, secrets=secrets)[:500]
            raise AdzunaResponseError(
                "Invalid Adzuna response format: 'results' field must be a list.",
                response_body=safe_body,
            )

        # Parse job items into controlled structure
        job_items: List[AdzunaJobItem] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue

            company = item.get("company")
            company_name = company.get("display_name") if isinstance(company, dict) else None

            location = item.get("location")
            location_name = location.get("display_name") if isinstance(location, dict) else None

            category_obj = item.get("category")
            category_label = category_obj.get("label") if isinstance(category_obj, dict) else None

            # Safe salary conversion
            salary_min: Optional[float] = None
            if item.get("salary_min") is not None:
                try:
                    salary_min = float(item["salary_min"])
                except (ValueError, TypeError):
                    salary_min = None

            salary_max: Optional[float] = None
            if item.get("salary_max") is not None:
                try:
                    salary_max = float(item["salary_max"])
                except (ValueError, TypeError):
                    salary_max = None

            job_items.append(
                AdzunaJobItem(
                    id=str(item.get("id", "")),
                    title=str(item.get("title", "")),
                    description=str(item.get("description", "")),
                    company_name=company_name,
                    location_name=location_name,
                    category_label=category_label,
                    created=item.get("created"),
                    redirect_url=item.get("redirect_url"),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    raw_data=item,
                )
            )

        total_count = int(data.get("count", len(job_items)))

        logger.info(
            "Adzuna search succeeded for country=%s, page=%d: %d results parsed (total count=%d)",
            country_code,
            page,
            len(job_items),
            total_count,
        )

        return AdzunaSearchResponse(
            results=job_items,
            total_count=total_count,
            page=page,
            country=country_code,
            raw_response=data,
        )

    def close(self) -> None:
        """Closes the underlying HTTP client if owned by this instance."""
        if self._owns_client and self._client is not None:
            self._client.close()

    def __enter__(self) -> "AdzunaClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"AdzunaClient(base_url={self._base_url!r}, "
            f"configured={self.is_configured}, "
            f"timeout={self._timeout})"
        )
