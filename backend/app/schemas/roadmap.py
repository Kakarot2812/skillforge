"""
Typed contracts and Pydantic schemas for Post-MVP Checkpoint P4:
Personalized Roadmap + Resources.

Enforces:
- Strict immutability and schema restrictions (frozen=True, extra="forbid").
- Deeply typed collections (Tuple instead of mutable List).
- Distinct representations for persisted (authenticated) vs in-memory (anonymous) roadmaps.
- Prerequisite distinction: HARD vs RECOMMENDED.
- Transitive-only prerequisite scoring: priority_score and priority_level are Optional and None.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from pydantic import BaseModel, ConfigDict, Field, field_validator


class DependencyType(str, Enum):
    """Prerequisite dependency classification."""
    HARD = "HARD"
    RECOMMENDED = "RECOMMENDED"


class MilestoneStatus(str, Enum):
    """
    Milestone execution lifecycle.
    P4 initializes milestones strictly to NOT_STARTED.
    VERIFIED is reserved for P5 GitHub verification.
    """
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFIED = "VERIFIED"


class RoadmapLifecycleStatus(str, Enum):
    """Overall candidate roadmap status."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


# ---------------------------------------------------------------------------
# Immutable Milestone Component Models
# ---------------------------------------------------------------------------

class RoadmapPrerequisiteItem(BaseModel):
    """Represents a prerequisite dependency constraint for a milestone skill."""
    skill_id: UUID = Field(..., description="Canonical UUID of the prerequisite skill")
    skill_name: str = Field(..., description="Human-readable name of the prerequisite skill")
    canonical_slug: str = Field(..., description="Slug of the prerequisite skill")
    dependency_type: DependencyType = Field(..., description="HARD (blocking) or RECOMMENDED (non-blocking)")
    is_satisfied: bool = Field(..., description="Whether the candidate already possesses STRONG verified evidence for this skill")

    model_config = ConfigDict(frozen=True, extra="forbid")


class RoadmapResourceItem(BaseModel):
    """Represents an explicitly approved, curated learning resource."""
    id: UUID = Field(..., description="Database UUID of the approved resource")
    title: str = Field(..., description="Curated resource title")
    url: str = Field(..., description="Whitelisted approved resource URL")
    resource_type: str = Field(..., description="Type of resource (OFFICIAL_DOCS, TUTORIAL, GUIDE, etc.)")
    provider: str = Field(..., description="Authoritative publisher or provider")
    difficulty: str = Field(..., description="Difficulty tier: BEGINNER, INTERMEDIATE, ADVANCED")
    estimated_minutes: Optional[int] = Field(None, ge=0, description="Estimated reading or exercise duration")

    model_config = ConfigDict(frozen=True, extra="forbid")


class RoadmapProjectItem(BaseModel):
    """Represents an approved practical hands-on engineering project."""
    id: UUID = Field(..., description="Database UUID of the approved project")
    title: str = Field(..., description="Curated project title")
    description: str = Field(..., description="Engineering project brief and instructions")
    difficulty: str = Field(..., description="Difficulty tier: BEGINNER, INTERMEDIATE, ADVANCED")
    deliverables: Tuple[str, ...] = Field(default_factory=tuple, description="Expected code and config file deliverables")
    verification_criteria: Tuple[str, ...] = Field(default_factory=tuple, description="Criteria for P5 GitHub verification inspection")
    estimated_hours: Optional[int] = Field(None, ge=0, description="Estimated project implementation effort in hours")

    model_config = ConfigDict(frozen=True, extra="forbid")


class RoadmapMilestoneItem(BaseModel):
    """
    Immutable representation of an ordered milestone in the candidate's learning roadmap.
    Enforces deterministic sorting, transparent scoring, and clear prerequisite grounding.
    """
    milestone_id: Optional[UUID] = Field(None, description="Database UUID if persisted; None if in-memory anonymous")
    order_index: int = Field(..., ge=1, description="1-indexed sequence order in the roadmap")
    skill_id: UUID = Field(..., description="Canonical skill UUID")
    skill_name: str = Field(..., description="Canonical skill name")
    canonical_slug: str = Field(..., description="Taxonomy lookup slug")
    category: Optional[str] = Field(None, description="Taxonomy category")
    gap_status: str = Field(..., description="Actionable gap classification: MISSING or PARTIAL")
    demonstrated_score: float = Field(0.0, ge=0.0, le=1.0, description="Candidate code demonstrated score")
    demand_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Market demand score if directly demanded; None if transitive-only prerequisite")
    growth_rate: Optional[float] = Field(None, description="Market growth rate if directly demanded; None if transitive-only prerequisite")
    priority_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Deterministic priority score if directly demanded; None if transitive-only prerequisite")
    priority_level: Optional[str] = Field(None, description="Priority level (HIGH, MEDIUM, LOW); None if transitive-only prerequisite")
    is_transitive_prerequisite: bool = Field(False, description="True if scheduled dynamically as a dependency rather than a direct role requirement")
    reason: str = Field(..., description="Deterministic explanation of why this milestone appears at this sequence position")
    prerequisites: Tuple[RoadmapPrerequisiteItem, ...] = Field(default_factory=tuple, description="Prerequisite skills for this milestone")
    learning_objectives: Tuple[str, ...] = Field(default_factory=tuple, description="Actionable learning competencies")
    resources: Tuple[RoadmapResourceItem, ...] = Field(default_factory=tuple, description="Curated approved resources")
    project: Optional[RoadmapProjectItem] = Field(None, description="Approved practical project challenge")
    status: MilestoneStatus = Field(MilestoneStatus.NOT_STARTED, description="Milestone lifecycle state. P4 strictly initializes to NOT_STARTED")

    model_config = ConfigDict(frozen=True, extra="forbid")


