"""Canonical and curated roadmap definitions for SkillForge AI.
Contains structured roadmap definitions for 12 domains with progressive practice problems:
- 5 Canonical roles (backed by JobRole and market demand data)
- 7 Curated domains (roadmap catalog without market data claims)
"""
from app.db.roadmaps_data import (
    CANONICAL_ROLE_IDS,
    ROADMAP_IDS,
    ROADMAPS_SEED_DATA,
)

__all__ = [
    "CANONICAL_ROLE_IDS",
    "ROADMAP_IDS",
    "ROADMAPS_SEED_DATA",
]
