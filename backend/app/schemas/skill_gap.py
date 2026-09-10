from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.demand import JobRoleItem


class SkillGapItem(BaseModel):
    id: UUID
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    status: str = Field(description="Deterministic gap status: STRONG, PARTIAL, or MISSING")
    demand_score: float = Field(description="Database-derived industry demand score (0.0 - 1.0)")
    growth_rate: float = Field(description="Year-over-year industry growth rate")
    claimed: bool = Field(description="Whether the skill was claimed in candidate resume")
    claim_confidence: float = Field(description="Confidence score of resume claim")
    demonstrated: bool = Field(description="Whether the skill was demonstrated in GitHub code artifacts")
    demonstrated_score: float = Field(description="Aggregated multi-repository code evidence score")
    evidence_level: Optional[str] = Field(None, description="Demonstrated evidence tier: HIGH, MEDIUM, LOW")
    evidence_count: int = Field(0, description="Total verified code evidence artifacts")
    priority_score: Optional[float] = Field(None, description="Deterministic priority score (0.0 - 1.0)")
    priority_level: Optional[str] = Field(None, description="Priority category: HIGH, MEDIUM, LOW")
    scoring_version: Optional[str] = Field("v1", description="Prioritization scoring version")

    model_config = ConfigDict(from_attributes=True)


class SkillGapSummary(BaseModel):
    total_required_skills: int
    strong_count: int
    partial_count: int
    missing_count: int


class SkillGapResponseData(BaseModel):
    role: JobRoleItem
    location: str
    summary: SkillGapSummary
    skills: List[SkillGapItem]


class SkillGapMeta(BaseModel):
    user_id: Optional[UUID] = None
    location: str = "India"
    calculated_at: str
    data_freshness: str = "2026-09-01"
    scoring_version: str = "v1"


class SkillGapResponse(BaseModel):
    data: SkillGapResponseData
    meta: SkillGapMeta


class SkillGapAnalyzeRequest(BaseModel):
    target_role_id: UUID
    location: str = Field(default="India", min_length=1, max_length=64)
    user_id: Optional[UUID] = None
    resume_id: Optional[UUID] = None
    include_resume: bool = True
    include_github: bool = True
    username: Optional[str] = None

    @field_validator("location")
    @classmethod
    def validate_location_field(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Location cannot be blank or whitespace.")
        stripped = v.strip()
        if len(stripped) > 64:
            raise ValueError("Location exceeds maximum length of 64 characters.")
        return stripped



# -----------------------------------------------------------------------------
# Phase 5 Checkpoint 2: Prioritization Schemas
# -----------------------------------------------------------------------------

class PrioritizedGapItem(BaseModel):
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    status: str = Field(description="Actionable gap status: MISSING or PARTIAL")
    priority_score: float = Field(description="Calculated deterministic priority score [0.0, 1.0]")
    priority_level: str = Field(description="Human-readable priority tier: HIGH, MEDIUM, LOW")
    demand_score: float = Field(description="Empirical market demand score [0.0, 1.0]")
    growth_rate: float = Field(description="Year-over-year market growth rate")
    claimed: bool = Field(description="Whether claimed in resume")
    claim_confidence: float = Field(description="Resume claim confidence")
    demonstrated: bool = Field(description="Whether demonstrated in GitHub code artifacts")
    demonstrated_score: float = Field(description="Demonstrated code confidence score")
    evidence_level: Optional[str] = Field(None, description="Evidence level tier")
    evidence_count: int = Field(0, description="Total verified code artifacts")
    location: str = Field("India", description="Market location")
    explanation: str = Field(description="Deterministic rule-based explanation without an LLM")

    model_config = ConfigDict(from_attributes=True)


class PrioritizedGapsSummary(BaseModel):
    total_actionable_gaps: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    missing_count: int
    partial_count: int


class PrioritizedGapsResponseData(BaseModel):
    role: JobRoleItem
    location: str
    summary: PrioritizedGapsSummary
    gaps: List[PrioritizedGapItem]


class PrioritizedGapsResponse(BaseModel):
    data: PrioritizedGapsResponseData
    meta: SkillGapMeta
