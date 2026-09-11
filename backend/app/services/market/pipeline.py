"""
Market ingestion and persistence pipeline orchestration for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-C.

Connects:
P1-B Adzuna Ingestion (in-memory clean and deduplicated records)
    ↓
P1-C MarketJobRepository (PostgreSQL native idempotent upsert)
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.services.market.ingestion.adzuna_ingestion import (
    DEFAULT_COUNTRY,
    DEFAULT_PAGES_PER_QUERY,
    DEFAULT_RESULTS_PER_PAGE,
    DEFAULT_ROLE_QUERIES,
    AdzunaIngestionService,
)
from app.services.market.models import AdzunaIngestionResult
from app.services.market.repository import MarketJobRepository, PersistenceMetrics

logger = logging.getLogger(__name__)


@dataclass
class MarketPipelineResult:
    """
    Consolidated audit result combining P1-B ingestion metrics
    and P1-C database persistence metrics.
    Guaranteed free of credentials or sensitive headers.
    """
    source: str = "adzuna"
    requested_queries: List[str] = field(default_factory=list)
    pages_fetched: int = 0
    raw_jobs_seen: int = 0
    valid_jobs: int = 0
    cleaned_jobs: int = 0
    duplicates_removed: int = 0
    final_jobs_count: int = 0
    attempted: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0

    def to_summary_dict(self) -> Dict[str, Any]:
        """Returns safe summary audit dictionary without credentials or headers."""
        return {
            "source": self.source,
            "requested_queries": list(self.requested_queries),
            "pages_fetched": self.pages_fetched,
            "raw_jobs_seen": self.raw_jobs_seen,
            "valid_jobs": self.valid_jobs,
            "cleaned_jobs": self.cleaned_jobs,
            "duplicates_removed": self.duplicates_removed,
            "final_jobs_count": self.final_jobs_count,
            "persistence": {
                "attempted": self.attempted,
                "inserted": self.inserted,
                "updated": self.updated,
                "unchanged": self.unchanged,
                "failed": self.failed,
            },
        }


class AdzunaMarketPipeline:
    """
    Orchestration layer linking Adzuna ingestion (P1-B) with
    PostgreSQL persistence (P1-C).
    """

    def __init__(
        self,
        ingestion_service: Optional[AdzunaIngestionService] = None,
        repository: Optional[MarketJobRepository] = None,
    ):
        self.ingestion_service = ingestion_service or AdzunaIngestionService()
        self.repository = repository or MarketJobRepository()

    def run_pipeline(
        self,
        db: Session,
        queries: Optional[List[str]] = None,
        country: str = DEFAULT_COUNTRY,
        pages_per_query: int = DEFAULT_PAGES_PER_QUERY,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
        commit: bool = True,
    ) -> MarketPipelineResult:
        """
        Executes end-to-end ingestion and persistence.

        1. Ingests and cleans jobs using AdzunaIngestionService.
        2. Persists normalized jobs using MarketJobRepository.
        3. Returns combined audit metrics.
        """
        logger.info("Starting Adzuna market pipeline execution...")

        # 1. Ingestion (P1-B)
        ingestion_result: AdzunaIngestionResult = self.ingestion_service.ingest_market_jobs(
            queries=queries,
            country=country,
            pages_per_query=pages_per_query,
            results_per_page=results_per_page,
        )

        # 2. Persistence (P1-C)
        persistence_metrics: PersistenceMetrics = self.repository.persist_jobs(
            jobs=ingestion_result.final_jobs,
            db=db,
            commit=commit,
        )

        logger.info(
            "Adzuna market pipeline completed: %d raw jobs -> %d unique -> %d inserted, %d updated, %d unchanged",
            ingestion_result.raw_jobs_seen,
            len(ingestion_result.final_jobs),
            persistence_metrics.inserted,
            persistence_metrics.updated,
            persistence_metrics.unchanged,
        )

        return MarketPipelineResult(
            source=ingestion_result.source,
            requested_queries=ingestion_result.requested_queries,
            pages_fetched=ingestion_result.pages_fetched,
            raw_jobs_seen=ingestion_result.raw_jobs_seen,
            valid_jobs=ingestion_result.valid_jobs,
            cleaned_jobs=ingestion_result.cleaned_jobs,
            duplicates_removed=ingestion_result.duplicates_removed,
            final_jobs_count=len(ingestion_result.final_jobs),
            attempted=persistence_metrics.attempted,
            inserted=persistence_metrics.inserted,
            updated=persistence_metrics.updated,
            unchanged=persistence_metrics.unchanged,
            failed=persistence_metrics.failed,
        )
