"""
Verified Context Contract models for SkillForge AI.
Post-MVP Phase 2, Checkpoint P2-B.

Enforces the core architectural boundary:
    "The LLM never decides what is true."
    "Deterministic systems decide what is true.
     AI explains, reasons over, and personalizes verified evidence."

All models representing verified facts are strictly frozen (immutable)
and disallow arbitrary untyped attributes (extra='forbid').
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class FactProvenance(str, Enum):
    """Authoritative deterministic origin of a verified fact."""
    RESUME = "RESUME"
    GITHUB = "GITHUB"
    MARKET = "MARKET"
    DETERMINISTIC_ANALYSIS = "DETERMINISTIC_ANALYSIS"


class SkillClassification(str, Enum):
    """Deterministic skill possession status."""
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"


class PriorityTier(str, Enum):
    """Deterministic candidate gap prioritization tier."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class GrowthClass(str, Enum):
    """Deterministic market demand growth category."""
    RISING = "RISING"
    STABLE = "STABLE"
    DECLINING = "DECLINING"


# ---------------------------------------------------------------------------
# Immutable Verified Fact Models
# ---------------------------------------------------------------------------

class VerifiedCandidateContext(BaseModel):
    """
    Immutable representation of candidate analysis scope.
    Originated exclusively from verified database entities.
    """
    candidate_id: Optional[UUID] = Field(None, description="Candidate UUID if available")
    target_role_id: Optional[UUID] = Field(None, description="Target job role UUID")
    target_role_name: Optional[str] = Field(None, description="Target job role title")
    location: str = Field("India", description="Geographic evaluation market")
    has_resume: bool = Field(False, description="Whether resume evidence was analyzed")
    has_github: bool = Field(False, description="Whether GitHub evidence was analyzed")
    provenance: FactProvenance = Field(FactProvenance.DETERMINISTIC_ANALYSIS, description="Fact origin")

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerifiedSkillFact(BaseModel):
    """
    Immutable representation of a deterministically classified skill gap.
    Qwen is strictly prohibited from altering classification or scores.
    """
    skill_id: UUID = Field(..., description="Canonical UUID referencing skills(id)")
    skill_name: str = Field(..., description="Human-readable canonical skill name")
    canonical_slug: str = Field(..., description="Taxonomy lookup slug")
    classification: SkillClassification = Field(..., description="Deterministic status: STRONG, PARTIAL, MISSING")
    category: Optional[str] = Field(None, description="Taxonomy category")
    demonstrated_score: float = Field(0.0, ge=0.0, le=1.0, description="Aggregated code demonstration score [0, 1]")
    claimed: bool = Field(False, description="Whether claimed in candidate resume")
    claim_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Resume claim confidence [0, 1]")
    evidence_count: int = Field(0, ge=0, description="Verified code artifact count")
    evidence_level: Optional[str] = Field(None, description="Evidence level (HIGH, MEDIUM, LOW)")
    provenance: FactProvenance = Field(FactProvenance.DETERMINISTIC_ANALYSIS, description="Fact origin")

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerifiedEvidenceFact(BaseModel):
    """
    Immutable representation of concrete, verified evidence artifacts.
    Constrained to controlled snippets; whole repository/document dumping is prohibited.
    """
    skill_id: UUID = Field(..., description="Associated canonical skill UUID")
    skill_name: str = Field(..., description="Canonical skill name")
    source: FactProvenance = Field(..., description="Originating source: RESUME, GITHUB, MARKET")
    evidence_type: str = Field(..., description="Concrete artifact type (e.g. dependency_manifest, dockerfile, ci_workflow)")
    evidence_id: Optional[UUID] = Field(None, description="Database evidence UUID")
    artifact_path: Optional[str] = Field(None, description="File path relative to repository or document")
    repo_name: Optional[str] = Field(None, description="Repository identifier if from GitHub")
    snippet: Optional[str] = Field(None, max_length=2000, description="Bounded text snippet context (max 2000 chars)")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Evidence extraction confidence")
    evidence_tier: Optional[str] = Field(None, description="Evidence tier tier (HIGH, MEDIUM, LOW)")

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerifiedMarketFact(BaseModel):
    """
    Immutable representation of market demand and historical growth signals.
    Originated from deterministic P1 market intelligence (market_skill_demand & growth).
    """
    skill_id: UUID = Field(..., description="Canonical skill UUID")
    skill_name: str = Field(..., description="Canonical skill name")
    source: str = Field("adzuna", description="Data provider namespace")
    demand_score: float = Field(..., ge=0.0, le=1.0, description="Empirical market demand score [0.0, 1.0]")
    demand_share: Optional[float] = Field(None, ge=0.0, le=1.0, description="Raw demand proportion [0.0, 1.0]")
    growth_rate: float = Field(0.0, description="Deterministic historical growth rate")
    growth_class: GrowthClass = Field(GrowthClass.STABLE, description="Classification: RISING, STABLE, DECLINING")
    sample_size: Optional[int] = Field(None, ge=0, description="Market job sample size evaluated")
    snapshot_at: Optional[datetime] = Field(None, description="Snapshot timestamp")
    provenance: FactProvenance = Field(FactProvenance.MARKET, description="Fact origin")

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerifiedPriorityFact(BaseModel):
    """
    Immutable representation of a deterministically prioritized skill gap.
    Qwen is strictly prohibited from recalculating priority scores or tiers.
    """
    skill_id: UUID = Field(..., description="Canonical skill UUID")
    skill_name: str = Field(..., description="Canonical skill name")
    priority_score: float = Field(..., ge=0.0, le=1.0, description="Deterministic priority score [0.0, 1.0]")
    priority_level: PriorityTier = Field(..., description="Priority tier: HIGH, MEDIUM, LOW")
    gap_status: SkillClassification = Field(..., description="Gap classification: STRONG, PARTIAL, MISSING")
    demand_score: float = Field(..., ge=0.0, le=1.0, description="Input market demand score")
    growth_rate: float = Field(0.0, description="Input growth rate")
    demonstrated_score: float = Field(0.0, ge=0.0, le=1.0, description="Input demonstrated score")
    scoring_version: str = Field("v1", description="Prioritization algorithm version")
    provenance: FactProvenance = Field(FactProvenance.DETERMINISTIC_ANALYSIS, description="Fact origin")

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerifiedContext(BaseModel):
    """
    Immutable aggregate container for all verified facts supplied to Qwen.
    Represents the ground truth established by deterministic SkillForge systems.
    Arbitrary untyped dictionaries and unverified claims are strictly forbidden.
    """
    candidate: Optional[VerifiedCandidateContext] = Field(None, description="Candidate and role scope")
    skills: Tuple[VerifiedSkillFact, ...] = Field(default_factory=tuple, description="Verified skill gap facts")
    evidence: Tuple[VerifiedEvidenceFact, ...] = Field(default_factory=tuple, description="Verified concrete evidence facts")
    market: Tuple[VerifiedMarketFact, ...] = Field(default_factory=tuple, description="Verified market demand facts")
    priorities: Tuple[VerifiedPriorityFact, ...] = Field(default_factory=tuple, description="Verified prioritization facts")
    context_id: Optional[UUID] = Field(None, description="Audit tracking UUID")
    created_at: Optional[datetime] = Field(None, description="Context assembly timestamp")
    provenance: FactProvenance = Field(FactProvenance.DETERMINISTIC_ANALYSIS, description="Container origin")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @property
    def total_facts_count(self) -> int:
        """Returns total discrete verified facts in this context."""
        return (
            (1 if self.candidate else 0)
            + len(self.skills)
            + len(self.evidence)
            + len(self.market)
            + len(self.priorities)
        )


