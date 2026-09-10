"""
Market demand intelligence package for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-E.
"""

from app.services.market.demand.aggregator import (
    MarketDemandAggregator,
    aggregate_market_demand,
    calculate_demand_metrics,
)
from app.services.market.demand.repository import (
    MarketSkillDemandRepository,
)

__all__ = [
    "MarketDemandAggregator",
    "aggregate_market_demand",
    "calculate_demand_metrics",
    "MarketSkillDemandRepository",
]
