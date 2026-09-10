"""
Deterministic validation for SkillForge AI Verified Context Contract.
Post-MVP Phase 2, Checkpoint P2-B.

Validates that all facts supplied to Qwen conform to strict schema, range,
provenance, and consistency constraints BEFORE any LLM invocation.

Core architectural principle:
    "Deterministic systems decide what is true."
    Validation is strictly programmatic and deterministic. Qwen does NOT validate.
"""

from typing import Dict, Optional, Set
from uuid import UUID

from app.ai.context.exceptions import ContextValidationError, ProvenanceError
from app.ai.context.models import (
    FactProvenance,
    GrowthClass,
    PriorityTier,
    SkillClassification,
    VerifiedContext,
    VerifiedEvidenceFact,
    VerifiedMarketFact,
    VerifiedPriorityFact,
    VerifiedSkillFact,
)

# Context size bounds to prevent prompt-injection or resource exhaustion
MAX_SKILLS_LIMIT = 100
MAX_EVIDENCE_LIMIT = 250
MAX_MARKET_LIMIT = 100
MAX_PRIORITIES_LIMIT = 100
MAX_TOTAL_FACTS_LIMIT = 500
MAX_SNIPPET_LENGTH = 2000


def validate_verified_context(context: VerifiedContext) -> None:
    """
    Deterministically validates a VerifiedContext instance.

    Raises:
        ContextValidationError: If any fact fails range, schema, size, or consistency rules.
        ProvenanceError: If any fact lacks valid deterministic provenance.
    """
    if not isinstance(context, VerifiedContext):
        raise ContextValidationError(
            f"Expected VerifiedContext instance, received {type(context).__name__}."
        )

    # 1. Non-empty check: at least one verified fact must be present
    if context.total_facts_count == 0:
        raise ContextValidationError(
            "Verified context cannot be empty. At least one verified candidate, skill, evidence, or market fact is required."
        )

    # 2. Context bounds check (prevents unbounded dumping into the prompt)
    if len(context.skills) > MAX_SKILLS_LIMIT:
        raise ContextValidationError(
            f"Context skills count ({len(context.skills)}) exceeds maximum allowed bound of {MAX_SKILLS_LIMIT}.",
            field_name="skills",
        )

    if len(context.evidence) > MAX_EVIDENCE_LIMIT:
        raise ContextValidationError(
            f"Context evidence count ({len(context.evidence)}) exceeds maximum allowed bound of {MAX_EVIDENCE_LIMIT}.",
            field_name="evidence",
        )

    if len(context.market) > MAX_MARKET_LIMIT:
        raise ContextValidationError(
            f"Context market count ({len(context.market)}) exceeds maximum allowed bound of {MAX_MARKET_LIMIT}.",
            field_name="market",
        )

    if len(context.priorities) > MAX_PRIORITIES_LIMIT:
        raise ContextValidationError(
            f"Context priorities count ({len(context.priorities)}) exceeds maximum allowed bound of {MAX_PRIORITIES_LIMIT}.",
            field_name="priorities",
        )

    if context.total_facts_count > MAX_TOTAL_FACTS_LIMIT:
        raise ContextValidationError(
            f"Total context facts count ({context.total_facts_count}) exceeds maximum allowed bound of {MAX_TOTAL_FACTS_LIMIT}."
        )

    # 3. Candidate Context Validation
    if context.candidate:
        if not isinstance(context.candidate.provenance, FactProvenance):
            raise ProvenanceError("Candidate context lacks valid FactProvenance.")
        if context.candidate.location and not context.candidate.location.strip():
            raise ContextValidationError("Candidate location cannot be blank whitespace.", field_name="candidate.location")

    # 4. Skill Facts Validation
    skill_map: Dict[UUID, VerifiedSkillFact] = {}
    for idx, skill in enumerate(context.skills):
        if not isinstance(skill, VerifiedSkillFact):
            raise ContextValidationError(f"Invalid skill fact type at index {idx}: {type(skill).__name__}.")

        if not skill.skill_name or not skill.skill_name.strip():
            raise ContextValidationError(f"Skill fact at index {idx} has empty skill_name.", field_name="skill_name")

        if not skill.canonical_slug or not skill.canonical_slug.strip():
            raise ContextValidationError(f"Skill fact at index {idx} has empty canonical_slug.", field_name="canonical_slug")

        if not isinstance(skill.classification, SkillClassification):
            raise ContextValidationError(f"Invalid classification for skill '{skill.skill_name}': {skill.classification}.")

        if not (0.0 <= skill.demonstrated_score <= 1.0):
            raise ContextValidationError(f"demonstrated_score for skill '{skill.skill_name}' must be in [0.0, 1.0].")

        if not (0.0 <= skill.claim_confidence <= 1.0):
            raise ContextValidationError(f"claim_confidence for skill '{skill.skill_name}' must be in [0.0, 1.0].")

        if not isinstance(skill.provenance, FactProvenance):
            raise ProvenanceError(f"Skill fact '{skill.skill_name}' lacks valid FactProvenance.")

        skill_map[skill.skill_id] = skill

    # 5. Evidence Facts Validation
    for idx, ev in enumerate(context.evidence):
        if not isinstance(ev, VerifiedEvidenceFact):
            raise ContextValidationError(f"Invalid evidence fact type at index {idx}: {type(ev).__name__}.")

        if not ev.skill_name or not ev.skill_name.strip():
            raise ContextValidationError(f"Evidence fact at index {idx} has empty skill_name.", field_name="skill_name")

        if not ev.evidence_type or not ev.evidence_type.strip():
            raise ContextValidationError(f"Evidence fact at index {idx} has empty evidence_type.", field_name="evidence_type")

        if not isinstance(ev.source, FactProvenance):
            raise ProvenanceError(f"Evidence fact '{ev.evidence_type}' lacks valid FactProvenance.")

        if ev.snippet and len(ev.snippet) > MAX_SNIPPET_LENGTH:
            raise ContextValidationError(
                f"Evidence snippet for '{ev.skill_name}' exceeds maximum allowed length of {MAX_SNIPPET_LENGTH} characters.",
                field_name="snippet",
            )

        if not (0.0 <= ev.confidence_score <= 1.0):
            raise ContextValidationError(f"confidence_score for evidence '{ev.evidence_type}' must be in [0.0, 1.0].")

    # 6. Market Facts Validation
    market_map: Dict[UUID, VerifiedMarketFact] = {}
    for idx, mkt in enumerate(context.market):
        if not isinstance(mkt, VerifiedMarketFact):
            raise ContextValidationError(f"Invalid market fact type at index {idx}: {type(mkt).__name__}.")

        if not mkt.skill_name or not mkt.skill_name.strip():
            raise ContextValidationError(f"Market fact at index {idx} has empty skill_name.", field_name="skill_name")

        if not (0.0 <= mkt.demand_score <= 1.0):
            raise ContextValidationError(f"demand_score for market fact '{mkt.skill_name}' must be in [0.0, 1.0].")

        if mkt.demand_share is not None and not (0.0 <= mkt.demand_share <= 1.0):
            raise ContextValidationError(f"demand_share for market fact '{mkt.skill_name}' must be in [0.0, 1.0].")

        if not isinstance(mkt.growth_class, GrowthClass):
            raise ContextValidationError(f"Invalid growth_class for market fact '{mkt.skill_name}': {mkt.growth_class}.")

        if not isinstance(mkt.provenance, FactProvenance):
            raise ProvenanceError(f"Market fact '{mkt.skill_name}' lacks valid FactProvenance.")

        market_map[mkt.skill_id] = mkt

    # 7. Priority Facts & Cross-Fact Consistency Validation
    for idx, prio in enumerate(context.priorities):
        if not isinstance(prio, VerifiedPriorityFact):
            raise ContextValidationError(f"Invalid priority fact type at index {idx}: {type(prio).__name__}.")

        if not prio.skill_name or not prio.skill_name.strip():
            raise ContextValidationError(f"Priority fact at index {idx} has empty skill_name.", field_name="skill_name")

        if not (0.0 <= prio.priority_score <= 1.0):
            raise ContextValidationError(f"priority_score for '{prio.skill_name}' must be in [0.0, 1.0].")

        if not isinstance(prio.priority_level, PriorityTier):
            raise ContextValidationError(f"Invalid priority_level for '{prio.skill_name}': {prio.priority_level}.")

        if not isinstance(prio.gap_status, SkillClassification):
            raise ContextValidationError(f"Invalid gap_status for '{prio.skill_name}': {prio.gap_status}.")

        if not (0.0 <= prio.demand_score <= 1.0):
            raise ContextValidationError(f"demand_score for priority '{prio.skill_name}' must be in [0.0, 1.0].")

        if not (0.0 <= prio.demonstrated_score <= 1.0):
            raise ContextValidationError(f"demonstrated_score for priority '{prio.skill_name}' must be in [0.0, 1.0].")

        if not isinstance(prio.provenance, FactProvenance):
            raise ProvenanceError(f"Priority fact '{prio.skill_name}' lacks valid FactProvenance.")

        # Cross-fact consistency check:
        # If skill is present in both skills and priorities, their gap_status must match
        if prio.skill_id in skill_map:
            matched_skill = skill_map[prio.skill_id]
            if prio.gap_status != matched_skill.classification:
                raise ContextValidationError(
                    f"Contradictory gap status for skill '{prio.skill_name}': "
                    f"skills fact asserts '{matched_skill.classification.value}', but priorities fact asserts '{prio.gap_status.value}'."
                )

        # If skill is present in both market and priorities, their demand_score must match
        if prio.skill_id in market_map:
            matched_market = market_map[prio.skill_id]
            if abs(prio.demand_score - matched_market.demand_score) > 1e-4:
                raise ContextValidationError(
                    f"Contradictory demand_score for skill '{prio.skill_name}': "
                    f"market fact asserts {matched_market.demand_score}, but priorities fact asserts {prio.demand_score}."
                )
