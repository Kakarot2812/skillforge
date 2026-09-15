"""
Verified Roadmap PDF Context Models for SkillForge AI.
Post-MVP Career Roadmap PDF Feature (Phase 2).

Core Architectural Invariants:
- "The LLM never decides what is true."
- "Deterministic systems decide what is true.
   AI explains, reasons over, and personalizes verified evidence."
- All models representing verified ground-truth facts are strictly frozen (immutable)
  and disallow arbitrary untyped attributes (extra='forbid').
- Clear separation between authoritative analysis (readiness, gaps, priority, sequencing)
  and supporting context (curated resources, curated project challenges).
- Curated projects are recommended engineering challenges, NOT candidate proof of skill.
"""

from datetime import datetime
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class EvidenceStatusType(str, Enum):
    """Classification of candidate evidence vs curated recommendation."""
    CLAIMED = "CLAIMED"
    DEMONSTRATED = "DEMONSTRATED"
    VERIFIED = "VERIFIED"


class SkillGapClassification(str, Enum):
    """Deterministic gap classification."""
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"


class PriorityTierLevel(str, Enum):
    """Deterministic priority category."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ---------------------------------------------------------------------------
# Section A: Candidate Profile Context
# ---------------------------------------------------------------------------

class VerifiedCandidateProfile(BaseModel):
    """
    Immutable candidate identity and educational context.
    Strictly populated from existing User and UserProfile records.
    Missing fields remain None; values are NEVER fabricated.
    """
    user_id: UUID = Field(..., description="Canonical user UUID")
    email: str = Field(..., description="Candidate contact email")
    name: Optional[str] = Field(None, description="Full candidate name if available")
    target_role: Optional[str] = Field(None, description="Candidate stated target career role")
    experience_level: Optional[str] = Field(None, description="Experience tier if available")
    college: Optional[str] = Field(None, description="College/University name if available")
    degree: Optional[str] = Field(None, description="Degree name if available")
    branch: Optional[str] = Field(None, description="Academic branch/major if available")
    semester: Optional[int] = Field(None, description="Academic semester if available")
    education: Optional[str] = Field(None, description="Education summary if available")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section B: Deterministic Readiness Metrics
# ---------------------------------------------------------------------------

class VerifiedReadinessMetrics(BaseModel):
    """
    Immutable deterministic readiness metrics derived from canonical SkillGapService.
    Readiness percentage is calculated strictly as:
    round((strong_count / total_required_skills) * 100) if total_required_skills > 0 else 0
    """
    readiness_percentage: int = Field(..., ge=0, le=100, description="Readiness percentage [0, 100]")
    total_required_skills: int = Field(..., ge=0, description="Total demanded skills for target role")
    strong_count: int = Field(..., ge=0, description="Count of STRONG verified competencies")
    partial_count: int = Field(..., ge=0, description="Count of PARTIAL demonstrated/claimed competencies")
    missing_count: int = Field(..., ge=0, description="Count of MISSING competencies")
    has_resume: bool = Field(False, description="Whether resume evidence was evaluated")
    has_github: bool = Field(False, description="Whether GitHub code evidence was evaluated")
    scoring_version: str = Field("v1", description="Prioritization and gap scoring algorithm version")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section C: Skill Gap Facts
# ---------------------------------------------------------------------------

class VerifiedSkillGapFact(BaseModel):
    """
    Immutable representation of a deterministically classified skill gap.
    Values are derived directly from SkillGapService; LLMs cannot alter these.
    """
    skill_id: UUID = Field(..., description="Canonical skill UUID")
    skill_name: str = Field(..., description="Canonical skill name")
    canonical_slug: str = Field(..., description="Taxonomy lookup slug")
    category: Optional[str] = Field(None, description="Skill taxonomy category")
    gap_status: SkillGapClassification = Field(..., description="STRONG, PARTIAL, or MISSING")
    claimed: bool = Field(False, description="Whether claimed in resume")
    claim_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Resume claim confidence")
    demonstrated: bool = Field(False, description="Whether demonstrated in GitHub code artifacts")
    demonstrated_score: float = Field(0.0, ge=0.0, le=1.0, description="Multi-repository demonstrated code score")
    evidence_level: Optional[str] = Field(None, description="HIGH, MEDIUM, LOW evidence tier")
    evidence_count: int = Field(0, ge=0, description="Total verified code artifacts count")
    demand_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Industry demand score [0.0, 1.0]")
    growth_rate: Optional[float] = Field(None, description="YoY market growth rate")
    priority_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Deterministic priority score")
    priority_level: Optional[PriorityTierLevel] = Field(None, description="Priority category (HIGH, MEDIUM, LOW)")
    deterministic_explanation: Optional[str] = Field(None, description="Rule-based deterministic explanation")

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerifiedPrioritizedGapsSummary(BaseModel):
    """
    Immutable summary of actionable gaps (MISSING and PARTIAL only).
    Ordered deterministically by priority score DESC, status rank, demand DESC.
    """
    total_actionable_gaps: int = Field(..., ge=0, description="Sum of MISSING + PARTIAL gaps")
    high_priority_count: int = Field(..., ge=0, description="Count of HIGH priority gaps (score >= 0.67)")
    medium_priority_count: int = Field(..., ge=0, description="Count of MEDIUM priority gaps (0.34 <= score < 0.67)")
    low_priority_count: int = Field(..., ge=0, description="Count of LOW priority gaps (score < 0.34)")
    top_gaps: Tuple[VerifiedSkillGapFact, ...] = Field(
        default_factory=tuple,
        description="Deterministically ordered prioritized actionable gaps"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section D: Industry Demand Evidence (Supporting Context)
# ---------------------------------------------------------------------------

class VerifiedMarketDemandFact(BaseModel):
    """
    Immutable representation of empirical market demand for a skill.
    Supporting evidence; does not imply candidate skill possession.
    """
    skill_id: UUID = Field(..., description="Canonical skill UUID")
    skill_name: str = Field(..., description="Canonical skill name")
    canonical_slug: str = Field(..., description="Taxonomy lookup slug")
    demand_score: float = Field(..., ge=0.0, le=1.0, description="Empirical market demand score [0.0, 1.0]")
    growth_rate: float = Field(0.0, description="YoY market growth rate")
    growth_class: str = Field("STABLE", description="RISING, STABLE, or DECLINING")
    location: str = Field("India", description="Hiring market location")
    data_source: str = Field("adzuna", description="Data provider identifier")
    freshness: Optional[str] = Field(None, description="Data freshness date identifier")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section E: Curated Learning Resources & Projects (Supporting Context)
# ---------------------------------------------------------------------------

class VerifiedApprovedResource(BaseModel):
    """
    Curated, approved learning material originating strictly from approved_resources.
    Arbitrary URLs and hallucinated resources are strictly forbidden.
    """
    resource_id: UUID = Field(..., description="Database UUID referencing approved_resources.id")
    skill_id: UUID = Field(..., description="Associated canonical skill UUID")
    skill_name: str = Field(..., description="Associated skill name")
    title: str = Field(..., description="Curated resource title")
    url: str = Field(..., description="Whitelisted authoritative URL")
    resource_type: str = Field(..., description="OFFICIAL_DOCS, TUTORIAL, GUIDE, etc.")
    provider: str = Field(..., description="Authoritative publisher or provider")
    difficulty: str = Field(..., description="BEGINNER, INTERMEDIATE, or ADVANCED")
    estimated_minutes: Optional[int] = Field(None, ge=0, description="Estimated duration in minutes")
    is_approved: bool = Field(True, description="Strict approval flag")

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerifiedApprovedProject(BaseModel):
    """
    Curated practical engineering challenge from approved_projects.
    IMPORTANT: Curated projects are recommended practical challenges.
    They are NOT proof that the candidate possesses the skill.
    """
    project_id: UUID = Field(..., description="Database UUID referencing approved_projects.id")
    skill_id: UUID = Field(..., description="Associated canonical skill UUID")
    skill_name: str = Field(..., description="Associated skill name")
    title: str = Field(..., description="Project challenge title")
    description: str = Field(..., description="Engineering project brief")
    difficulty: str = Field(..., description="BEGINNER, INTERMEDIATE, or ADVANCED")
    deliverables: Tuple[str, ...] = Field(default_factory=tuple, description="Expected code deliverables")
    verification_criteria: Tuple[str, ...] = Field(default_factory=tuple, description="Verification criteria")
    estimated_hours: Optional[int] = Field(None, ge=0, description="Estimated effort in hours")
    role_id: Optional[UUID] = Field(None, description="Target job role UUID if role-scoped")
    is_curated_challenge: bool = Field(True, description="Always True for approved projects")
    is_candidate_proof: bool = Field(False, description="Always False: curated challenges are NOT candidate proof")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section F: Candidate Verification Evidence (Authoritative Proof)
# ---------------------------------------------------------------------------

class VerifiedCandidateEvidenceItem(BaseModel):
    """
    Concrete candidate evidence record (Claim, GitHub repository evidence, or Milestone verification).
    Explicitly distinguishes between claimed, demonstrated, and verified states.
    """
    evidence_id: UUID = Field(..., description="Database record UUID")
    skill_id: UUID = Field(..., description="Associated canonical skill UUID")
    skill_name: str = Field(..., description="Associated skill name")
    evidence_type: EvidenceStatusType = Field(..., description="CLAIMED, DEMONSTRATED, or VERIFIED")
    source: str = Field(..., description="RESUME, GITHUB, or MILESTONE_VERIFICATION")
    status: str = Field(..., description="Underlying verification status")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score if applicable")
    artifact_reference: Optional[str] = Field(None, description="Repository name, commit SHA, or resume file name")
    milestone_id: Optional[UUID] = Field(None, description="Associated roadmap milestone UUID if applicable")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Section G: Sequenced Roadmap Milestones
# ---------------------------------------------------------------------------

class VerifiedRoadmapPrerequisite(BaseModel):
    """Prerequisite dependency constraint for a roadmap milestone."""
    skill_id: UUID = Field(..., description="Prerequisite skill UUID")
    skill_name: str = Field(..., description="Prerequisite skill name")
    canonical_slug: str = Field(..., description="Prerequisite skill slug")
    dependency_type: str = Field(..., description="HARD or RECOMMENDED")
    is_satisfied: bool = Field(..., description="Whether candidate has verified STRONG evidence")

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerifiedRoadmapMilestoneContext(BaseModel):
    """
    Immutable representation of an ordered milestone in the candidate's learning roadmap.
    Preserves existing deterministic DAG topological sequencing and scoring.
    """
    milestone_id: Optional[UUID] = Field(None, description="Database UUID if persisted")
    order_index: int = Field(..., ge=1, description="1-indexed sequence order in the roadmap")
    skill_id: UUID = Field(..., description="Canonical skill UUID")
    skill_name: str = Field(..., description="Canonical skill name")
    canonical_slug: str = Field(..., description="Taxonomy lookup slug")
    category: Optional[str] = Field(None, description="Taxonomy category")
    gap_status: SkillGapClassification = Field(..., description="Actionable gap classification: MISSING or PARTIAL")
    priority_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Deterministic priority score")
    priority_level: Optional[PriorityTierLevel] = Field(None, description="Priority level (HIGH, MEDIUM, LOW)")
    is_transitive_prerequisite: bool = Field(False, description="Whether dynamically added as a prerequisite")
    deterministic_reason: str = Field(..., description="Deterministic explanation for milestone sequencing")
    status: str = Field("NOT_STARTED", description="Milestone lifecycle state (NOT_STARTED, IN_PROGRESS, COMPLETED, VERIFIED)")
    prerequisites: Tuple[VerifiedRoadmapPrerequisite, ...] = Field(default_factory=tuple, description="Prerequisite skills")
    learning_objectives: Tuple[str, ...] = Field(default_factory=tuple, description="Actionable learning competencies")
    resources: Tuple[VerifiedApprovedResource, ...] = Field(default_factory=tuple, description="Approved curated learning resources")
    project: Optional[VerifiedApprovedProject] = Field(None, description="Approved practical challenge")
    latest_verification: Optional[VerifiedCandidateEvidenceItem] = Field(None, description="Latest milestone verification audit record")

    model_config = ConfigDict(frozen=True, extra="forbid")


class VerifiedRoadmapSummary(BaseModel):
    """
    Immutable summary of the candidate's complete sequenced roadmap.
    Preserves canonical database ordering.
    """
    roadmap_id: UUID = Field(..., description="Candidate roadmap UUID")
    user_id: UUID = Field(..., description="Authenticated candidate user UUID")
    role_id: UUID = Field(..., description="Target job role UUID")
    target_role_title: str = Field(..., description="Target job role title")
    location: str = Field("India", description="Hiring market location")
    status: str = Field("ACTIVE", description="Roadmap lifecycle status (ACTIVE, COMPLETED, ARCHIVED)")
    roadmap_version: str = Field("v1", description="Roadmap algorithm version")
    total_milestones: int = Field(..., ge=0, description="Total milestone count")
    high_priority_count: int = Field(0, ge=0, description="High priority milestone count")
    medium_priority_count: int = Field(0, ge=0, description="Medium priority milestone count")
    low_priority_count: int = Field(0, ge=0, description="Low priority milestone count")
    transitive_prerequisite_count: int = Field(0, ge=0, description="Transitive-only prerequisite milestone count")
    milestones: Tuple[VerifiedRoadmapMilestoneContext, ...] = Field(
        default_factory=tuple,
        description="Ordered sequence of milestones"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# Root Container: Verified Roadmap PDF Context
# ---------------------------------------------------------------------------

def generate_deterministic_verification_hash(
    roadmap_id: UUID,
    user_id: UUID,
    role_id: UUID,
    target_role_title: str,
    readiness_percentage: int,
    strong_count: int,
    partial_count: int,
    missing_count: int,
    milestone_tuples: Tuple[Tuple[int, str, str, Optional[str]], ...],
) -> str:
    """
    Generates a deterministic SHA-256 hash over canonical verified context data.
    Guarantees:
    - Stable ordering
    - No timestamps generated during hashing
    - No random fields
    - Semantically identical input yields identical output
    """
    canonical_dict = {
        "roadmap_id": str(roadmap_id),
        "user_id": str(user_id),
        "role_id": str(role_id),
        "target_role_title": target_role_title.strip(),
        "readiness_percentage": readiness_percentage,
        "strong_count": strong_count,
        "partial_count": partial_count,
        "missing_count": missing_count,
        "milestones": [
            {
                "order": item[0],
                "skill_id": item[1],
                "gap_status": item[2],
                "priority_level": item[3],
            }
            for item in milestone_tuples
        ],
    }
    canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class VerifiedRoadmapPDFContext(BaseModel):
    """
    Complete immutable aggregate container for all verified facts supplied to Phase 3 Gemini.
    Represents the ground truth established by deterministic SkillForge systems.
    Zero LLM decisions, zero fabricated scores, zero unapproved resources.
    """
    schema_version: str = Field("v1.0", description="Context schema contract version")
    candidate: VerifiedCandidateProfile = Field(..., description="Candidate profile facts")
    readiness: VerifiedReadinessMetrics = Field(..., description="Deterministic readiness facts")
    prioritized_gaps: VerifiedPrioritizedGapsSummary = Field(..., description="Prioritized actionable gaps")
    all_gap_facts: Tuple[VerifiedSkillGapFact, ...] = Field(
        default_factory=tuple,
        description="Complete role competency gap facts"
    )
    roadmap: VerifiedRoadmapSummary = Field(..., description="Sequenced canonical roadmap facts")
    market_facts: Tuple[VerifiedMarketDemandFact, ...] = Field(
        default_factory=tuple,
        description="Market demand facts for demanded skills"
    )
    verification_evidence: Tuple[VerifiedCandidateEvidenceItem, ...] = Field(
        default_factory=tuple,
        description="Concrete candidate evidence facts"
    )
    weekly_hours_recommendation: Optional[int] = Field(
        None,
        description="Deterministic weekly hours recommendation. None if not configured; NEVER fabricated."
    )
    verification_hash: str = Field(
        ...,
        description="Deterministic SHA-256 hash over canonical facts ensuring context integrity"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
