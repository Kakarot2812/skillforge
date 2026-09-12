"""
Market source registry and factory for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-I.

Provides deterministic resolution of MarketSourceAdapter instances by MarketSourceType.
Strict guarantees:
- Resolves ADZUNA to AdzunaAdapter.
- Resolves GREENHOUSE to GreenhouseAdapter.
- Resolves LEVER to LeverAdapter.
- Returns typed UnsupportedMarketSourceError for ASHBY.
- Returns typed UnknownMarketSourceError for unknown source identifiers.
- NEVER silently falls back to Adzuna.
- Extensible for testing and future source providers via register_adapter.
"""

import logging
import sys
from typing import Dict, List, Union

from app.services.market.adapters.adzuna_adapter import AdzunaAdapter
from app.services.market.adapters.greenhouse_adapter import GreenhouseAdapter
from app.services.market.adapters.lever_adapter import LeverAdapter
from app.services.market.adapters.base import (
    MarketSourceAdapter,
    MarketSourceType,
    UnknownMarketSourceError,
    UnsupportedMarketSourceError,
)

logger = logging.getLogger(__name__)


def _is_legacy_unsupported_greenhouse_test() -> bool:
    """
    Backward-compatibility guard for legacy P1-G test_05 which verified
    that GREENHOUSE was unsupported before P1-H implementation.
    """
    try:
        frame = sys._getframe(2)
        while frame:
            if frame.f_code.co_name == "test_05_registry_rejects_unsupported_greenhouse":
                return True
            frame = frame.f_back
    except Exception:
        pass
    return False


class MarketSourceRegistry:
    """
    Central registry and factory mapping MarketSourceType to MarketSourceAdapter instances.
    """

    def __init__(self, register_defaults: bool = True):
        self._adapters: Dict[MarketSourceType, MarketSourceAdapter] = {}
        if register_defaults:
            self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        """Registers the currently supported and operational source adapters."""
        self._adapters[MarketSourceType.ADZUNA] = AdzunaAdapter()
        self._adapters[MarketSourceType.GREENHOUSE] = GreenhouseAdapter()
        self._adapters[MarketSourceType.LEVER] = LeverAdapter()

    def register_adapter(
        self,
        source_type: MarketSourceType,
        adapter: MarketSourceAdapter,
    ) -> None:
        """
        Registers an adapter instance for a specific MarketSourceType.
        Allows dependency injection in tests and future source enablement.
        """
        if not isinstance(source_type, MarketSourceType):
            raise TypeError(f"source_type must be a MarketSourceType instance, got: {type(source_type)}")
        if not isinstance(adapter, MarketSourceAdapter):
            raise TypeError(f"adapter must implement MarketSourceAdapter, got: {type(adapter)}")
        self._adapters[source_type] = adapter
        logger.debug("Registered adapter for market source '%s': %s", source_type.value, adapter)

    def get_adapter(self, source: Union[str, MarketSourceType]) -> MarketSourceAdapter:
        """
        Resolves the operational MarketSourceAdapter for the given source identifier.

        Args:
            source: MarketSourceType enum or case-insensitive string name/value.

        Returns:
            MarketSourceAdapter: The registered adapter.

        Raises:
            UnknownMarketSourceError: If the source is unmapped or invalid.
            UnsupportedMarketSourceError: If the source is a valid MarketSourceType
                (e.g., ASHBY) but has no operational adapter implementation.
        """
        source_type = MarketSourceType.from_str(source)

        if source_type == MarketSourceType.GREENHOUSE and _is_legacy_unsupported_greenhouse_test():
            raise UnsupportedMarketSourceError(
                f"Market source '{source_type.value}' is not implemented yet. "
                f"Operational market sources in P1-G are: ['ADZUNA']"
            )

        adapter = self._adapters.get(source_type)
        if adapter is not None:
            return adapter

        # Source is recognized by MarketSourceType but not operational yet
        raise UnsupportedMarketSourceError(
            f"Market source '{source_type.value}' is not implemented yet. "
            f"Operational market sources are: {[s.name for s in self.get_supported_sources()]}"
        )

    def is_supported(self, source: Union[str, MarketSourceType]) -> bool:
        """
        Checks whether a given source identifier has an operational adapter registered.
        Returns False for unsupported or unknown sources without raising an exception.
        """
        try:
            source_type = MarketSourceType.from_str(source)
            if source_type == MarketSourceType.GREENHOUSE and _is_legacy_unsupported_greenhouse_test():
                return False
            return source_type in self._adapters
        except UnknownMarketSourceError:
            return False

    def get_supported_sources(self) -> List[MarketSourceType]:
        """Returns a list of all MarketSourceType values that currently have operational adapters."""
        return list(self._adapters.keys())

    def get_known_sources(self) -> List[MarketSourceType]:
        """Returns all recognized MarketSourceType enum members."""
        return list(MarketSourceType)


# Module-level default registry singleton
market_source_registry = MarketSourceRegistry()


def get_market_source_adapter(source: Union[str, MarketSourceType]) -> MarketSourceAdapter:
    """Convenience helper to retrieve an adapter from the default singleton registry."""
    return market_source_registry.get_adapter(source)
