"""
Lever public Postings API source adapter for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-I.

Adapts the official Lever public Postings API:
    https://api.lever.co/v0/postings/{site}?mode=json
conforming to the MarketSourceAdapter abstraction established in P1-G.

Architectural guarantees:
- source_type = MarketSourceType.LEVER
- source = "lever"
- Conforms strictly to the existing NormalizedMarketJob contract
- Public job-posting data only; zero private recruiting credentials or API keys
- Preserves raw upstream data for provenance and auditability
- Deterministic text cleaning (HTML tag stripping, entity unescaping, list assembly)
- Bounded, deterministic fetching and filtering
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

class LeverError(MarketSourceError):
    """Base domain exception for all Lever adapter errors."""
    pass


class LeverConnectionError(LeverError):
    """Raised on network failures, connection drops, or timeouts when contacting Lever."""
    pass


class LeverAPIError(LeverError):
    """Raised when the Lever API returns an HTTP 4xx or 5xx status code."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class LeverResponseError(LeverError):
    """Raised when Lever returns an unparseable, malformed, or unexpected response format."""

    def __init__(self, message: str, response_body: Optional[str] = None):
        super().__init__(message)
        self.response_body = response_body


# ---------------------------------------------------------------------------
# HTML Description Assembly & Cleaning Utility
# ---------------------------------------------------------------------------

_RE_BLOCK_TAGS = re.compile(
    r"<(?:/p|/div|/h[1-6]|/li|/tr|/blockquote|br\s*/?|hr\s*/?)>",
    flags=re.IGNORECASE,
)
_RE_ALL_TAGS = re.compile(r"<[^>]+>")


def clean_lever_description(raw_job: Dict[str, Any]) -> Optional[str]:
    """
    Deterministically cleans and assembles job description text from a Lever posting.

    Lever structures postings across multiple fields:
    - description (or descriptionPlain): opening overview and role description.
    - lists: structured sections (e.g. Requirements, What You'll Do) containing
      text headers and HTML list items.
    - additional (or additionalPlain): closing notes and company summary.

    This function:
    1. Combines role overview, structured list sections, and closing notes.
    2. Decodes single and double-encoded HTML entities.
    3. Converts block tags into newlines to preserve paragraph and list boundaries.
    4. Strips remaining HTML tags.
    5. Applies clean_multiline_text for deterministic whitespace normalization.
    """
    if not isinstance(raw_job, dict):
        return None

    parts: List[str] = []

    # 1. Main description / opening
    desc = raw_job.get("description") or raw_job.get("descriptionPlain")
    if desc and isinstance(desc, str) and desc.strip():
        parts.append(desc.strip())

    # 2. Structured lists (requirements, qualifications, benefits, etc.)
    lists = raw_job.get("lists")
    if isinstance(lists, list):
        for item in lists:
            if isinstance(item, dict):
                header = item.get("text")
                content = item.get("content")
                list_str = ""
                if header and isinstance(header, str) and header.strip():
                    list_str += f"<div><h3>{header.strip()}</h3>"
                if content and isinstance(content, str) and content.strip():
                    list_str += f"{content.strip()}</div>"
                elif list_str:
                    list_str += "</div>"
                if list_str:
                    parts.append(list_str)

    # 3. Additional closing content
    additional = raw_job.get("additional") or raw_job.get("additionalPlain")
    if additional and isinstance(additional, str) and additional.strip():
        parts.append(additional.strip())

    if not parts:
        return None

    combined = "\n\n".join(parts)

    # Unescape HTML entities (handling potential double-escaping)
    unescaped = combined
    for _ in range(2):
        if "&lt;" in unescaped or "&amp;" in unescaped or "&gt;" in unescaped or "&quot;" in unescaped or "&#" in unescaped:
            unescaped = html.unescape(unescaped)

    # Convert block tags into newlines before stripping tags
    with_breaks = _RE_BLOCK_TAGS.sub("\n", unescaped)

    # Strip remaining HTML tags
    tagless = _RE_ALL_TAGS.sub("", with_breaks)

    # Clean multiline whitespace deterministically preserving paragraphs
    return clean_multiline_text(tagless)


def _parse_lever_created_at(raw_created: Any) -> Optional[str]:
    """
    Parses a Lever createdAt timestamp (typically epoch milliseconds integer)
    into an ISO 8601 UTC timestamp string.
    """
    if raw_created is None:
        return None

    if isinstance(raw_created, (int, float)):
        try:
            dt = datetime.fromtimestamp(raw_created / 1000.0, tz=timezone.utc)
            return dt.isoformat()
        except Exception:
            return None

    if isinstance(raw_created, str):
        cleaned = collapse_whitespace(raw_created)
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
# Lever Adapter Implementation
# ---------------------------------------------------------------------------

