"""
Deterministic cleaning and validation rules for market job postings.
Post-MVP Phase 1, Checkpoint P1-B.

Enforces:
- Deterministic whitespace trimming and collapsing.
- Normalization of empty/blank strings to None.
- Structural validation (rejection of jobs missing ID or title).
- Preservation of raw description semantics without LLM rewriting or skill inference.
"""

import logging
import re
from typing import Any, Dict, Optional

from app.services.market.clients.adzuna_client import AdzunaJobItem
from app.services.market.models import NormalizedMarketJob

logger = logging.getLogger(__name__)

# Precompiled regex for efficient inline whitespace collapsing
_RE_MULTIPLE_SPACES = re.compile(r"[^\S\r\n]+")
_RE_EXCESSIVE_NEWLINES = re.compile(r"\n{3,}")


def collapse_whitespace(text: Optional[str]) -> Optional[str]:
    """
    Trims leading/trailing whitespace and collapses repeated inline whitespace into a single space.
    Converts empty or whitespace-only strings to None.
    """
    if text is None:
        return None
    # Strip leading and trailing whitespace
    stripped = text.strip()
    if not stripped:
        return None
    # Collapse any sequence of whitespace characters to a single space
    collapsed = _RE_MULTIPLE_SPACES.sub(" ", stripped)
    return collapsed if collapsed else None


def clean_multiline_text(text: Optional[str]) -> Optional[str]:
    """
    Cleans multiline text (e.g., job descriptions) while preserving paragraph boundaries.
    - Normalizes carriage returns (\\r\\n and \\r) to \\n.
    - Collapses consecutive spaces/tabs on each line.
    - Collapses 3 or more consecutive newlines down to 2 (paragraph break).
    - Strips overall leading/trailing whitespace.
    - Converts empty or whitespace-only results to None.
    """
    if text is None:
        return None
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple inline spaces within lines
    normalized = _RE_MULTIPLE_SPACES.sub(" ", normalized)
    # Collapse excessive vertical spacing
    normalized = _RE_EXCESSIVE_NEWLINES.sub("\n\n", normalized)
    stripped = normalized.strip()
    return stripped if stripped else None


def clean_adzuna_job(raw_job: AdzunaJobItem) -> Optional[NormalizedMarketJob]:
    """
    Deterministically cleans, normalizes, and validates a raw AdzunaJobItem.

    Returns:
        NormalizedMarketJob if the record meets data quality rules.
        None if the record is rejected (missing external_job_id or missing title).
    """
    try:
        # Validate and clean external_job_id
        raw_id_str = str(raw_job.id) if raw_job.id is not None else ""
        job_id = collapse_whitespace(raw_id_str)
        if not job_id:
            logger.debug("Rejected job posting: missing or empty external_job_id")
            return None

        # Validate and clean title
        title = collapse_whitespace(raw_job.title)
        if not title:
            logger.debug("Rejected job posting id=%s: missing or empty title", job_id)
            return None

        # Clean description without destroying paragraph structure
        description = clean_multiline_text(raw_job.description)

        # Clean company name
        company_raw = raw_job.company_name
        if not company_raw and isinstance(raw_job.raw_data, dict):
            company_obj = raw_job.raw_data.get("company")
            if isinstance(company_obj, dict):
                company_raw = company_obj.get("display_name")
        company_name = collapse_whitespace(company_raw)

        # Clean location
        location_raw = raw_job.location_name
        if not location_raw and isinstance(raw_job.raw_data, dict):
            loc_obj = raw_job.raw_data.get("location")
            if isinstance(loc_obj, dict):
                location_raw = loc_obj.get("display_name")
        location = collapse_whitespace(location_raw)

        # Clean category
        category_raw = raw_job.category_label
        if not category_raw and isinstance(raw_job.raw_data, dict):
            cat_obj = raw_job.raw_data.get("category")
            if isinstance(cat_obj, dict):
                category_raw = cat_obj.get("label") or cat_obj.get("tag")
        category = collapse_whitespace(category_raw)

        # Clean contract attributes
        contract_type_raw = None
        contract_time_raw = None
        if isinstance(raw_job.raw_data, dict):
            contract_type_raw = raw_job.raw_data.get("contract_type")
            contract_time_raw = raw_job.raw_data.get("contract_time")

        contract_type = collapse_whitespace(contract_type_raw)
        contract_time = collapse_whitespace(contract_time_raw)

        # Clean timestamps and redirect URL
        created_raw = raw_job.created
        if not created_raw and isinstance(raw_job.raw_data, dict):
            created_raw = raw_job.raw_data.get("created")
        created_at = collapse_whitespace(created_raw)

        redirect_raw = raw_job.redirect_url
        if not redirect_raw and isinstance(raw_job.raw_data, dict):
            redirect_raw = raw_job.raw_data.get("redirect_url")
        redirect_url = collapse_whitespace(redirect_raw)

        raw_payload: Dict[str, Any] = (
            raw_job.raw_data if isinstance(raw_job.raw_data, dict) else {}
        )

        return NormalizedMarketJob(
            source="adzuna",
            external_job_id=job_id,
            title=title,
            description=description,
            company_name=company_name,
            location=location,
            category=category,
            contract_type=contract_type,
            contract_time=contract_time,
            created_at=created_at,
            redirect_url=redirect_url,
            raw_data=raw_payload,
        )
    except Exception as exc:
        logger.warning("Unexpected error normalizing job item: %s", exc)
        return None
