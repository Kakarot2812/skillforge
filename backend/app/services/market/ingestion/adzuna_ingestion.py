"""
Adzuna market data ingestion service.
Post-MVP Phase 1, Checkpoint P1-B.

Orchestrates:
- Market role query execution via the existing AdzunaClient.
- Raw job extraction from Adzuna responses.
- Deterministic cleaning and field normalization.
- Strict deterministic deduplication on (source, external_job_id).
- In-memory NormalizedMarketJob collection with audit metrics.
"""

import logging
from typing import List, Optional, Set, Tuple

from app.services.market.cleaning import clean_adzuna_job
from app.services.market.clients.adzuna_client import AdzunaClient
from app.services.market.models import AdzunaIngestionResult, NormalizedMarketJob

logger = logging.getLogger(__name__)

# Standard role queries defined for Checkpoint P1-B
DEFAULT_ROLE_QUERIES: List[str] = [
    "backend developer",
    "full stack developer",
    "frontend developer",
    "devops engineer",
    "machine learning engineer",
]

DEFAULT_COUNTRY: str = "in"
DEFAULT_PAGES_PER_QUERY: int = 1
DEFAULT_RESULTS_PER_PAGE: int = 20


class AdzunaIngestionService:
    """
    Ingestion pipeline consuming Adzuna API postings, performing deterministic
    cleaning, and deduplicating records in-memory.

    Never executes direct HTTP requests; delegates entirely to AdzunaClient.
    """

    def __init__(self, client: Optional[AdzunaClient] = None):
        self.client = client or AdzunaClient()

    def ingest_market_jobs(
        self,
        queries: Optional[List[str]] = None,
        country: str = DEFAULT_COUNTRY,
        pages_per_query: int = DEFAULT_PAGES_PER_QUERY,
        results_per_page: int = DEFAULT_RESULTS_PER_PAGE,
    ) -> AdzunaIngestionResult:
        """
        Executes an ingestion run across target role queries.

        Args:
            queries: List of role search query strings. Defaults to standard P1-B roles.
            country: 2-letter ISO country code (e.g. 'in' for India).
            pages_per_query: Number of pages to retrieve per role query (default: 1).
            results_per_page: Number of postings per page (1 to 50, default: 20).

        Returns:
            AdzunaIngestionResult with audit counts and deduplicated normalized jobs.

        Raises:
            ValueError: If pagination or country arguments are invalid.
            AdzunaConfigurationError: If Adzuna credentials are not configured.
            AdzunaError: If remote API or connection errors occur.
        """
        # Parameter validation
        if pages_per_query < 1:
            raise ValueError("pages_per_query must be an integer >= 1")
        if results_per_page < 1 or results_per_page > 50:
            raise ValueError("results_per_page must be an integer between 1 and 50")

        country_code = country.strip().lower() if country else ""
        if len(country_code) != 2:
            raise ValueError("country must be a valid 2-letter ISO code (e.g., 'in')")

        if queries is None:
            target_queries = list(DEFAULT_ROLE_QUERIES)
        else:
            target_queries = [q.strip() for q in queries if q and q.strip()]

        if not target_queries:
            return AdzunaIngestionResult(
                source="adzuna",
                requested_queries=[],
                pages_fetched=0,
                raw_jobs_seen=0,
                valid_jobs=0,
                cleaned_jobs=0,
                duplicates_removed=0,
                final_jobs=[],
            )

        pages_fetched = 0
        raw_jobs_seen = 0
        valid_jobs = 0
        duplicates_removed = 0
        final_jobs: List[NormalizedMarketJob] = []
        seen_keys: Set[Tuple[str, str]] = set()

        for query in target_queries:
            for page in range(1, pages_per_query + 1):
                # Fetch page via the existing client
                search_response = self.client.search_jobs(
                    what=query,
                    page=page,
                    results_per_page=results_per_page,
                    country=country_code,
                )
                pages_fetched += 1

                for raw_job in search_response.results:
                    raw_jobs_seen += 1

                    # Deterministic cleaning and validation
                    cleaned_job = clean_adzuna_job(raw_job)
                    if cleaned_job is None:
                        # Malformed job rejected (e.g. missing id or title)
                        continue

                    valid_jobs += 1
                    dedup_key = cleaned_job.deduplication_key

                    # Deterministic deduplication: keep first occurrence
                    if dedup_key in seen_keys:
                        duplicates_removed += 1
                        continue

                    seen_keys.add(dedup_key)
                    final_jobs.append(cleaned_job)

        logger.info(
            "Adzuna ingestion completed: %d queries, %d pages, %d raw jobs, "
            "%d valid cleaned, %d duplicates removed, %d unique jobs",
            len(target_queries),
            pages_fetched,
            raw_jobs_seen,
            valid_jobs,
            duplicates_removed,
            len(final_jobs),
        )

        return AdzunaIngestionResult(
            source="adzuna",
            requested_queries=target_queries,
            pages_fetched=pages_fetched,
            raw_jobs_seen=raw_jobs_seen,
            valid_jobs=valid_jobs,
            cleaned_jobs=valid_jobs,
            duplicates_removed=duplicates_removed,
            final_jobs=final_jobs,
        )
