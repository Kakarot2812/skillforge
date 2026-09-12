"""
Market intelligence services for SkillForge AI.
Post-MVP Phase 1 (P1) market integration foundation.
"""

from app.db.models import (
    MarketJob,
    MarketJobSkill,
    MarketSkillDemand,
    MarketSkillDemandGrowth,
    MarketSkillDemandSnapshot,
)
from app.services.market.cleaning import (
    clean_adzuna_job,
    clean_multiline_text,
    collapse_whitespace,
)
from app.services.market.clients.adzuna_client import (
    AdzunaAPIError,
    AdzunaClient,
    AdzunaConfigurationError,
    AdzunaConnectionError,
    AdzunaError,
    AdzunaJobItem,
    AdzunaResponseError,
    AdzunaSearchResponse,
)
from app.services.market.demand import (
    MarketDemandAggregator,
    MarketDemandGrowthService,
    MarketDemandRefreshService,
    MarketDemandSnapshotConflictError,
    MarketDemandSnapshotService,
    MarketSkillDemandGrowthRepository,
    MarketSkillDemandRepository,
    MarketSkillDemandSnapshotRepository,
    aggregate_market_demand,
    calculate_demand_metrics,
    calculate_growth_rate,
    classify_growth_rate,
    refresh_market_demand,
)
from app.services.market.extraction import (
    DeterministicSkillMatcher,
    MarketSkillExtractionService,
    extract_evidence_snippet,
)
from app.services.market.ingestion.adzuna_ingestion import (
    DEFAULT_COUNTRY,
    DEFAULT_PAGES_PER_QUERY,
    DEFAULT_RESULTS_PER_PAGE,
    DEFAULT_ROLE_QUERIES,
    AdzunaIngestionService,
)
from app.services.market.models import (
    AdzunaIngestionResult,
    MarketDemandAggregationMetrics,
    MarketDemandGrowthRecord,
    MarketDemandRefreshResult,
    MarketDemandSnapshotRecord,
    MarketJobSkillEvidence,
    MarketSkillDemandRecord,
    MarketSkillExtractionMetrics,
    NormalizedMarketJob,
)
from app.services.market.pipeline import (
    AdzunaMarketPipeline,
    MarketPipelineResult,
)
from app.services.market.adapters import (
    AdzunaAdapter,
    MarketSourceAdapter,
    MarketSourceConfigurationError,
    MarketSourceError,
    MarketSourceRegistry,
    MarketSourceType,
    UnknownMarketSourceError,
    UnsupportedMarketSourceError,
    get_market_source_adapter,
    market_source_registry,
)
from app.services.market.repository import (
    MarketJobRepository,
    MarketJobSkillRepository,
    PersistenceMetrics,
)

__all__ = [
    # Client & Exceptions (P1-A)
    "AdzunaAPIError",
    "AdzunaClient",
    "AdzunaConfigurationError",
    "AdzunaConnectionError",
    "AdzunaError",
    "AdzunaJobItem",
    "AdzunaResponseError",
    "AdzunaSearchResponse",
    # Models & Ingestion (P1-B)
    "AdzunaIngestionResult",
    "NormalizedMarketJob",
    "clean_adzuna_job",
    "clean_multiline_text",
    "collapse_whitespace",
    "DEFAULT_COUNTRY",
    "DEFAULT_PAGES_PER_QUERY",
    "DEFAULT_RESULTS_PER_PAGE",
    "DEFAULT_ROLE_QUERIES",
    "AdzunaIngestionService",
    # Persistence & Orchestration (P1-C)
    "MarketJob",
    "MarketJobRepository",
    "PersistenceMetrics",
    "AdzunaMarketPipeline",
    "MarketPipelineResult",
    # Skill Extraction & Evidence (P1-D)
    "MarketJobSkill",
    "MarketJobSkillRepository",
    "MarketJobSkillEvidence",
    "MarketSkillExtractionMetrics",
    "DeterministicSkillMatcher",
    "MarketSkillExtractionService",
    "extract_evidence_snippet",
    # Market Demand Aggregation (P1-E)
    "MarketSkillDemand",
    "MarketSkillDemandRecord",
    "MarketDemandAggregationMetrics",
    "MarketSkillDemandRepository",
    "MarketDemandAggregator",
    "aggregate_market_demand",
    "calculate_demand_metrics",
    # Historical Snapshots & Growth (P1-F)
    "MarketSkillDemandSnapshot",
    "MarketSkillDemandGrowth",
    "MarketDemandSnapshotRecord",
    "MarketDemandGrowthRecord",
    "MarketDemandRefreshResult",
    "MarketDemandSnapshotConflictError",
    "MarketDemandSnapshotService",
    "MarketSkillDemandSnapshotRepository",
    "MarketDemandGrowthService",
    "MarketSkillDemandGrowthRepository",
    "calculate_growth_rate",
    "classify_growth_rate",
    "MarketDemandRefreshService",
    "refresh_market_demand",
    # Multi-Source Market Ingestion Foundation (P1-G)
    "MarketSourceType",
    "MarketSourceAdapter",
    "AdzunaAdapter",
    "MarketSourceRegistry",
    "market_source_registry",
    "get_market_source_adapter",
    "MarketSourceError",
    "UnknownMarketSourceError",
    "UnsupportedMarketSourceError",
    "MarketSourceConfigurationError",
]
