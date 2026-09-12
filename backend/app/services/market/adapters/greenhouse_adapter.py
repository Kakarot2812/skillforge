"""
Greenhouse public Job Board API source adapter for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-H.

Adapts the official Greenhouse public Job Board API:
    https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
conforming to the MarketSourceAdapter abstraction established in P1-G.

Architectural guarantees:
- source_type = MarketSourceType.GREENHOUSE
- source = "greenhouse"
- Conforms strictly to the existing NormalizedMarketJob contract
- Public job-board data only; no private API credentials or recruitment authentication
- Preserves raw upstream data for provenance and auditability
- Deterministic text cleaning (HTML tag stripping, entity unescaping, whitespace collapsing)
- Bounded, deterministic fetching and filtering
- No LLMs, no database mutations, no downstream demand/growth modifications
"""

import html
import logging
import re
from typing import Any, Dict, List, Optional, Union

import httpx

from app.config import settings
from app.services.market.adapters.base import (
    MarketSourceAdapter,
    MarketSourceConfigurationError,
    MarketSourceError,
    MarketSourceType,
)
from app.services.market.cleaning import clean_multiline_text, collapse_whitespace
from app.services.market.models import NormalizedMarketJob

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed Domain Exceptions
# ---------------------------------------------------------------------------

class GreenhouseError(MarketSourceError):
    """Base domain exception for all Greenhouse adapter errors."""
    pass


class GreenhouseConnectionError(GreenhouseError):
    """Raised on network failures, connection drops, or timeouts when contacting Greenhouse."""
    pass


