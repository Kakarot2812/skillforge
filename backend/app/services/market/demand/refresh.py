"""
Deterministic 24-hour market demand refresh service for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-F.

Orchestrates the market demand ingestion, persistence, extraction, aggregation,
snapshot, and growth pipeline under a deterministic 24-hour refresh policy.

Core principles:
- "The LLM never decides what is true."
- Purely deterministic orchestration.
- 24-hour policy: skips refresh and network calls if latest successful snapshot < 24 hours old (unless force=True).
- Atomic failure safety: if any stage fails, previous known-good state is preserved intact via rollback.
- Historical snapshot immutability: snapshots are never mutated or deleted on failure.
- Zero secret / credential exposure in metrics, logs, or error returns.
- Callable service: no infinite loops, no sleep loops; designed for cron / external scheduler invocation.
- Strict isolation: MVP tables (skill_demand, job_roles, candidate skill gaps/priorities) are untouched.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.services.market.demand.aggregator import MarketDemandAggregator
from app.services.market.demand.growth import MarketDemandGrowthService
from app.services.market.demand.snapshots import MarketDemandSnapshotService
from app.services.market.extraction import MarketSkillExtractionService
from app.services.market.ingestion.adzuna_ingestion import (
    DEFAULT_COUNTRY,
    DEFAULT_PAGES_PER_QUERY,
    DEFAULT_RESULTS_PER_PAGE,
)
from app.services.market.models import MarketDemandRefreshResult
from app.services.market.pipeline import AdzunaMarketPipeline

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_HOURS = 24


class MarketDemandRefreshService:
    """
    Orchestration service for the 24-hour market demand refresh cycle.
    """

    def __init__(
        self,
        pipeline: Optional[AdzunaMarketPipeline] = None,
        extraction_service: Optional[MarketSkillExtractionService] = None,
        aggregator: Optional[MarketDemandAggregator] = None,
        snapshot_service: Optional[MarketDemandSnapshotService] = None,
        growth_service: Optional[MarketDemandGrowthService] = None,
    ):
        self.pipeline = pipeline or AdzunaMarketPipeline()
        self.extraction_service = extraction_service or MarketSkillExtractionService()
        self.aggregator = aggregator or MarketDemandAggregator()
        self.snapshot_service = snapshot_service or MarketDemandSnapshotService()
        self.growth_service = growth_service or MarketDemandGrowthService(
            snapshot_service=self.snapshot_service
        )

    def refresh(
        self,
        db: Session,
        force: bool = False,
        source: str = "adzuna",
        queries: Optional[List[str]] = None,
        country: str = DEFAULT_COUNTRY,
        pages_per_query: int = DEFAULT_PAGES_PER_QUERY,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
        commit: bool = True,
    ) -> MarketDemandRefreshResult:
        """
        Executes the deterministic 24-hour market demand refresh cycle.

        Sequence:
        1. Check 24-hour refresh policy against latest snapshot.
        2. Skip if force=False and latest snapshot < 24h old (no network calls).
        3. Fetch configured Adzuna data.
        4. Clean/normalize jobs.
        5. Persist market jobs.
        6. Extract canonical skills.
        7. Aggregate market demand using P1-E.
        8. Persist immutable historical snapshot.
        9. Calculate growth.
        10. Persist current growth.
        11. Return structured operational metrics.
        """
        clean_source = source.strip() if source else "adzuna"
        started_at = datetime.now(timezone.utc)

        # 1 & 2: Check 24-hour policy
        latest_timestamps = self.snapshot_service.get_latest_snapshot_timestamps(
            db=db,
            source=clean_source,
            limit=1,
        )
        last_snapshot_at = latest_timestamps[0] if latest_timestamps else None

        if last_snapshot_at is not None and not force:
            last_ts_aware = (
                last_snapshot_at if last_snapshot_at.tzinfo is not None
                else last_snapshot_at.replace(tzinfo=timezone.utc)
            )
            elapsed = started_at - last_ts_aware
            if elapsed < timedelta(hours=REFRESH_INTERVAL_HOURS):
                logger.info(
                    "24-hour refresh policy: skipping refresh for source '%s'. "
                    "Last snapshot was %s (elapsed: %s < %dh).",
                    clean_source,
                    last_ts_aware.isoformat(),
                    str(elapsed),
                    REFRESH_INTERVAL_HOURS,
                )
                return MarketDemandRefreshResult(
                    source=clean_source,
                    refreshed=False,
                    reason="skipped_within_24h",
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    last_snapshot_at=last_ts_aware,
                )

        logger.info(
            "Starting market demand refresh for source '%s' (force=%s, last_snapshot=%s)...",
            clean_source,
            force,
            last_snapshot_at.isoformat() if last_snapshot_at else "none",
        )

        try:
            # 3, 4, 5: Ingest, Clean, Persist market jobs
            pipeline_result = self.pipeline.run_pipeline(
                db=db,
                queries=queries,
                country=country,
                pages_per_query=pages_per_query,
                results_per_page=results_per_page,
                commit=False,
            )

            # 6: Extract canonical skills
            extraction_metrics = self.extraction_service.process_persisted_jobs(
                db=db,
                source=clean_source,
                reconcile=True,
                commit=False,
            )

            # 7: Aggregate market demand (P1-E)
            aggregation_metrics = self.aggregator.aggregate_market_demand(
                db=db,
                source=clean_source,
                reconcile=True,
                commit=False,
            )

            # 8: Persist immutable historical snapshot (P1-F)
            snapshot_at = datetime.now(timezone.utc)
            snapshot_entities, snap_ins, snap_unc = self.snapshot_service.create_snapshot_from_current_demand(
                db=db,
                source=clean_source,
                snapshot_at=snapshot_at,
                commit=False,
            )

            # 9 & 10: Calculate and persist current growth (P1-F)
            growth_records, g_ins, g_upd, g_unc = self.growth_service.compute_and_persist_growth(
                db=db,
                source=clean_source,
                commit=False,
            )

            if commit:
                db.commit()

            completed_at = datetime.now(timezone.utc)
            growth_breakdown = dict(Counter(r.growth_class for r in growth_records))

            logger.info(
                "Market demand refresh successful for source '%s': %d jobs, %d skills, %d snapshots, %d growth",
                clean_source,
                pipeline_result.final_jobs_count,
                extraction_metrics.skills_matched,
                len(snapshot_entities),
                len(growth_records),
            )

            return MarketDemandRefreshResult(
                source=clean_source,
                refreshed=True,
                reason="completed",
                started_at=started_at,
                completed_at=completed_at,
                snapshot_at=snapshot_at,
                last_snapshot_at=last_snapshot_at,
                jobs_ingested=pipeline_result.raw_jobs_seen,
                jobs_persisted=pipeline_result.inserted + pipeline_result.updated,
                skills_extracted=extraction_metrics.skills_matched,
                demand_records_aggregated=aggregation_metrics.skills_with_demand,
                snapshot_records_created=snap_ins + snap_unc,
                growth_records_computed=len(growth_records),
                growth_breakdown=growth_breakdown,
                error=None,
            )

        except Exception as e:
            db.rollback()
            err_type = type(e).__name__
            logger.error(
                "Market demand refresh failed for source '%s': %s. Previous known-good state preserved intact.",
                clean_source,
                err_type,
            )
            return MarketDemandRefreshResult(
                source=clean_source,
                refreshed=False,
                reason=f"failed: {err_type}",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                last_snapshot_at=last_snapshot_at,
                error=err_type,
            )


def refresh_market_demand(
    db: Session,
    force: bool = False,
    source: str = "adzuna",
    queries: Optional[List[str]] = None,
    country: str = DEFAULT_COUNTRY,
    pages_per_query: int = DEFAULT_PAGES_PER_QUERY,
    results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
    commit: bool = True,
) -> MarketDemandRefreshResult:
    """
    Callable orchestration entry point for deterministic 24-hour market demand refresh.
    Designed for execution by crons, workers, or deployment orchestrators.
    """
    service = MarketDemandRefreshService()
    return service.refresh(
        db=db,
        force=force,
        source=source,
        queries=queries,
        country=country,
        pages_per_query=pages_per_query,
        results_per_page=results_per_page,
        commit=commit,
    )
