"""
Multi-source market refresh orchestration data contracts for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-L (Architecture & Contract Foundation).

Defines:
- MarketRefreshStatus: Top-level orchestration execution state.
- MarketSourceStatus: Per-source execution state (SUCCESS, FAILED, SKIPPED).
- MultiSourceRefreshGateDecision: Centralized 24-hour refresh evaluation outcome.
- MarketSourceRefreshResult: Per-source audit metrics and sanitized error info.
- MultiSourceRefreshConfig: Deterministic configuration for the orchestrator.
- MultiSourceRefreshResult: Consolidated multi-source orchestration result.
- Security-hardened serialization guaranteeing zero secret / credential exposure.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from app.services.market.adapters.base import (
    MarketSourceType,
    UnknownMarketSourceError,
)

# ---------------------------------------------------------------------------
# Security Sanitization
# ---------------------------------------------------------------------------

def sanitize_error_message(message: Optional[str]) -> Optional[str]:
    """
    Sanitizes error messages to guarantee no API keys, tokens, authorization
    headers, passwords, or raw secrets can leak into logs, models, or result dicts.
    """
    if not message:
        return message
    sanitized = str(message)
    # URL / DSN user:password credentials (e.g. postgresql://user:pass@host or https://user:pass@host)
    sanitized = re.sub(r"(?i)([a-zA-Z0-9+.-]+://[^:\s]+:)[^@\s]+(@)", r"\1[REDACTED]\2", sanitized)
    # Authorization header (including Basic, Bearer, Token schemes)
    sanitized = re.sub(r"(?i)\bauthorization\s*[:=]\s*(?:(?:basic|bearer|token)\s+)?['\"]?[^\s,'\"]+['\"]?", "Authorization: [REDACTED]", sanitized)
    # Standalone Bearer tokens
    sanitized = re.sub(r"(?i)\bbearer\s+['\"]?[a-zA-Z0-9_\-\.\~/+=]+['\"]?", "Bearer [REDACTED]", sanitized)
    # Key-value secrets (api_key=..., app_id=..., app_key=..., secret=..., token=..., password=..., etc.)
    sanitized = re.sub(
        r"(?i)\b(api[-_]?key|app[-_]?key|app[-_]?id|client[-_]?secret|secret[-_]?key|secret|token|password|passwd|auth)\s*[:=]\s*(?!(?:api[-_]?key|app[-_]?key|app[-_]?id|token|password|secret)\s*[:=])(?:['\"][^'\"]+['\"]|[^\s,'\"&]+)",
        r"\1=[REDACTED]",
        sanitized,
    )
    return sanitized


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MarketRefreshStatus(str, Enum):
    """
    Overall execution status for a multi-source market refresh run.
    """
    COMPLETED = "completed"
    PARTIALLY_COMPLETED = "partially_completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class MarketSourceStatus(str, Enum):
    """
    Execution status for an individual market source provider.
    - SUCCESS: Source fetched, cleaned, and normalized jobs successfully.
    - FAILED: Source encountered an error (network, API, response, config).
    - SKIPPED: Source was intentionally not executed (e.g., 24h gate skipped, source disabled).
    """
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Centralized 24-Hour Gate Decision
# ---------------------------------------------------------------------------

@dataclass
class MultiSourceRefreshGateDecision:
    """
    Structured outcome of the centralized 24-hour market refresh gate evaluation.

    Guarantees:
    - ONE centralized refresh gate evaluation at the orchestrator boundary.
    - No per-source timers or independent schedulers.
    """
    should_refresh: bool
    reason: str
    last_snapshot_at: Optional[datetime] = None
    elapsed_hours: Optional[float] = None
    interval_hours: float = 24.0
    checked_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.interval_hours <= 0:
            raise ValueError(f"interval_hours must be positive, got: {self.interval_hours}")
        if self.checked_at is None:
            self.checked_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes gate decision to dictionary."""
        return {
            "should_refresh": self.should_refresh,
            "reason": self.reason,
            "last_snapshot_at": self.last_snapshot_at.isoformat() if self.last_snapshot_at else None,
            "elapsed_hours": round(self.elapsed_hours, 4) if self.elapsed_hours is not None else None,
            "interval_hours": self.interval_hours,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }


# ---------------------------------------------------------------------------
# Per-Source Refresh Result
# ---------------------------------------------------------------------------

