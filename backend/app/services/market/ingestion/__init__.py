"""
Market ingestion package for SkillForge AI.
"""

from app.services.market.ingestion.adzuna_ingestion import (
    DEFAULT_COUNTRY,
    DEFAULT_PAGES_PER_QUERY,
    DEFAULT_RESULTS_PER_PAGE,
    DEFAULT_ROLE_QUERIES,
    AdzunaIngestionService,
)

__all__ = [
    "DEFAULT_COUNTRY",
    "DEFAULT_PAGES_PER_QUERY",
    "DEFAULT_RESULTS_PER_PAGE",
    "DEFAULT_ROLE_QUERIES",
    "AdzunaIngestionService",
]