# ---------------------------------------------------------------------------
# AI Request & Response Contracts (Strictly Decoupled from Verified Facts)
# ---------------------------------------------------------------------------

DEFAULT_VERIFIED_CONTEXT_SYSTEM_PROMPT = (
    "You are an evidence-based career intelligence explanation engine for SkillForge AI.\n"
    "The supplied context contains authoritative, verified facts derived deterministically "
    "from candidate resume analysis, GitHub code artifact inspection, and market demand intelligence.\n"
    "Core boundary invariants:\n"
    "1. The LLM never decides what is true. The supplied context is absolute ground truth.\n"
    "2. Never invent, modify, or contradict any verified fact (skill classification, scores, priorities).\n"
    "3. Do not infer unverified skills or extrapolate evidence not present in the verified context.\n"
    "4. If the supplied context lacks sufficient information to answer a query, state clearly that "
    "the verified evidence is unavailable.\n"
    "5. Your role is solely to explain, reason over, and personalize the verified evidence."
)


class AIExplanationRequest(BaseModel):
    """
    Typed request envelope passed to the AI explanation layer.
    Requires validated, immutable VerifiedContext as input.
    """
    context: VerifiedContext = Field(..., description="Validated immutable verified context")
    user_prompt: str = Field(..., min_length=1, description="Candidate question or explanation query")
    system_instruction: str = Field(
        default=DEFAULT_VERIFIED_CONTEXT_SYSTEM_PROMPT,
        description="Boundary system instruction enforcing fact adherence",
    )
    temperature: float = Field(default=0.2, ge=0.0, le=1.0, description="Sampling temperature for explanation")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Ollama runtime options")

    model_config = ConfigDict(frozen=True, extra="forbid")


class AIGeneratedExplanation(BaseModel):
    """
    Typed response representing non-authoritative text generated by Qwen.
    Explicitly separated from verified facts.
    Cannot overwrite or be inserted back into VerifiedContext.
    """
    content: str = Field(..., description="Generated natural-language explanation text")
    model: str = Field("qwen3:8b", description="Model identifier used for generation")
    done: bool = Field(True, description="Whether generation completed successfully")
    done_reason: Optional[str] = Field(None, description="Termination reason (e.g. stop)")
    referenced_skill_ids: List[UUID] = Field(
        default_factory=list,
        description="Skill UUIDs referenced in explanation (pointers to input facts, not newly asserted facts)",
    )
    status: str = Field(
        "EXPLANATORY",
        description="Explicit marker identifying output as explanatory text, never verified fact",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Operational audit metadata")

    model_config = ConfigDict(frozen=True, extra="forbid")