@dataclass
class MarketSourceRefreshResult:
    """
    Audit metrics and execution outcome for a single market source.

    Guarantees:
    - Strictly typed status (SUCCESS, FAILED, SKIPPED).
    - Never confuses source failure with an empty successful dataset.
    - Sanitized error category and message free of credentials.
    """
    source: Union[MarketSourceType, str]
    status: MarketSourceStatus
    jobs_fetched: int = 0
    jobs_normalized: int = 0
    jobs_persisted: int = 0
    error_category: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None

    def __post_init__(self) -> None:
        # Normalize source to MarketSourceType if string
        if isinstance(self.source, str):
            self.source = MarketSourceType.from_str(self.source)
        elif not isinstance(self.source, MarketSourceType):
            raise TypeError(f"source must be MarketSourceType or str, got {type(self.source)}")

        # Normalize status to MarketSourceStatus if string
        if isinstance(self.status, str):
            self.status = MarketSourceStatus(self.status.lower())
        elif not isinstance(self.status, MarketSourceStatus):
            raise TypeError(f"status must be MarketSourceStatus, got {type(self.status)}")

        # Enforce non-negative integer counts
        if self.jobs_fetched < 0 or self.jobs_normalized < 0 or self.jobs_persisted < 0:
            raise ValueError("Job counts (fetched, normalized, persisted) must be non-negative integers.")

        # Sanitize error message against credential leakage
        if self.error_message:
            self.error_message = sanitize_error_message(self.error_message)

    @property
    def source_type(self) -> MarketSourceType:
        return self.source if isinstance(self.source, MarketSourceType) else MarketSourceType.from_str(self.source)

    @property
    def source_name(self) -> str:
        return self.source_type.value

    def to_dict(self) -> Dict[str, Any]:
        """Serializes source result to dictionary without credential leakage."""
        return {
            "source": self.source_name,
            "status": self.status.value,
            "jobs_fetched": self.jobs_fetched,
            "jobs_normalized": self.jobs_normalized,
            "jobs_persisted": self.jobs_persisted,
            "error_category": self.error_category,
            "error_message": self.error_message,
            "duration_seconds": round(self.duration_seconds, 4) if self.duration_seconds is not None else None,
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Summary dictionary representation."""
        return self.to_dict()


# ---------------------------------------------------------------------------
# Multi-Source Refresh Configuration
# ---------------------------------------------------------------------------

DEFAULT_ORCHESTRATOR_SOURCES: Tuple[MarketSourceType, ...] = (
    MarketSourceType.ADZUNA,
    MarketSourceType.GREENHOUSE,
    MarketSourceType.LEVER,
    MarketSourceType.ASHBY,
)


@dataclass
class MultiSourceRefreshConfig:
    """
    Deterministic configuration parameters for multi-source market refresh orchestration.
    """
    enabled_sources: Tuple[MarketSourceType, ...] = DEFAULT_ORCHESTRATOR_SOURCES
    refresh_interval_hours: float = 24.0
    force: bool = False
    queries: Optional[List[str]] = None
    source_fetch_limits: Optional[Dict[str, int]] = None
    commit: bool = True

    def __post_init__(self) -> None:
        if self.refresh_interval_hours <= 0:
            raise ValueError(
                f"refresh_interval_hours must be strictly positive, got: {self.refresh_interval_hours}"
            )

        # Normalize and validate enabled_sources
        normalized_sources: List[MarketSourceType] = []
        if not self.enabled_sources:
            raise ValueError("enabled_sources cannot be empty.")

        for s in self.enabled_sources:
            if isinstance(s, MarketSourceType):
                normalized_sources.append(s)
            elif isinstance(s, str):
                normalized_sources.append(MarketSourceType.from_str(s))
            else:
                raise TypeError(f"Invalid source in enabled_sources: {s!r}")

        # Deterministic preservation (remove duplicates preserving order)
        seen = set()
        deduped: List[MarketSourceType] = []
        for s in normalized_sources:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        self.enabled_sources = tuple(deduped)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled_sources": [s.value for s in self.enabled_sources],
            "refresh_interval_hours": self.refresh_interval_hours,
            "force": self.force,
            "queries": list(self.queries) if self.queries else None,
            "source_fetch_limits": dict(self.source_fetch_limits) if self.source_fetch_limits else None,
            "commit": self.commit,
        }


# ---------------------------------------------------------------------------
# Consolidated Orchestration Result
# ---------------------------------------------------------------------------

@dataclass
class MultiSourceRefreshResult:
    """
    Consolidated operational and audit summary for a multi-source market refresh run.

    Guarantees:
    - Complete visibility into centralized gate decision.
    - Deterministic per-source results for all configured providers.
    - Explicit tracking of last-known-good preservation state.
    - Strictly free of secrets, credentials, API keys, tokens, or auth headers.
    """
    status: MarketRefreshStatus
    gate_decision: MultiSourceRefreshGateDecision
    source_results: Dict[str, MarketSourceRefreshResult] = field(default_factory=dict)
    total_jobs_fetched: int = 0
    total_jobs_normalized: int = 0
    total_jobs_persisted: int = 0
    total_sources_succeeded: int = 0
    total_sources_failed: int = 0
    total_sources_skipped: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    snapshot_at: Optional[datetime] = None
    last_snapshot_at: Optional[datetime] = None
    last_known_good_preserved: bool = True
    downstream_demand_refreshed: bool = False
    downstream_metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.status, str):
            self.status = MarketRefreshStatus(self.status.lower())
        elif not isinstance(self.status, MarketRefreshStatus):
            raise TypeError(f"status must be MarketRefreshStatus, got {type(self.status)}")

        if self.error:
            self.error = sanitize_error_message(self.error)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes orchestration result to dictionary without credential leakage."""
        return {
            "status": self.status.value,
            "gate_decision": self.gate_decision.to_dict() if self.gate_decision else None,
            "source_results": {
                k: v.to_dict() for k, v in self.source_results.items()
            },
            "metrics": {
                "total_jobs_fetched": self.total_jobs_fetched,
                "total_jobs_normalized": self.total_jobs_normalized,
                "total_jobs_persisted": self.total_jobs_persisted,
                "total_sources_succeeded": self.total_sources_succeeded,
                "total_sources_failed": self.total_sources_failed,
                "total_sources_skipped": self.total_sources_skipped,
            },
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "snapshot_at": self.snapshot_at.isoformat() if self.snapshot_at else None,
            "last_snapshot_at": self.last_snapshot_at.isoformat() if self.last_snapshot_at else None,
            "last_known_good_preserved": self.last_known_good_preserved,
            "downstream_demand_refreshed": self.downstream_demand_refreshed,
            "downstream_metrics": self.downstream_metrics,
            "error": self.error,
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Summary audit dictionary safe for logging and API transport."""
        return self.to_dict()
