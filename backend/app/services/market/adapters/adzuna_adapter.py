"""
Adzuna source adapter implementation for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-G.

Adapts the existing Adzuna client, cleaning, and ingestion pipeline
to conform to the MarketSourceAdapter abstraction without modifying
existing Adzuna behavior or duplicating business logic.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from app.config import settings
from app.services.market.adapters.base import MarketSourceAdapter, MarketSourceType
from app.services.market.cleaning import clean_adzuna_job
from app.services.market.clients.adzuna_client import AdzunaClient, AdzunaJobItem
from app.services.market.ingestion.adzuna_ingestion import (
    DEFAULT_COUNTRY,
    DEFAULT_PAGES_PER_QUERY,
    DEFAULT_RESULTS_PER_PAGE,
    AdzunaIngestionService,
)
from app.services.market.models import AdzunaIngestionResult, NormalizedMarketJob

logger = logging.getLogger(__name__)


class AdzunaAdapter(MarketSourceAdapter):
    """
    MarketSourceAdapter implementation for the Adzuna Job Search API.

    Delegates fetching, rate-limiting, and error handling to AdzunaClient,
    cleaning and structural validation to clean_adzuna_job,
    and deduplication to AdzunaIngestionService.
    """

    def __init__(
        self,
        ingestion_service: Optional[AdzunaIngestionService] = None,
        client: Optional[AdzunaClient] = None,
    ):
        if ingestion_service is not None:
            self.ingestion_service = ingestion_service
        elif client is not None:
            self.ingestion_service = AdzunaIngestionService(client=client)
        else:
            self.ingestion_service = AdzunaIngestionService()

    @property
    def source_type(self) -> MarketSourceType:
        """Returns MarketSourceType.ADZUNA."""
        return MarketSourceType.ADZUNA

    @property
    def is_configured(self) -> bool:
        """
        Checks if Adzuna credentials (ADZUNA_APP_ID and ADZUNA_APP_KEY)
        are present in configuration.
        """
        app_id = settings.ADZUNA_APP_ID
        app_key = settings.ADZUNA_APP_KEY
        return bool(app_id and app_id.strip() and app_key and app_key.strip())

    def fetch_and_normalize_jobs(
        self,
        queries: Optional[List[str]] = None,
        country: str = DEFAULT_COUNTRY,
        pages_per_query: int = DEFAULT_PAGES_PER_QUERY,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
        **kwargs: Any,
    ) -> List[NormalizedMarketJob]:
        """
        Fetches job postings from Adzuna across target queries, executes
        deterministic cleaning and deduplication, and returns canonical
        NormalizedMarketJob objects.
        """
        result: AdzunaIngestionResult = self.ingestion_service.ingest_market_jobs(
            queries=queries,
            country=country,
            pages_per_query=pages_per_query,
            results_per_page=results_per_page,
        )
        return result.final_jobs

    def normalize_job(self, raw_job: Any) -> Optional[NormalizedMarketJob]:
        """
        Deterministically cleans and normalizes a raw Adzuna posting.

        Accepts:
        - NormalizedMarketJob (returns as-is)
        - AdzunaJobItem (passes to clean_adzuna_job)
        - Raw dict (constructs AdzunaJobItem and cleans)

        Returns:
            NormalizedMarketJob if valid, or None if rejected.
        """
        if isinstance(raw_job, NormalizedMarketJob):
            return raw_job

        if isinstance(raw_job, AdzunaJobItem):
            return clean_adzuna_job(raw_job)

        if isinstance(raw_job, dict):
            # Construct typed AdzunaJobItem preserving raw upstream data
            company_raw = raw_job.get("company_name")
            if not company_raw and isinstance(raw_job.get("company"), dict):
                company_raw = raw_job["company"].get("display_name")

            location_raw = raw_job.get("location_name")
            if not location_raw and isinstance(raw_job.get("location"), dict):
                location_raw = raw_job["location"].get("display_name")

            category_raw = raw_job.get("category_label")
            if not category_raw and isinstance(raw_job.get("category"), dict):
                category_raw = raw_job["category"].get("label") or raw_job["category"].get("tag")

            job_item = AdzunaJobItem(
                id=str(raw_job.get("id", "")),
                title=str(raw_job.get("title", "")),
                description=str(raw_job.get("description", "")),
                company_name=company_raw,
                location_name=location_raw,
                category_label=category_raw,
                created=raw_job.get("created"),
                redirect_url=raw_job.get("redirect_url"),
                salary_min=raw_job.get("salary_min"),
                salary_max=raw_job.get("salary_max"),
                raw_data=raw_job,
            )
            return clean_adzuna_job(job_item)

        logger.debug("AdzunaAdapter cannot normalize unsupported input type: %s", type(raw_job))
        return None
