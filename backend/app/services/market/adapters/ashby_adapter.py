"""
Ashby public Job Board Posting API source adapter for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-J.

Adapts the official Ashby public Job Board Posting API:
    https://api.ashbyhq.com/posting-api/job-board/{job_board}
conforming to the MarketSourceAdapter abstraction established in P1-G.

Architectural guarantees:
- source_type = MarketSourceType.ASHBY
- source = "ashby"
- Conforms strictly to the existing NormalizedMarketJob contract
- Public job-posting data only; zero private recruiting credentials or API keys
- Preserves raw upstream data for provenance and auditability
- Deterministic text cleaning (descriptionPlain preferred, HTML tag stripping, entity unescaping)
- Strict geographical location extraction (workplaceType NEVER used as location)
- Bounded, deterministic fetching and filtering
- Deterministic ordering by (title.lower(), external_job_id)
- No LLMs, no database mutations, no downstream demand/growth modifications
"""

from datetime import datetime, timezone
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

class AshbyError(MarketSourceError):
    """Base domain exception for all Ashby adapter errors."""
    pass


class AshbyConnectionError(AshbyError):
    """Raised on network failures, connection drops, or timeouts when contacting Ashby."""
    pass


class AshbyAPIError(AshbyError):
    """Raised when the Ashby API returns an HTTP 4xx or 5xx status code."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AshbyResponseError(AshbyError):
    """Raised when Ashby returns an unparseable, malformed, or unexpected response format."""

    def __init__(self, message: str, response_body: Optional[str] = None):
        super().__init__(message)
        self.response_body = response_body


# ---------------------------------------------------------------------------
# Description Cleaning Utility
# ---------------------------------------------------------------------------

_RE_BLOCK_TAGS = re.compile(
    r"<(?:/p|/div|/h[1-6]|/li|/tr|/blockquote|br\s*/?|hr\s*/?)>",
    flags=re.IGNORECASE,
)
_RE_ALL_TAGS = re.compile(r"<[^>]+>")


def clean_ashby_description(raw_job: Dict[str, Any]) -> Optional[str]:
    """
    Deterministically cleans job description text from an Ashby posting.

    Preferred source:
    - descriptionPlain

    If descriptionPlain exists and is non-empty:
    - HTML entity unescape (handling potential single or double escaping)
    - clean_multiline_text for whitespace normalization
    - return cleaned text

    If descriptionPlain is unavailable/empty, fallback to descriptionHtml or description:
    1. convert block tags to newlines: </p>, </div>, </li>, <br>, headings, etc.
    2. strip remaining HTML tags
    3. HTML entity unescape
    4. clean_multiline_text

    Returns None if no usable description exists.
    """
    if not isinstance(raw_job, dict):
        return None

    # 1. Preferred source: descriptionPlain
    plain = raw_job.get("descriptionPlain")
    if plain and isinstance(plain, str) and plain.strip():
        unescaped = plain
        for _ in range(2):
            if any(ent in unescaped for ent in ("&lt;", "&amp;", "&gt;", "&quot;", "&#")):
                unescaped = html.unescape(unescaped)
        cleaned = clean_multiline_text(unescaped)
        if cleaned:
            return cleaned

    # 2. Fallback: descriptionHtml or description
    html_desc = raw_job.get("descriptionHtml") or raw_job.get("description")
    if html_desc and isinstance(html_desc, str) and html_desc.strip():
        # 1. Convert block tags to newlines
        with_breaks = _RE_BLOCK_TAGS.sub("\n", html_desc.strip())
        # 2. Strip remaining HTML tags
        tagless = _RE_ALL_TAGS.sub("", with_breaks)
        # 3. HTML entity unescape
        unescaped = tagless
        for _ in range(2):
            if any(ent in unescaped for ent in ("&lt;", "&amp;", "&gt;", "&quot;", "&#")):
                unescaped = html.unescape(unescaped)
        # 4. Apply clean_multiline_text
        cleaned = clean_multiline_text(unescaped)
        if cleaned:
            return cleaned

    return None


# ---------------------------------------------------------------------------
# Location Extraction Utility
# ---------------------------------------------------------------------------

def _format_postal_address(postal: Any) -> Optional[str]:
    """Helper to format a postalAddress dictionary into a geographic location string."""
    if not isinstance(postal, dict):
        return None
    parts = []
    for field in ("addressLocality", "addressRegion", "addressCountry"):
        val = postal.get(field)
        if val and isinstance(val, str) and val.strip():
            parts.append(val.strip())
    if parts:
        res = ", ".join(parts)
        if res.lower() not in ("remote", "hybrid", "onsite", "on-site"):
            return res
    return None


def _extract_ashby_location(raw_job: Dict[str, Any]) -> Optional[str]:
    """
    Deterministically extracts geographical location from an Ashby posting.

    Hierarchy:
    1. raw_job["location"]
    2. raw_job["address"]["postalAddress"]
    3. raw_job["secondaryLocations"][0]["location"]
    4. raw_job["secondaryLocations"][0]["address"]["postalAddress"]
    5. None

    CRITICAL RULES:
    - workplaceType MUST NEVER be used as a location.
    - Values 'Remote', 'Hybrid', 'OnSite' are workplace arrangements, NOT geographical locations.
    - Never return any of those values as NormalizedMarketJob.location.
    - If primary location is missing or equals a workplace arrangement and no geographical
      location is available, location must remain None.
    """
    if not isinstance(raw_job, dict):
        return None

    FORBIDDEN_LOCATIONS = {"remote", "hybrid", "onsite", "on-site"}

    # 1. Primary location
    loc = raw_job.get("location")
    if loc and isinstance(loc, str) and loc.strip():
        cleaned = collapse_whitespace(loc)
        if cleaned and cleaned.lower() not in FORBIDDEN_LOCATIONS:
            return cleaned

    # 2. raw_job["address"]["postalAddress"]
    address = raw_job.get("address")
    if isinstance(address, dict):
        postal = address.get("postalAddress")
        postal_str = _format_postal_address(postal)
        if postal_str and postal_str.lower() not in FORBIDDEN_LOCATIONS:
            return collapse_whitespace(postal_str)

    # 3. raw_job["secondaryLocations"][0]
    secondary = raw_job.get("secondaryLocations")
    if isinstance(secondary, list) and secondary:
        first_sec = secondary[0]
        if isinstance(first_sec, dict):
            sec_loc = first_sec.get("location")
            if sec_loc and isinstance(sec_loc, str) and sec_loc.strip():
                cleaned_sec = collapse_whitespace(sec_loc)
                if cleaned_sec and cleaned_sec.lower() not in FORBIDDEN_LOCATIONS:
                    return cleaned_sec

            sec_addr = first_sec.get("address")
            if isinstance(sec_addr, dict):
                sec_postal = sec_addr.get("postalAddress")
                sec_postal_str = _format_postal_address(sec_postal)
                if sec_postal_str and sec_postal_str.lower() not in FORBIDDEN_LOCATIONS:
                    return collapse_whitespace(sec_postal_str)

    return None


# ---------------------------------------------------------------------------
# Timestamp Parsing Utility
# ---------------------------------------------------------------------------

def _parse_ashby_timestamp(raw_ts: Any) -> Optional[str]:
    """
    Parses an Ashby timestamp (ISO 8601 string or epoch milliseconds)
    into an ISO 8601 UTC timestamp string.
    """
    if raw_ts is None:
        return None

    if isinstance(raw_ts, (int, float)):
        try:
            dt = datetime.fromtimestamp(raw_ts / 1000.0, tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            return None

    if isinstance(raw_ts, str):
        cleaned = collapse_whitespace(raw_ts)
        if not cleaned:
            return None
        if cleaned.isdigit():
            try:
                dt = datetime.fromtimestamp(int(cleaned) / 1000.0, tz=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass
        return cleaned

    return None


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
# Ashby Adapter Implementation
# ---------------------------------------------------------------------------

class AshbyAdapter(MarketSourceAdapter):
    """
    MarketSourceAdapter implementation for the Ashby public Job Board Posting API.

    Fetches public postings from:
        GET https://api.ashbyhq.com/posting-api/job-board/{job_board}

    Guarantees:
    - Returns canonical NormalizedMarketJob objects (source='ashby').
    - Requires only the public job board identifier (e.g. 'linear', 'ashby', 'ramp').
    - Zero private credentials or recruiter API authentication.
    - Preserves external_job_id (stable UUID) and raw_data provenance.
    - Deterministic text normalization, geographic location extraction, query filtering.
    - Deterministic ordering by (title.lower(), external_job_id).
    - No silent fallback to other sources.
    """

    DEFAULT_BASE_URL: str = "https://api.ashbyhq.com/posting-api/job-board"
    DEFAULT_TIMEOUT_SECONDS: float = 15.0

    def __init__(
        self,
        job_board: Optional[str] = None,
        client: Optional[httpx.Client] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._job_board = job_board.strip() if job_board and job_board.strip() else None
        self._timeout = timeout
        raw_base = base_url or getattr(settings, "ASHBY_API_BASE_URL", self.DEFAULT_BASE_URL)
        self._base_url = raw_base.rstrip("/") if raw_base else self.DEFAULT_BASE_URL
        self._client = client
        self._owns_client = client is None

    @property
    def source_type(self) -> MarketSourceType:
        """Returns MarketSourceType.ASHBY."""
        return MarketSourceType.ASHBY

    @property
    def source_name(self) -> str:
        """Returns canonical string identifier 'ashby'."""
        return MarketSourceType.ASHBY.value

    @property
    def is_configured(self) -> bool:
        """
        Returns True if a public Ashby job board identifier is configured either
        on this adapter instance or via settings.ASHBY_JOB_BOARD.
        """
        job_board = self._resolve_job_board(raise_if_missing=False)
        return bool(job_board and job_board.strip())

    def _resolve_job_board(
        self,
        job_board: Optional[str] = None,
        raise_if_missing: bool = True,
    ) -> Optional[str]:
        """
        Resolves the active public job board identifier from argument, instance, or settings.
        Raises MarketSourceConfigurationError if required but unavailable.
        """
        effective_board = job_board or self._job_board or getattr(settings, "ASHBY_JOB_BOARD", None)
        if effective_board and effective_board.strip():
            return effective_board.strip()

        if raise_if_missing:
            raise MarketSourceConfigurationError(
                "Ashby job board identifier is missing. A valid public job board identifier must be provided "
                "via argument, adapter constructor, or settings.ASHBY_JOB_BOARD."
            )
        return None

    def fetch_and_normalize_jobs(
        self,
        queries: Optional[List[str]] = None,
        job_board: Optional[str] = None,
        max_results: Optional[int] = None,
        **kwargs: Any,
    ) -> List[NormalizedMarketJob]:
        """
        Fetches public job postings from the Ashby Job Board Posting API, deterministically
        normalizes each posting into a NormalizedMarketJob, applies deterministic query
        filtering and bounded result limits.

        Args:
            queries: Optional list of keyword query filters (e.g. ['Backend', 'Python']).
            job_board: Optional job board identifier override (e.g. 'linear').
            max_results: Optional maximum number of normalized postings to return.

        Returns:
            List[NormalizedMarketJob]: Cleaned, validated, and deterministically ordered jobs.

        Raises:
            MarketSourceConfigurationError: If job_board is missing.
            AshbyConnectionError: If network failure or timeout occurs.
            AshbyAPIError: If upstream returns HTTP 4xx or 5xx.
            AshbyResponseError: If response is malformed or unexpected format.
        """
        active_board = self._resolve_job_board(job_board=job_board, raise_if_missing=True)
        endpoint = f"{self._base_url}/{active_board}"
        headers = {
            "Accept": "application/json",
            "User-Agent": "SkillForge-AI-MarketClient/0.1.0",
        }

        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            logger.debug("Dispatching Ashby postings request to job board '%s'", active_board)
            res = client.get(endpoint, headers=headers)
        except httpx.TimeoutException as exc:
            logger.warning("Ashby request for job board '%s' timed out after %ss", active_board, self._timeout)
            raise AshbyConnectionError(
                f"Ashby API request for job board '{active_board}' timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("Ashby network request failed for job board '%s': %s", active_board, exc)
            raise AshbyConnectionError(
                f"Ashby API network connection failed for job board '{active_board}': {exc}"
            ) from exc
        finally:
            if self._owns_client and self._client is None:
                client.close()

        # Handle HTTP status codes
        if res.status_code >= 400:
            if res.status_code == 404:
                detail = f"Ashby public job board '{active_board}' not found (HTTP 404)."
            elif res.status_code == 429:
                detail = f"Ashby API rate limit exceeded for job board '{active_board}' (HTTP 429)."
            elif 400 <= res.status_code < 500:
                detail = f"Ashby API client error: HTTP {res.status_code} for job board '{active_board}'."
            else:
                detail = (
                    f"Ashby API server error: HTTP {res.status_code} for job board '{active_board}'. "
                    "The upstream service may be temporarily unavailable."
                )

            logger.error("Ashby API returned error: %s", detail)
            raise AshbyAPIError(
                message=detail,
                status_code=res.status_code,
                response_body=res.text[:500],
            )

        # Parse JSON response
        try:
            data = res.json()
        except Exception as exc:
            logger.error("Ashby returned unparseable JSON for job board '%s': %s", active_board, exc)
            raise AshbyResponseError(
                f"Failed to parse Ashby response as JSON for job board '{active_board}'.",
                response_body=res.text[:500],
            ) from exc

        if not isinstance(data, dict):
            logger.error("Ashby response for job board '%s' is not a JSON object: %s", active_board, type(data))
            raise AshbyResponseError(
                f"Ashby response for job board '{active_board}' is not a JSON object.",
                response_body=res.text[:500],
            )

        jobs_list = data.get("jobs")
        if jobs_list is None or not isinstance(jobs_list, list):
            logger.error("Ashby response for job board '%s' missing 'jobs' list: %s", active_board, type(jobs_list))
            raise AshbyResponseError(
                f"Ashby response for job board '{active_board}' does not contain a 'jobs' list.",
                response_body=res.text[:500],
            )

        raw_postings: List[Dict[str, Any]] = jobs_list
        normalized_jobs: List[NormalizedMarketJob] = []

        for raw_job in raw_postings:
            job = self.normalize_job(raw_job)
            if job is not None and _matches_query_terms(job, queries):
                normalized_jobs.append(job)

        # Deterministic ordering by (title.lower(), external_job_id)
        normalized_jobs.sort(key=lambda j: (j.title.lower(), j.external_job_id))

        # Enforce bounded result limits if specified
        if max_results is not None and max_results > 0:
            normalized_jobs = normalized_jobs[:max_results]

        logger.debug(
            "Normalized %d valid jobs from Ashby job board '%s' (raw=%d)",
            len(normalized_jobs),
            active_board,
            len(raw_postings),
        )
        return normalized_jobs

    def normalize_job(self, raw_job: Any) -> Optional[NormalizedMarketJob]:
        """
        Deterministically cleans and normalizes a raw Ashby posting into
        a canonical NormalizedMarketJob.

        Validation rules:
        - Must contain a valid, non-empty external_job_id (derived from 'id').
        - Must contain a valid, non-empty job title (derived from 'title').
        - Preserves source="ashby".
        - Cleans description (preferred 'descriptionPlain', fallback 'descriptionHtml').
        - Extracts geographical location strictly (workplaceType NEVER used as location).
        - Extracts optional company_name, category (department/team), contract_type, redirect_url, created_at.
        - Never fabricates missing values.
        - Preserves complete raw_data payload for provenance and auditability.

        Returns:
            NormalizedMarketJob if data quality rules are met, or None if rejected.
        """
        if isinstance(raw_job, NormalizedMarketJob):
            return raw_job

        if not isinstance(raw_job, dict):
            logger.debug("AshbyAdapter rejected non-dict raw_job: %s", type(raw_job))
            return None

        # 1. Validate and clean external_job_id (must be present, non-empty)
        raw_id = raw_job.get("id")
        if raw_id is None:
            logger.debug("AshbyAdapter rejected job posting: missing 'id'")
            return None
        external_job_id = collapse_whitespace(str(raw_id))
        if not external_job_id:
            logger.debug("AshbyAdapter rejected job posting: empty 'id'")
            return None

        # 2. Validate and clean title (must be present, non-empty)
        title_raw = raw_job.get("title")
        title = collapse_whitespace(str(title_raw) if title_raw is not None else None)
        if not title:
            logger.debug("AshbyAdapter rejected job id=%s: missing or empty title", external_job_id)
            return None

        # 3. Clean description (preferred descriptionPlain, fallback to HTML cleaning)
        description = clean_ashby_description(raw_job)

        # 4. Extract company name if supplied in payload
        company_raw = raw_job.get("company_name") or raw_job.get("company")
        company_name = collapse_whitespace(str(company_raw) if company_raw is not None else None)

        # 5. Extract location strictly adhering to geographical fallback rules
        location = _extract_ashby_location(raw_job)

        # 6. Extract category / department / team
        category_raw = raw_job.get("department") or raw_job.get("team")
        category = collapse_whitespace(str(category_raw) if category_raw is not None else None)

        # 7. Extract contract type from employmentType (e.g. 'FullTime', 'Contract', 'PartTime')
        commitment_raw = raw_job.get("employmentType")
        contract_type = collapse_whitespace(str(commitment_raw) if commitment_raw is not None else None)
        contract_time = None

        # 8. Extract redirect URL (jobUrl fallback to applyUrl)
        redirect_raw = raw_job.get("jobUrl") or raw_job.get("applyUrl")
        redirect_url = collapse_whitespace(str(redirect_raw) if redirect_raw is not None else None)

        # 9. Extract creation / publication timestamp (publishedAt fallback to createdAt)
        created_at = _parse_ashby_timestamp(raw_job.get("publishedAt") or raw_job.get("createdAt"))

        return NormalizedMarketJob(
            source="ashby",
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
