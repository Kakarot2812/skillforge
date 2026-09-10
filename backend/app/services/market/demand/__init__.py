"""
Market demand intelligence package for SkillForge AI.
Post-MVP Phase 1, Checkpoints P1-E & P1-F.
"""

from app.services.market.demand.aggregator import (
    MarketDemandAggregator,
    aggregate_market_demand,
    calculate_demand_metrics,
)
from app.services.market.demand.growth import (
    MarketDemandGrowthService,
    MarketSkillDemandGrowthRepository,
    calculate_growth_rate,
    classify_growth_rate,
)
from app.services.market.demand.refresh import (
    MarketDemandRefreshService,
    refresh_market_demand,
)
from app.services.market.demand.repository import (
    MarketSkillDemandRepository,
)
from app.services.market.demand.snapshots import (
    MarketDemandSnapshotConflictError,
    MarketDemandSnapshotService,
    MarketSkillDemandSnapshotRepository,
)

__all__ = [
    # Demand Aggregator (P1-E)
    "MarketDemandAggregator",
    "aggregate_market_demand",
    "calculate_demand_metrics",
    "MarketSkillDemandRepository",
    # Snapshots (P1-F)
    "MarketDemandSnapshotConflictError",
    "MarketDemandSnapshotService",
    "MarketSkillDemandSnapshotRepository",
    # Growth (P1-F)
    "MarketDemandGrowthService",
    "MarketSkillDemandGrowthRepository",
    "calculate_growth_rate",
    "classify_growth_rate",
    # Refresh (P1-F)
    "MarketDemandRefreshService",
    "refresh_market_demand",
]
