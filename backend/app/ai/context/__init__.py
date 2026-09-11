"""
Verified Context Contract package for SkillForge AI.
Post-MVP Phase 2, Checkpoint P2-B.

Enforces deterministic evidence boundaries between SkillForge intelligence and LLMs.
"""

from app.ai.context.exceptions import (
    ContextImmutabilityError,
    ContextValidationError,
    ProvenanceError,
    VerifiedContextError,
)
from app.ai.context.models import (
    DEFAULT_VERIFIED_CONTEXT_SYSTEM_PROMPT,
    AIExplanationRequest,
    AIGeneratedExplanation,
    FactProvenance,
    GrowthClass,
    PriorityTier,
    SkillClassification,
    VerifiedCandidateContext,
    VerifiedContext,
    VerifiedEvidenceFact,
    VerifiedMarketFact,
    VerifiedPriorityFact,
    VerifiedSkillFact,
)
from app.ai.context.validation import (
    MAX_EVIDENCE_LIMIT,
    MAX_MARKET_LIMIT,
    MAX_PRIORITIES_LIMIT,
    MAX_SKILLS_LIMIT,
    MAX_SNIPPET_LENGTH,
    MAX_TOTAL_FACTS_LIMIT,
    validate_verified_context,
)

__all__ = [
    # Enums
    "FactProvenance",
    "SkillClassification",
    "PriorityTier",
    "GrowthClass",
    # Verified Fact Models
    "VerifiedCandidateContext",
    "VerifiedSkillFact",
    "VerifiedEvidenceFact",
    "VerifiedMarketFact",
    "VerifiedPriorityFact",
    "VerifiedContext",
    # AI Contracts
    "DEFAULT_VERIFIED_CONTEXT_SYSTEM_PROMPT",
    "AIExplanationRequest",
    "AIGeneratedExplanation",
    # Validation & Limits
    "validate_verified_context",
    "MAX_SKILLS_LIMIT",
    "MAX_EVIDENCE_LIMIT",
    "MAX_MARKET_LIMIT",
    "MAX_PRIORITIES_LIMIT",
    "MAX_TOTAL_FACTS_LIMIT",
    "MAX_SNIPPET_LENGTH",
    # Exceptions
    "VerifiedContextError",
    "ContextValidationError",
    "ContextImmutabilityError",
    "ProvenanceError",
]