class CanonicalRoadmapData(BaseModel):
    """
    Immutable container representing the complete, ordered canonical roadmap.
    Fully functional and authoritative without any LLM invocation.
    """
    id: Optional[UUID] = Field(None, description="Database UUID if persisted; None if in-memory anonymous")
    user_id: Optional[UUID] = Field(None, description="Authenticated candidate user UUID; None if in-memory anonymous")
    role_id: UUID = Field(..., description="Target job role UUID")
    target_role_title: str = Field(..., description="Target job role title")
    location: str = Field("India", description="Geographic hiring market")
    status: RoadmapLifecycleStatus = Field(RoadmapLifecycleStatus.ACTIVE, description="Lifecycle status")
    roadmap_version: str = Field("v1", description="Roadmap algorithm version")
    persisted: bool = Field(..., description="True if saved to database; False if generated in-memory for anonymous session")
    total_milestones: int = Field(..., ge=0, description="Total milestone count")
    high_priority_count: int = Field(0, ge=0, description="High priority milestone count")
    medium_priority_count: int = Field(0, ge=0, description="Medium priority milestone count")
    low_priority_count: int = Field(0, ge=0, description="Low priority milestone count")
    transitive_prerequisite_count: int = Field(0, ge=0, description="Milestones added strictly as foundational prerequisites")
    milestones: Tuple[RoadmapMilestoneItem, ...] = Field(default_factory=tuple, description="Sequenced milestones")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of generation")

    model_config = ConfigDict(frozen=True, extra="forbid")


# ---------------------------------------------------------------------------
# API Request & Response Contracts
# ---------------------------------------------------------------------------

class RoadmapGenerateRequest(BaseModel):
    """Input payload for generating a deterministic career roadmap."""
    role_id: UUID = Field(..., description="Target canonical job role UUID")
    location: str = Field(default="India", min_length=1, max_length=64, description="Market location")
    user_id: Optional[UUID] = Field(None, description="Candidate user UUID (subject to authorization validation)")
    resume_id: Optional[UUID] = Field(None, description="Scoped resume UUID (must be owned by candidate)")
    include_resume: bool = Field(True, description="Whether to incorporate resume claims")
    include_github: bool = Field(True, description="Whether to incorporate GitHub code demonstration")
    github_username: Optional[str] = Field(None, max_length=128, description="GitHub username (must belong to candidate)")

    model_config = ConfigDict(extra="forbid")

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("location cannot be blank or whitespace.")
        return v.strip()


class RoadmapResponse(BaseModel):
    """Standard response envelope for generated or retrieved canonical roadmaps."""
    data: CanonicalRoadmapData
    meta: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class AIRoadmapExplainRequest(BaseModel):
    """Request for generating non-authoritative natural language guidance over a canonical roadmap."""
    user_query: Optional[str] = Field(None, max_length=1000, description="Optional candidate focus question")
    temperature: float = Field(0.2, ge=0.0, le=1.0, description="Generation temperature")

    model_config = ConfigDict(extra="forbid")


class AIRoadmapExplainResponse(BaseModel):
    """Typed explanatory response generated by Qwen over the canonical roadmap."""
    roadmap_id: Optional[UUID] = Field(None, description="Associated roadmap UUID")
    target_role_title: str = Field(..., description="Target career role")
    content: str = Field(..., description="Generated natural language explanation/strategy")
    model: str = Field("qwen3:8b", description="Model used for explanation")
    status: str = Field("EXPLANATORY", description="Explicit marker indicating non-authoritative explanatory text")
    referenced_skill_slugs: Tuple[str, ...] = Field(default_factory=tuple, description="Canonical skill slugs mentioned")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(frozen=True, extra="forbid")


class ApprovedResourceListResponse(BaseModel):
    """Response envelope for approved resources query."""
    skill_id: UUID
    skill_name: str
    total_resources: int
    resources: Tuple[RoadmapResourceItem, ...]

    model_config = ConfigDict(extra="forbid")