class LeverAdapter(MarketSourceAdapter):
    """
    MarketSourceAdapter implementation for the Lever public Postings API.

    Fetches public postings from:
        GET https://api.lever.co/v0/postings/{site}?mode=json

    Guarantees:
    - Returns canonical NormalizedMarketJob objects (source='lever').
    - Requires only the public site slug/identifier (e.g. 'leverdemo', 'palantir').
    - Zero private credentials or recruiter API authentication.
    - Preserves external_job_id and raw_data provenance.
    - Deterministic text normalization, query filtering, and bounded result slicing.
    - No silent fallback to Adzuna or Greenhouse.
    """

    DEFAULT_BASE_URL: str = "https://api.lever.co/v0/postings"
    DEFAULT_TIMEOUT_SECONDS: float = 15.0

    def __init__(
        self,
        site: Optional[str] = None,
        client: Optional[httpx.Client] = None,
        base_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self._site = site.strip() if site and site.strip() else None
        self._timeout = timeout
        raw_base = base_url or getattr(settings, "LEVER_API_BASE_URL", self.DEFAULT_BASE_URL)
        self._base_url = raw_base.rstrip("/") if raw_base else self.DEFAULT_BASE_URL
        self._client = client
        self._owns_client = client is None

    @property
    def source_type(self) -> MarketSourceType:
        """Returns MarketSourceType.LEVER."""
        return MarketSourceType.LEVER

    @property
    def source_name(self) -> str:
        """Returns canonical string identifier 'lever'."""
        return MarketSourceType.LEVER.value

    @property
    def is_configured(self) -> bool:
        """
        Returns True if a public Lever site identifier is configured either
        on this adapter instance or via settings.LEVER_SITE.
        """
        site = self._resolve_site(raise_if_missing=False)
        return bool(site and site.strip())

    def _resolve_site(
        self,
        site: Optional[str] = None,
        raise_if_missing: bool = True,
    ) -> Optional[str]:
        """
        Resolves the active public site identifier from argument, instance, or settings.
        Raises MarketSourceConfigurationError if required but unavailable.
        """
        effective_site = site or self._site or getattr(settings, "LEVER_SITE", None)
        if effective_site and effective_site.strip():
            return effective_site.strip()

        if raise_if_missing:
            raise MarketSourceConfigurationError(
                "Lever site identifier is missing. A valid public site slug must be provided "
                "via argument, adapter constructor, or settings.LEVER_SITE."
            )
        return None

    def fetch_and_normalize_jobs(
        self,
        queries: Optional[List[str]] = None,
        site: Optional[str] = None,
        max_results: Optional[int] = None,
        **kwargs: Any,
    ) -> List[NormalizedMarketJob]:
        """
        Fetches public job postings from the Lever Postings API, deterministically
        normalizes each posting into a NormalizedMarketJob, applies deterministic query
        filtering and bounded result limits.

        Args:
            queries: Optional list of keyword query filters (e.g. ['Backend', 'Python']).
            site: Optional site slug override (e.g. 'leverdemo').
            max_results: Optional maximum number of normalized postings to return.

        Returns:
            List[NormalizedMarketJob]: Cleaned, validated, and deterministically ordered jobs.

        Raises:
            MarketSourceConfigurationError: If site is missing.
            LeverConnectionError: If network failure or timeout occurs.
            LeverAPIError: If upstream returns HTTP 4xx or 5xx.
            LeverResponseError: If response is malformed or unexpected format.
        """
        active_site = self._resolve_site(site=site, raise_if_missing=True)
        endpoint = f"{self._base_url}/{active_site}"
        params: Dict[str, Any] = {"mode": "json"}
        headers = {
            "Accept": "application/json",
            "User-Agent": "SkillForge-AI-MarketClient/0.1.0",
        }

        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            logger.debug("Dispatching Lever postings request to site '%s'", active_site)
            res = client.get(endpoint, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            logger.warning("Lever request for site '%s' timed out after %ss", active_site, self._timeout)
            raise LeverConnectionError(
                f"Lever API request for site '{active_site}' timed out after {self._timeout}s."
            ) from exc
        except httpx.RequestError as exc:
            logger.warning("Lever network request failed for site '%s': %s", active_site, exc)
            raise LeverConnectionError(
                f"Lever API network connection failed for site '{active_site}': {exc}"
            ) from exc
        finally:
            if self._owns_client and self._client is None:
                client.close()

        # Handle HTTP status codes
        if res.status_code >= 400:
            if res.status_code == 404:
                detail = f"Lever public job site '{active_site}' not found (HTTP 404)."
            elif res.status_code == 429:
                detail = f"Lever API rate limit exceeded for site '{active_site}' (HTTP 429)."
            elif 400 <= res.status_code < 500:
                detail = f"Lever API client error: HTTP {res.status_code} for site '{active_site}'."
            else:
                detail = (
                    f"Lever API server error: HTTP {res.status_code} for site '{active_site}'. "
                    "The upstream service may be temporarily unavailable."
                )

            logger.error("Lever API returned error: %s", detail)
            raise LeverAPIError(
                message=detail,
                status_code=res.status_code,
                response_body=res.text[:500],
            )

        # Parse JSON response
        try:
            data = res.json()
        except Exception as exc:
            logger.error("Lever returned unparseable JSON for site '%s': %s", active_site, exc)
            raise LeverResponseError(
                f"Failed to parse Lever response as JSON for site '{active_site}'.",
                response_body=res.text[:500],
            ) from exc

        # Lever returns an array of posting objects in JSON mode
        # E.g. [ {"id": "...", "text": "...", ...}, ... ]
        # In error states, it may return a dict like {"ok": false, "error": "..."}
        if isinstance(data, dict) and data.get("ok") is False:
            err_msg = data.get("error", "Unknown Lever error")
            raise LeverAPIError(
                message=f"Lever API returned error: {err_msg}",
                status_code=res.status_code,
                response_body=res.text[:500],
            )

        if not isinstance(data, list):
            logger.error("Unexpected Lever response shape for site '%s': expected list, got %s", active_site, type(data))
            raise LeverResponseError(
                f"Lever response for site '{active_site}' is not a list of postings.",
                response_body=res.text[:500],
            )

        raw_postings: List[Dict[str, Any]] = data
        normalized_jobs: List[NormalizedMarketJob] = []

        for raw_job in raw_postings:
            job = self.normalize_job(raw_job)
            if job is not None and _matches_query_terms(job, queries):
                normalized_jobs.append(job)

        # Deterministic ordering by (title, external_job_id) to ensure consistent output
        normalized_jobs.sort(key=lambda j: (j.title.lower(), j.external_job_id))

        # Enforce bounded result limits if specified
        if max_results is not None and max_results > 0:
            normalized_jobs = normalized_jobs[:max_results]

        logger.debug(
            "Normalized %d valid jobs from Lever site '%s' (raw=%d)",
            len(normalized_jobs),
            active_site,
            len(raw_postings),
        )
        return normalized_jobs

    def normalize_job(self, raw_job: Any) -> Optional[NormalizedMarketJob]:
        """
        Deterministically cleans and normalizes a raw Lever posting into
        a canonical NormalizedMarketJob.

        Validation rules:
        - Must contain a valid, non-empty external_job_id (derived from 'id').
        - Must contain a valid, non-empty job title (derived from 'text' or 'title').
        - Preserves source="lever".
        - Assembles and cleans description (opening, lists with headers, closing notes).
        - Extracts optional company_name, location, category, redirect_url, created_at.
        - Never fabricates missing values.
        - Preserves complete raw_data payload for provenance and auditability.

        Returns:
            NormalizedMarketJob if data quality rules are met, or None if rejected.
        """
        if isinstance(raw_job, NormalizedMarketJob):
            return raw_job

        if not isinstance(raw_job, dict):
            logger.debug("LeverAdapter rejected non-dict raw_job: %s", type(raw_job))
            return None

        # 1. Validate and clean external_job_id
        raw_id = raw_job.get("id")
        if raw_id is None:
            logger.debug("LeverAdapter rejected job posting: missing 'id'")
            return None
        external_job_id = collapse_whitespace(str(raw_id))
        if not external_job_id:
            logger.debug("LeverAdapter rejected job posting: empty 'id'")
            return None

        # 2. Validate and clean title (in Lever, 'text' represents the posting title)
        title_raw = raw_job.get("text") or raw_job.get("title")
        title = collapse_whitespace(str(title_raw) if title_raw is not None else None)
        if not title:
            logger.debug("LeverAdapter rejected job id=%s: missing or empty title", external_job_id)
            return None

        # 3. Clean description (assembles opening, lists, closing content, strips HTML)
        description = clean_lever_description(raw_job)

        # 4. Extract company name if supplied in payload
        company_raw = raw_job.get("company_name") or raw_job.get("company")
        company_name = collapse_whitespace(str(company_raw) if company_raw is not None else None)

        # 5. Extract location from categories object or country
        categories = raw_job.get("categories") if isinstance(raw_job.get("categories"), dict) else {}
        location_raw = categories.get("location")

        if not location_raw and isinstance(categories.get("allLocations"), list) and categories["allLocations"]:
            first_loc = categories["allLocations"][0]
            if isinstance(first_loc, str) and first_loc.strip():
                location_raw = first_loc

        if not location_raw:
            country = raw_job.get("country")
            if isinstance(country, str) and country.strip():
                location_raw = country

        location = collapse_whitespace(str(location_raw) if location_raw is not None else None)

        # 6. Extract category / department / team from categories object
        category_raw = categories.get("department") or categories.get("team")
        category = collapse_whitespace(str(category_raw) if category_raw is not None else None)

        # 7. Extract contract type / commitment (e.g. 'Full-time', 'Contract', 'Intern')
        commitment_raw = categories.get("commitment")
        contract_type = collapse_whitespace(str(commitment_raw) if commitment_raw is not None else None)
        contract_time = None

        # 8. Extract redirect URL (hostedUrl or applyUrl)
        redirect_raw = raw_job.get("hostedUrl") or raw_job.get("applyUrl")
        redirect_url = collapse_whitespace(str(redirect_raw) if redirect_raw is not None else None)

        # 9. Extract creation timestamp from createdAt epoch milliseconds
        created_at = _parse_lever_created_at(raw_job.get("createdAt"))

        return NormalizedMarketJob(
            source="lever",
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
