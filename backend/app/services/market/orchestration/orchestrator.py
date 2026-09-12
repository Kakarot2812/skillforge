"""
Centralized multi-source market refresh orchestrator for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-L (Two-Phase Multi-Source Refresh Execution).

Defines:
- MultiSourceMarketRefreshOrchestrator: Connects all registered market sources
  (Adzuna, Greenhouse, Lever, Ashby) to the common market ingestion, persistence,
  skill extraction, demand aggregation, and 24-hour snapshot/growth pipeline.

Architectural Guarantees:
1. ONE Centralized 24-Hour Gate:
   - Evaluates the 24-hour refresh condition across all market sources once at the
     orchestration boundary.
   - Absolutely NO source-specific schedulers, background threads, cron jobs, Celery
     tasks, or per-source timers.
2. Two-Phase Execution Architecture:
   - Phase 1 (Multi-Source Ingestion): Sequentially attempts all configured sources in
     deterministic canonical order [ADZUNA, GREENHOUSE, LEVER, ASHBY]. Fetches, normalizes,
     and persists jobs for each source. Phase 1 completes for ALL sources before Phase 2 begins.
   - Phase 2 (Downstream Intelligence): Iterates ONLY over sources that successfully completed
     Phase 1, in the same canonical order, to execute canonical skill extraction, demand
     aggregation, snapshot creation, and growth computation.
3. Source-Scoped P1-F Semantics:
   - Snapshots, demand aggregation, and growth calculations remain strictly source-scoped.
   - No synthetic cross-source snapshot (e.g. source="all") is invented.
   - All participating source snapshots share the exact same refresh snapshot_at timestamp.
4. Source Isolation & Last-Known-Good Preservation:
   - If a source fails in Phase 1, it is marked FAILED, its previous valid data is preserved
     intact, and it is excluded from Phase 2. Healthy sources continue unimpeded.
   - Provider failures NEVER silently become empty successful datasets.
   - Downstream demand/growth is never fabricated.
5. Registry Resolution Authority:
   - Uses MarketSourceRegistry as the single authority for source adapter resolution.
   - Unknown sources are rejected with UnknownMarketSourceError.
   - No fallback adapters.
6. Zero Credential Exposure:
   - All models, audit dictionaries, and logs strictly strip API keys, tokens,
     passwords, and authorization headers.
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from sqlalchemy.orm import Session

from app.db.models import MarketSkillDemandSnapshot
from app.services.market.adapters.base import (
    MarketSourceAdapter,
    MarketSourceConfigurationError,
    MarketSourceError,
    MarketSourceType,
    UnknownMarketSourceError,
    UnsupportedMarketSourceError,
)
from app.services.market.adapters.registry import (
    MarketSourceRegistry,
    market_source_registry,
)
from app.services.market.demand.aggregator import MarketDemandAggregator
from app.services.market.demand.growth import MarketDemandGrowthService
from app.services.market.demand.refresh import (
    REFRESH_INTERVAL_HOURS,
    MarketDemandRefreshService,
)
from app.services.market.demand.snapshots import MarketDemandSnapshotService
from app.services.market.extraction import MarketSkillExtractionService
from app.services.market.orchestration.models import (
    DEFAULT_ORCHESTRATOR_SOURCES,
    MarketRefreshStatus,
    MarketSourceRefreshResult,
    MarketSourceStatus,
    MultiSourceRefreshConfig,
    MultiSourceRefreshGateDecision,
    MultiSourceRefreshResult,
    sanitize_error_message,
)
from app.services.market.repository import MarketJobRepository

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_ORDER: Tuple[MarketSourceType, ...] = DEFAULT_ORCHESTRATOR_SOURCES


class MultiSourceMarketRefreshOrchestrator:
    """
    Centralized multi-source market refresh orchestrator with two-phase execution.

    Owns:
    - Selecting configured market sources in deterministic order.
    - Resolving adapters via MarketSourceRegistry.
    - Enforcing the centralized 24-hour refresh gate.
    - Phase 1: Ingesting and idempotently persisting jobs via MarketJobRepository across all sources.
    - Phase 2: Coordinating canonical skill extraction, demand aggregation, snapshots, and growth
      across successfully ingested sources.
    - Reporting per-source results (SUCCESS, FAILED, SKIPPED) and preserving last-known-good state.
    """

    def __init__(
        self,
        registry: Optional[MarketSourceRegistry] = None,
        repository: Optional[MarketJobRepository] = None,
        extraction_service: Optional[MarketSkillExtractionService] = None,
        aggregator: Optional[MarketDemandAggregator] = None,
        snapshot_service: Optional[MarketDemandSnapshotService] = None,
        growth_service: Optional[MarketDemandGrowthService] = None,
        refresh_service: Optional[MarketDemandRefreshService] = None,
    ):
        self.registry = registry or market_source_registry
        self.repository = repository or MarketJobRepository()
        self.extraction_service = extraction_service or MarketSkillExtractionService()
        self.aggregator = aggregator or MarketDemandAggregator()
        self.snapshot_service = snapshot_service or MarketDemandSnapshotService()
        self.growth_service = growth_service or MarketDemandGrowthService(
            snapshot_service=self.snapshot_service
        )
        self.refresh_service = refresh_service or MarketDemandRefreshService()

    def get_configured_sources(
        self,
        config: Optional[MultiSourceRefreshConfig] = None,
    ) -> List[MarketSourceType]:
        """
        Deterministically resolves and validates the list of configured market sources.

        Guarantees:
        - Deterministic order (respecting canonical DEFAULT_SOURCE_ORDER or config order).
        - Validates that every configured source has a registered operational adapter.
        - Raises UnknownMarketSourceError if an unknown source is encountered.
        - Raises UnsupportedMarketSourceError if a source has no registered adapter.
        """
        cfg = config or MultiSourceRefreshConfig()
        resolved_sources: List[MarketSourceType] = []

        for source in cfg.enabled_sources:
            source_type = MarketSourceType.from_str(source)
            # Validate adapter exists in registry
            self.registry.get_adapter(source_type)
            resolved_sources.append(source_type)

        return resolved_sources

    def evaluate_24h_gate(
        self,
        db: Any,
        force: bool = False,
        interval_hours: float = float(REFRESH_INTERVAL_HOURS),
        now: Optional[datetime] = None,
    ) -> MultiSourceRefreshGateDecision:
        """
        Evaluates the single centralized 24-hour refresh gate against the latest snapshot.

        Logic:
        1. Query latest snapshot timestamp across all market demand snapshots.
        2. If force is True -> should_refresh=True (reason='force_refresh').
        3. If no prior snapshot exists -> should_refresh=True (reason='no_prior_snapshot').
        4. If elapsed >= interval_hours -> should_refresh=True (reason='elapsed_exceeds_interval').
        5. If elapsed < interval_hours -> should_refresh=False (reason='skipped_within_24h').
        """
        checked_at = now or datetime.now(timezone.utc)
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=timezone.utc)

        last_snapshot_at: Optional[datetime] = None
        if db is not None:
            try:
                row = (
                    db.query(MarketSkillDemandSnapshot.snapshot_at)
                    .order_by(MarketSkillDemandSnapshot.snapshot_at.desc())
                    .first()
                )
                if row:
                    last_snapshot_at = row[0]
            except Exception as e:
                logger.warning("Failed to query latest snapshot timestamp: %s", e)

        last_ts_aware = (
            last_snapshot_at if (last_snapshot_at is not None and last_snapshot_at.tzinfo is not None)
            else last_snapshot_at.replace(tzinfo=timezone.utc) if last_snapshot_at is not None
            else None
        )
        elapsed_hours = (
            (checked_at - last_ts_aware).total_seconds() / 3600.0
            if last_ts_aware is not None
            else None
        )

        if force:
            return MultiSourceRefreshGateDecision(
                should_refresh=True,
                reason="force_refresh",
                last_snapshot_at=last_ts_aware,
                elapsed_hours=elapsed_hours,
                interval_hours=interval_hours,
                checked_at=checked_at,
            )

        if last_ts_aware is None:
            return MultiSourceRefreshGateDecision(
                should_refresh=True,
                reason="no_prior_snapshot",
                last_snapshot_at=None,
                elapsed_hours=None,
                interval_hours=interval_hours,
                checked_at=checked_at,
            )

        if elapsed_hours < interval_hours:
            return MultiSourceRefreshGateDecision(
                should_refresh=False,
                reason="skipped_within_24h",
                last_snapshot_at=last_ts_aware,
                elapsed_hours=elapsed_hours,
                interval_hours=interval_hours,
                checked_at=checked_at,
            )

        return MultiSourceRefreshGateDecision(
            should_refresh=True,
            reason="elapsed_exceeds_interval",
            last_snapshot_at=last_ts_aware,
            elapsed_hours=elapsed_hours,
            interval_hours=interval_hours,
            checked_at=checked_at,
        )

    def orchestrate_refresh(
        self,
        db: Session,
        config: Optional[MultiSourceRefreshConfig] = None,
        force: bool = False,
    ) -> MultiSourceRefreshResult:
        """
        Executes deterministic multi-source market refresh orchestration with strict two-phase separation:

        Phase 1 — Multi-Source Ingestion:
          Iterates through all configured sources in deterministic canonical order
          [ADZUNA, GREENHOUSE, LEVER, ASHBY]. For each source:
          - Resolves adapter via registry.
          - Validates adapter configuration.
          - Fetches and normalizes postings to NormalizedMarketJob.
          - Persists normalized jobs via MarketJobRepository.persist_jobs().
          - Records source success or failure with error isolation.
          IMPORTANT: Phase 1 attempts ALL configured sources before Phase 2 begins.

        Phase 2 — Downstream Market Intelligence:
          Iterates ONLY over sources that successfully completed Phase 1, in the same
          deterministic canonical order:
          - Extracts canonical skills via MarketSkillExtractionService.process_persisted_jobs().
          - Aggregates source-scoped demand via MarketDemandAggregator.aggregate_market_demand().
          - Creates immutable historical snapshot via MarketDemandSnapshotService.create_snapshot_from_current_demand().
          - Computes source-scoped growth via MarketDemandGrowthService.compute_and_persist_growth().
          Preserves existing P1-F source-scoped semantics (no source="all", no unified snapshot).

        Transaction:
          - If >= 1 source succeeded: commits transaction, returns COMPLETED or PARTIALLY_COMPLETED.
          - If all sources failed: rolls back transaction, returns FAILED, preserves last-known-good.
        """
        cfg = config or MultiSourceRefreshConfig(force=force)
        effective_force = force or cfg.force
        started_at = datetime.now(timezone.utc)

        # 1. Centralized 24-Hour Gate Check
        gate_decision = self.evaluate_24h_gate(
            db=db,
            force=effective_force,
            interval_hours=cfg.refresh_interval_hours,
            now=started_at,
        )

        configured_sources = self.get_configured_sources(cfg)

        # 2. Skip entire refresh if centralized gate is not satisfied
        if not gate_decision.should_refresh:
            logger.info(
                "Centralized 24-hour gate: skipping multi-source refresh (reason=%s, elapsed=%s).",
                gate_decision.reason,
                f"{gate_decision.elapsed_hours:.2f}h" if gate_decision.elapsed_hours is not None else "none",
            )
            source_results = {
                s.value: MarketSourceRefreshResult(
                    source=s,
                    status=MarketSourceStatus.SKIPPED,
                    error_message="Centralized 24-hour gate skipped refresh",
                )
                for s in configured_sources
            }
            return MultiSourceRefreshResult(
                status=MarketRefreshStatus.SKIPPED,
                gate_decision=gate_decision,
                source_results=source_results,
                total_sources_skipped=len(configured_sources),
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                last_snapshot_at=gate_decision.last_snapshot_at,
                last_known_good_preserved=True,
                downstream_demand_refreshed=False,
            )

        logger.info(
            "Starting multi-source market refresh for %d configured sources (force=%s)...",
            len(configured_sources),
            effective_force,
        )

        # ===================================================================
        # PHASE 1: Multi-Source Ingestion & Persistence (All Sources)
        # ===================================================================
        source_results: Dict[str, MarketSourceRefreshResult] = {}
        succeeded_sources: List[MarketSourceType] = []

        total_jobs_fetched = 0
        total_jobs_normalized = 0
        total_jobs_persisted = 0
        sources_failed = 0

        for source_type in configured_sources:
            source_name = source_type.value
            source_start = datetime.now(timezone.utc)

            try:
                adapter = self.registry.get_adapter(source_type)
                if not adapter.is_configured:
                    raise MarketSourceConfigurationError(
                        f"Market source '{source_name}' is not configured."
                    )

                # Prepare optional source-specific fetch limits if configured
                kwargs: Dict[str, Any] = {}
                if cfg.source_fetch_limits:
                    lim = (
                        cfg.source_fetch_limits.get(source_name)
                        or cfg.source_fetch_limits.get(source_type.name)
                    )
                    if lim is not None:
                        if source_type in (MarketSourceType.GREENHOUSE, MarketSourceType.ASHBY):
                            kwargs["max_results"] = lim
                        elif source_type == MarketSourceType.LEVER:
                            kwargs["max_results"] = lim
                            kwargs["limit"] = lim
                        elif source_type == MarketSourceType.ADZUNA:
                            kwargs["results_per_page"] = min(lim, 50)

                # 1a. Fetch & Normalize
                normalized_jobs = adapter.fetch_and_normalize_jobs(
                    queries=cfg.queries,
                    **kwargs,
                )
                if not isinstance(normalized_jobs, list):
                    raise ValueError(
                        f"Adapter for '{source_name}' returned invalid non-list result: {type(normalized_jobs)}"
                    )

                jobs_count = len(normalized_jobs)

                # 1b. Persist jobs
                savepoint = db.begin_nested() if db is not None and hasattr(db, "begin_nested") else None
                try:
                    persistence_metrics = self.repository.persist_jobs(
                        jobs=normalized_jobs,
                        db=db,
                        commit=False,
                    )
                    if savepoint is not None:
                        savepoint.commit()
                except Exception:
                    if savepoint is not None:
                        savepoint.rollback()
                    raise

                persisted_count = (
                    persistence_metrics.inserted
                    + persistence_metrics.updated
                    + persistence_metrics.unchanged
                )

                duration = (datetime.now(timezone.utc) - source_start).total_seconds()
                source_results[source_name] = MarketSourceRefreshResult(
                    source=source_type,
                    status=MarketSourceStatus.SUCCESS,
                    jobs_fetched=jobs_count,
                    jobs_normalized=jobs_count,
                    jobs_persisted=persisted_count,
                    duration_seconds=duration,
                )

                total_jobs_fetched += jobs_count
                total_jobs_normalized += jobs_count
                total_jobs_persisted += persisted_count
                succeeded_sources.append(source_type)

                logger.info(
                    "Phase 1: Ingestion successful for '%s' (%d jobs normalized, %d persisted).",
                    source_name,
                    jobs_count,
                    persisted_count,
                )

            except Exception as exc:
                duration = (datetime.now(timezone.utc) - source_start).total_seconds()
                err_category = type(exc).__name__
                sanitized_msg = sanitize_error_message(str(exc))

                logger.error(
                    "Phase 1: Ingestion failed for '%s': %s (%s). Preserving last-known-good state.",
                    source_name,
                    err_category,
                    sanitized_msg,
                )

                source_results[source_name] = MarketSourceRefreshResult(
                    source=source_type,
                    status=MarketSourceStatus.FAILED,
                    jobs_fetched=0,
                    jobs_normalized=0,
                    jobs_persisted=0,
                    error_category=err_category,
                    error_message=sanitized_msg,
                    duration_seconds=duration,
                )
                sources_failed += 1

        # ===================================================================
        # PHASE 2: Downstream Market Intelligence (Succeeded Sources Only)
        # ===================================================================
        downstream_metrics: Dict[str, Any] = {}
        snapshot_at: Optional[datetime] = None

        if succeeded_sources:
            # Synchronized snapshot timestamp across all sources refreshing in this run
            snapshot_at = datetime.now(timezone.utc)

            for source_type in succeeded_sources:
                source_name = source_type.value
                savepoint = db.begin_nested() if db is not None and hasattr(db, "begin_nested") else None
                try:
                    # 2a. Canonical Skill Extraction
                    ext_metrics = self.extraction_service.process_persisted_jobs(
                        db=db,
                        source=source_name,
                        reconcile=True,
                        commit=False,
                    )

                    # 2b. Market Demand Aggregation (P1-E)
                    agg_metrics = self.aggregator.aggregate_market_demand(
                        db=db,
                        source=source_name,
                        reconcile=True,
                        commit=False,
                    )

                    # 2c. Historical Snapshot Creation (P1-F)
                    snapshots, snap_ins, snap_unc = self.snapshot_service.create_snapshot_from_current_demand(
                        db=db,
                        source=source_name,
                        snapshot_at=snapshot_at,
                        commit=False,
                    )

                    # 2d. Growth Calculation & Persistence (P1-F)
                    growth_records, g_ins, g_upd, g_unc = self.growth_service.compute_and_persist_growth(
                        db=db,
                        source=source_name,
                        commit=False,
                    )

                    if savepoint is not None:
                        savepoint.commit()

                    downstream_metrics[source_name] = {
                        "jobs_persisted": source_results[source_name].jobs_persisted,
                        "skills_matched": ext_metrics.skills_matched,
                        "skills_with_demand": agg_metrics.skills_with_demand,
                        "snapshots_persisted": snap_ins + snap_unc,
                        "growth_records_computed": len(growth_records),
                    }

                    logger.info(
                        "Phase 2: Downstream intelligence completed for '%s': "
                        "%d skills matched, %d snapshots, %d growth records.",
                        source_name,
                        ext_metrics.skills_matched,
                        snap_ins + snap_unc,
                        len(growth_records),
                    )

                except Exception as down_exc:
                    if savepoint is not None:
                        savepoint.rollback()
                    err_category = type(down_exc).__name__
                    sanitized_msg = sanitize_error_message(str(down_exc))
                    logger.error(
                        "Phase 2: Downstream processing failed for '%s': %s (%s).",
                        source_name,
                        err_category,
                        sanitized_msg,
                    )
                    prev_res = source_results[source_name]
                    source_results[source_name] = MarketSourceRefreshResult(
                        source=source_type,
                        status=MarketSourceStatus.FAILED,
                        jobs_fetched=prev_res.jobs_fetched,
                        jobs_normalized=prev_res.jobs_normalized,
                        jobs_persisted=prev_res.jobs_persisted,
                        error_category=err_category,
                        error_message=sanitized_msg,
                        duration_seconds=prev_res.duration_seconds,
                    )

        # Re-evaluate final counts
        final_succeeded_count = sum(
            1 for r in source_results.values() if r.status == MarketSourceStatus.SUCCESS
        )
        final_failed_count = sum(
            1 for r in source_results.values() if r.status == MarketSourceStatus.FAILED
        )

        if final_succeeded_count == len(configured_sources):
            overall_status = MarketRefreshStatus.COMPLETED
        elif final_succeeded_count > 0:
            overall_status = MarketRefreshStatus.PARTIALLY_COMPLETED
        else:
            overall_status = MarketRefreshStatus.FAILED

        downstream_refreshed = (final_succeeded_count > 0)

        # 3. Transaction Commit or Rollback
        if cfg.commit and db is not None:
            try:
                if downstream_refreshed:
                    db.commit()
                else:
                    db.rollback()
            except Exception as commit_exc:
                logger.error("Transaction commit failed during multi-source refresh: %s", commit_exc)
                if db is not None:
                    db.rollback()
                overall_status = MarketRefreshStatus.FAILED
                downstream_refreshed = False

        completed_at = datetime.now(timezone.utc)
        error_msg = None
        if overall_status == MarketRefreshStatus.FAILED:
            error_msg = "All configured market sources failed during refresh. Last-known-good state preserved."

        return MultiSourceRefreshResult(
            status=overall_status,
            gate_decision=gate_decision,
            source_results=source_results,
            total_jobs_fetched=total_jobs_fetched,
            total_jobs_normalized=total_jobs_normalized,
            total_jobs_persisted=total_jobs_persisted,
            total_sources_succeeded=final_succeeded_count,
            total_sources_failed=final_failed_count,
            total_sources_skipped=0,
            started_at=started_at,
            completed_at=completed_at,
            snapshot_at=snapshot_at if downstream_refreshed else None,
            last_snapshot_at=gate_decision.last_snapshot_at,
            last_known_good_preserved=True,
            downstream_demand_refreshed=downstream_refreshed,
            downstream_metrics=downstream_metrics if downstream_refreshed else None,
            error=error_msg,
        )