class GreenhouseAPIError(GreenhouseError):
    """Raised when the Greenhouse API returns an HTTP 4xx or 5xx status code."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class GreenhouseResponseError(GreenhouseError):
    """Raised when Greenhouse returns an unparseable, malformed, or unexpected response format."""

    def __init__(self, message: str, response_body: Optional[str] = None):
        super().__init__(message)
        self.response_body = response_body


# ---------------------------------------------------------------------------
# HTML Description Cleaning Utility
# ---------------------------------------------------------------------------

_RE_BLOCK_TAGS = re.compile(
    r"<(?:/p|/div|/h[1-6]|/li|/tr|/blockquote|br\s*/?|hr\s*/?)>",
    flags=re.IGNORECASE,
)
_RE_ALL_TAGS = re.compile(r"<[^>]+>")


def clean_greenhouse_html(raw_html: Optional[str]) -> Optional[str]:
    """
    Deterministically cleans HTML content from Greenhouse job postings.

    1. Recursively decodes HTML entities (&amp;lt;p&amp;gt; -> <p>).
    2. Converts structural block boundaries (<p>, <div>, <li>, <br>, headings)
       into newlines to preserve paragraph and list structure.
    3. Strips all remaining HTML tags.
    4. Applies clean_multiline_text to collapse inline spaces, normalize
       newlines, and convert blank strings to None.
    """
    if raw_html is None:
        return None

    stripped_input = raw_html.strip()
    if not stripped_input:
        return None

    # Greenhouse content can contain single-escaped or double-escaped entities
    unescaped = stripped_input
    for _ in range(2):
        if "&lt;" in unescaped or "&amp;" in unescaped or "&gt;" in unescaped or "&quot;" in unescaped:
            unescaped = html.unescape(unescaped)

    # Convert block boundaries to newlines before tag stripping
    with_breaks = _RE_BLOCK_TAGS.sub("\n", unescaped)

    # Strip remaining HTML tags
    tagless = _RE_ALL_TAGS.sub("", with_breaks)

    # Clean multiline whitespace deterministically preserving paragraphs
    return clean_multiline_text(tagless)


# ---------------------------------------------------------------------------
# Deterministic In-Memory Query Filtering
# ---------------------------------------------------------------------------

def _matches_query_terms(job: NormalizedMarketJob, queries: Optional[List[str]]) -> bool:
    """
    Deterministically verifies if a NormalizedMarketJob matches the requested query keywords.
    Case-insensitive substring search over title and description.
    Returns True if queries is empty, None, or if any query term matches.
    """
    if not queries:
        return True

    title_lower = (job.title or "").lower()
    desc_lower = (job.description or "").lower()

    valid_queries = [q.strip().lower() for q in queries if q and q.strip()]
    if not valid_queries:
        return True

    for term in valid_queries:
        if term in title_lower or term in desc_lower:
            return True

    return False


# ---------------------------------------------------------------------------
# Greenhouse Adapter Implementation
# ---------------------------------------------------------------------------

class GreenhouseAdapter(MarketSourceAdapter):
    """
    MarketSourceAdapter implementation for the Greenhouse public Job Board API.

    Fetches public postings from:
        GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true

    Guarantees:
    - Returns canonical NormalizedMarketJob objects (source='greenhouse').
    - Requires only the public board_token identifier.
    - Zero private credentials or recruiter API authentication.
    - Preserves external_job_id and raw_data provenance.
    - Deterministic text normalization and bounded result slicing.
    - No silent fallback to Adzuna.
    """

    DEFAULT_BASE_URL: str = "https://boards-api.greenhouse.io/v1/boards"
    DEFAULT_TIMEOUT_SECONDS: float = 15.0

    def __init__(
        self,
        board_token: Optional[str] = None,
        client: Optional[httpx.Client] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._board_token = board_token.strip() if board_token and board_token.strip() else None
        self._timeout = timeout
        raw_base = base_url or getattr(settings, "GREENHOUSE_API_BASE_URL", self.DEFAULT_BASE_URL)
        self._base_url = raw_base.rstrip("/") if raw_base else self.DEFAULT_BASE_URL
        self._client = client
        self._owns_client = client is None

    @property
    def source_type(self) -> MarketSourceType:
        """Returns MarketSourceType.GREENHOUSE."""
        return MarketSourceType.GREENHOUSE

    @property
    def source_name(self) -> str:
        """Returns canonical string identifier 'greenhouse'."""
        return MarketSourceType.GREENHOUSE.value

    @property
    def is_configured(self) -> bool:
        """
        Returns True if a public Greenhouse board token is configured either
        on this adapter instance or via settings.GREENHOUSE_BOARD_TOKEN.
        """
        token = self._resolve_board_token(raise_if_missing=False)
        return bool(token and token.strip())

    def _resolve_board_token(
        self,
        board_token: Optional[str] = None,
        raise_if_missing: bool = True,
    ) -> Optional[str]:
        """
        Resolves the active public board token from argument, instance, or settings.
        Raises MarketSourceConfigurationError if required but unavailable.
        """
        token = board_token or self._board_token or getattr(settings, "GREENHOUSE_BOARD_TOKEN", None)
        if token and token.strip():
            return token.strip()

        if raise_if_missing:
            raise MarketSourceConfigurationError(
                "Greenhouse board token is missing. A valid public board_token must be provided "
                "via argument, adapter constructor, or settings.GREENHOUSE_BOARD_TOKEN."
            )
        return None

    def fetch_and_normalize_jobs(
        self,
        queries: Optional[List[str]] = None,
        board_token: Optional[str] = None,
        max_results: Optional[int] = None,
        **kwargs: Any,
    ) -> List[NormalizedMarketJob]:
        """
        Fetches public job postings from the Greenhouse Job Board API, deterministically
        normalizes each posting into a NormalizedMarketJob, applies deterministic query
        filtering and bounded result limits.

        Args:
            queries: Optional list of keyword query filters (e.g. ['Backend', 'Python']).
            board_token: Optional board token override (e.g. 'cloudflare').
            max_results: Optional maximum number of normalized postings to return.

        Returns:
            List[NormalizedMarketJob]: Cleaned, validated, and deterministically ordered jobs.

        Raises:
            MarketSourceConfigurationError: If board_token is missing.
            GreenhouseConnectionError: If network failure or timeout occurs.
            GreenhouseAPIError: If upstream returns HTTP 4xx or 5xx.
            GreenhouseResponseError: If response is malformed or not valid JSON.
        """
        active_board_token = self._resolve_board_token(board_token=board_token, raise_if_missing=True)
        endpoint = f"{self._base_url}/{active_board_token}/jobs"
        params = {"content": "true"}
        headers = {
            "Accept": "application/json",
            "User-Agent": "SkillForge-AI-MarketClient/0.1.0",
        }

        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            logger.debug("Dispatching Greenhouse jobs request to board '%s'", active_board_token)
            res = client.get(endpoint, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            logger.warning("Greenhouse request for board '%s' timed out after %ss", active_board_token, self._timeout)
            raise GreenhouseConnectionError(
                f"Greenhouse API request for board '{active_board_token}' timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("Greenhouse network request failed for board '%s': %s", active_board_token, exc)
            raise GreenhouseConnectionError(
                f"Greenhouse API network connection failed for board '{active_board_token}': {exc}"
            ) from exc
        finally:
            if self._owns_client and self._client is None:
                client.close()

        # Handle HTTP response codes
        if res.status_code >= 400:
            if res.status_code == 404:
                detail = f"Greenhouse public job board '{active_board_token}' not found (HTTP 404)."
            elif res.status_code == 429:
                detail = f"Greenhouse API rate limit exceeded for board '{active_board_token}' (HTTP 429)."
            elif 400 <= res.status_code < 500:
                detail = f"Greenhouse API client error: HTTP {res.status_code} for board '{active_board_token}'."
            else:
                detail = (
                    f"Greenhouse API server error: HTTP {res.status_code} for board '{active_board_token}'. "
                    "The upstream service may be temporarily unavailable."
                )

            logger.error("Greenhouse API returned error: %s", detail)
            raise GreenhouseAPIError(
                message=detail,
                status_code=res.status_code,
                response_body=res.text[:500],
            )

        # Parse JSON response
        try:
            data = res.json()
        except Exception as exc:
            logger.error("Greenhouse returned unparseable JSON for board '%s': %s", active_board_token, exc)
            raise GreenhouseResponseError(
                f"Failed to parse Greenhouse response as JSON for board '{active_board_token}'.",
                response_body=res.text[:500],
            ) from exc

        if not isinstance(data, dict) or "jobs" not in data or not isinstance(data["jobs"], list):
            logger.error("Unexpected Greenhouse response shape for board '%s': missing 'jobs' list", active_board_token)
            raise GreenhouseResponseError(
                f"Greenhouse response for board '{active_board_token}' missing expected 'jobs' array.",
                response_body=res.text[:500],
            )

        raw_jobs: List[Dict[str, Any]] = data["jobs"]
        normalized_jobs: List[NormalizedMarketJob] = []

        for raw_job in raw_jobs:
            job = self.normalize_job(raw_job)
            if job is not None and _matches_query_terms(job, queries):
                normalized_jobs.append(job)

        # Deterministic ordering by external_job_id to ensure consistent output
        normalized_jobs.sort(key=lambda j: (j.title.lower(), j.external_job_id))

        # Enforce bounded result limits if specified
        if max_results is not None and max_results > 0:
            normalized_jobs = normalized_jobs[:max_results]

        logger.debug(
            "Normalized %d valid jobs from Greenhouse board '%s' (raw=%d)",
            len(normalized_jobs),
            active_board_token,
            len(raw_jobs),
        )
        return normalized_jobs

    def normalize_job(self, raw_job: Any) -> Optional[NormalizedMarketJob]:
        """
        Deterministically cleans and normalizes a raw Greenhouse posting into
        a canonical NormalizedMarketJob.

        Validation rules:
        - Must contain a valid, non-empty external_job_id (derived from 'id').
        - Must contain a valid, non-empty job title.
        - Preserves source="greenhouse".
        - Decodes HTML entities and strips tags from description while preserving breaks.
        - Extracts optional company_name, location, category, redirect_url, created_at.
        - Never fabricates missing values.
        - Preserves complete raw_data payload for provenance and auditability.

        Returns:
            NormalizedMarketJob if data quality rules are met, or None if rejected.
        """
        if isinstance(raw_job, NormalizedMarketJob):
            return raw_job

        if not isinstance(raw_job, dict):
            logger.debug("GreenhouseAdapter rejected non-dict raw_job: %s", type(raw_job))
            return None

        # 1. Validate and clean external_job_id
        raw_id = raw_job.get("id")
        if raw_id is None:
            logger.debug("GreenhouseAdapter rejected job posting: missing 'id'")
            return None
        external_job_id = collapse_whitespace(str(raw_id))
        if not external_job_id:
            logger.debug("GreenhouseAdapter rejected job posting: empty 'id'")
            return None

        # 2. Validate and clean title
        title_raw = raw_job.get("title")
        title = collapse_whitespace(str(title_raw) if title_raw is not None else None)
        if not title:
            logger.debug("GreenhouseAdapter rejected job id=%s: missing or empty title", external_job_id)
            return None

        # 3. Clean description (HTML content unescaping, block boundary preservation, whitespace collapsing)
        content_raw = raw_job.get("content")
        description = clean_greenhouse_html(str(content_raw) if content_raw is not None else None)

        # 4. Extract company name if supplied
        company_raw = raw_job.get("company_name")
        company_name = collapse_whitespace(str(company_raw) if company_raw is not None else None)

        # 5. Extract location from Greenhouse location object or offices
        location_raw = None
        loc_obj = raw_job.get("location")
        if isinstance(loc_obj, dict):
            location_raw = loc_obj.get("name")
        elif isinstance(loc_obj, str):
            location_raw = loc_obj

        # Fallback to primary office location if location.name is absent
        if not location_raw and isinstance(raw_job.get("offices"), list) and raw_job["offices"]:
            first_office = raw_job["offices"][0]
            if isinstance(first_office, dict):
                location_raw = first_office.get("location") or first_office.get("name")

        location = collapse_whitespace(str(location_raw) if location_raw is not None else None)

        # 6. Extract category / department from departments list
        category_raw = None
        if isinstance(raw_job.get("departments"), list) and raw_job["departments"]:
            first_dept = raw_job["departments"][0]
            if isinstance(first_dept, dict):
                category_raw = first_dept.get("name")

        category = collapse_whitespace(str(category_raw) if category_raw is not None else None)

        # 7. Extract redirect URL
        redirect_raw = raw_job.get("absolute_url")
        redirect_url = collapse_whitespace(str(redirect_raw) if redirect_raw is not None else None)

        # 8. Extract creation / publication timestamp
        created_raw = raw_job.get("first_published") or raw_job.get("updated_at")
        created_at = collapse_whitespace(str(created_raw) if created_raw is not None else None)

        # Contract types are not standard in the public board schema; do not fabricate
        contract_type = None
        contract_time = None

        return NormalizedMarketJob(
            source="greenhouse",
            external_job_id=external_job_id,
            title=title,
            description=description,
            company_name=company_name,
            location=location,
            category=category,
            contract_type=contract_type,
            contract_time=contract_time,
            created_at=created_at,
            redirect_url=redirect_url,
            raw_data=raw_job,
        )
