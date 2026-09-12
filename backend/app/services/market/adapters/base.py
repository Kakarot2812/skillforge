"""
Common market source adapter foundation for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-G.

Defines:
- Strongly typed MarketSourceType enumeration (ADZUNA, GREENHOUSE, LEVER, ASHBY).
- Typed market source domain exceptions.
- Abstract base class MarketSourceAdapter representing the common source ingestion contract.
"""

from abc import ABC, abstractmethod
from enum import Enum
import logging
from typing import Any, List, Optional, Union

from app.services.market.models import NormalizedMarketJob

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Source Types
# ---------------------------------------------------------------------------

class MarketSourceType(str, Enum):
    """
    Strongly typed market source identifiers for SkillForge AI.
    P1-G Multi-Source Market Ingestion Foundation.
    """

    ADZUNA = "adzuna"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"

    @classmethod
    def from_str(cls, value: Union[str, "MarketSourceType"]) -> "MarketSourceType":
        """
        Deterministically resolves a string or enum instance to MarketSourceType.
        Case-insensitive, supports member name (e.g. 'ADZUNA') and value (e.g. 'adzuna').

        Raises:
            UnknownMarketSourceError: If the value cannot be mapped to a known source.
        """
        if isinstance(value, cls):
            return value

        if not isinstance(value, str) or not value.strip():
            raise UnknownMarketSourceError(
                f"Invalid market source identifier: {value!r}. Value must be a non-empty string or MarketSourceType."
            )

        normalized = value.strip().lower()
        for member in cls:
            if member.value == normalized or member.name.lower() == normalized:
                return member

        valid_sources = [m.name for m in cls]
        raise UnknownMarketSourceError(
            f"Unknown market source '{value}'. Supported source identifiers are: {valid_sources}"
        )


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MarketSourceError(Exception):
    """Base exception for all market source adapter errors."""
    pass


class UnknownMarketSourceError(MarketSourceError, ValueError):
    """Raised when an unknown or unmapped market source identifier is requested."""
    pass


class UnsupportedMarketSourceError(MarketSourceError, NotImplementedError):
    """Raised when a valid MarketSourceType has no operational adapter implementation yet."""
    pass


class MarketSourceConfigurationError(MarketSourceError):
    """Raised when required credentials or settings for a source adapter are missing or invalid."""
    pass


# ---------------------------------------------------------------------------
# Market Source Adapter Interface
# ---------------------------------------------------------------------------

class MarketSourceAdapter(ABC):
    """
    Abstract contract for external market data provider adapters.

    Every source adapter conforms to this common interface:
    upstream provider data -> adapter -> canonical NormalizedMarketJob objects.

    Guarantees:
    - Downstream pipeline consumes identical NormalizedMarketJob records.
    - Preserves source identity, upstream external ID, and raw payload provenance.
    - Encapsulates provider-specific client, cleaning, and normalization rules.
    """

    @property
    @abstractmethod
    def source_type(self) -> MarketSourceType:
        """Returns the strongly-typed MarketSourceType for this adapter."""
        ...

    @property
    def source_name(self) -> str:
        """Returns the canonical lowercase string identifier (e.g. 'adzuna')."""
        return self.source_type.value

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the required credentials/configuration for this provider are present."""
        ...

    @abstractmethod
    def fetch_and_normalize_jobs(
        self,
        queries: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[NormalizedMarketJob]:
        """
        Fetches postings from the upstream provider, cleans and validates them,
        and returns a collection of canonical NormalizedMarketJob instances.

        Returns:
            List[NormalizedMarketJob]: Deduplicated, validated normalized market jobs.
        """
        ...

    @abstractmethod
    def normalize_job(self, raw_job: Any) -> Optional[NormalizedMarketJob]:
        """
        Deterministically cleans and normalizes a single raw provider record into
        a canonical NormalizedMarketJob.

        Returns:
            NormalizedMarketJob if the record satisfies data quality rules, or
            None if the record is rejected (e.g. missing external ID or title).
        """
        ...
