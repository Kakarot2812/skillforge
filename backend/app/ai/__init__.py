"""
AI and LLM integration package for SkillForge AI.
Post-MVP Phase 2 (P2) local intelligence foundation.
"""

from app.ai.context import (
    DEFAULT_VERIFIED_CONTEXT_SYSTEM_PROMPT,
    AIExplanationRequest,
    AIGeneratedExplanation,
    ContextImmutabilityError,
    ContextValidationError,
    FactProvenance,
    GrowthClass,
    PriorityTier,
    ProvenanceError,
    SkillClassification,
    VerifiedCandidateContext,
    VerifiedContext,
    VerifiedContextError,
    VerifiedEvidenceFact,
    VerifiedMarketFact,
    VerifiedPriorityFact,
    VerifiedSkillFact,
    validate_verified_context,
)
from app.ai.qwen import (
    QwenAPIError,
    QwenChatResponse,
    QwenClient,
    QwenConfigurationError,
    QwenConnectionError,
    QwenError,
    QwenGenerateResponse,
    QwenHealthStatus,
    QwenMessage,
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
)

__all__ = [
    # Qwen Client (P2-A)
    "QwenClient",
    "QwenMessage",
    "QwenChatResponse",
    "QwenGenerateResponse",
    "QwenHealthStatus",
    "QwenError",
    "QwenConfigurationError",
    "QwenConnectionError",
    "QwenTimeoutError",
    "QwenAPIError",
    "QwenResponseError",
    "QwenModelNotFoundError",
    # Verified Context Contract (P2-B)
    "FactProvenance",
    "SkillClassification",
    "PriorityTier",
    "GrowthClass",
    "VerifiedCandidateContext",
    "VerifiedSkillFact",
    "VerifiedEvidenceFact",
    "VerifiedMarketFact",
    "VerifiedPriorityFact",
    "VerifiedContext",
    "DEFAULT_VERIFIED_CONTEXT_SYSTEM_PROMPT",
    "AIExplanationRequest",
    "AIGeneratedExplanation",
    "validate_verified_context",
    "VerifiedContextError",
    "ContextValidationError",
    "ContextImmutabilityError",
    "ProvenanceError",
]
