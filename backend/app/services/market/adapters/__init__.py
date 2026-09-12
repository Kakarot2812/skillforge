"""
Market source adapter package for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-G.
"""

from app.services.market.adapters.adzuna_adapter import AdzunaAdapter
from app.services.market.adapters.greenhouse_adapter import (
    GreenhouseAPIError,
    GreenhouseAdapter,
    GreenhouseConnectionError,
    GreenhouseError,
    GreenhouseResponseError,
    clean_greenhouse_html,
)
from app.services.market.adapters.lever_adapter import (
    LeverAPIError,
    LeverAdapter,
    LeverConnectionError,
    LeverError,
    LeverResponseError,
    clean_lever_description,
)
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
    get_market_source_adapter,
    market_source_registry,
)

__all__ = [
    # Types & Base
    "MarketSourceType",
    "MarketSourceAdapter",
    # Adapters
    "AdzunaAdapter",
    "GreenhouseAdapter",
    "clean_greenhouse_html",
    "LeverAdapter",
    "clean_lever_description",
    # Registry
    "MarketSourceRegistry",
    "market_source_registry",
    "get_market_source_adapter",
    # Exceptions
    "MarketSourceError",
    "UnknownMarketSourceError",
    "UnsupportedMarketSourceError",
    "MarketSourceConfigurationError",
    "GreenhouseError",
    "GreenhouseConnectionError",
    "GreenhouseAPIError",
    "GreenhouseResponseError",
    "LeverError",
    "LeverConnectionError",
    "LeverAPIError",
    "LeverResponseError",
]
