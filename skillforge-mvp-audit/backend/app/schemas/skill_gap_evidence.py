import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.skill_gap import SkillGapMeta


class ResumeEvidenceItem(BaseModel):
    id: uuid.UUID
    raw_mention: Optional[str] = None
    confidence_score: float
    source: str = "resume"
    resume_id: Optional[uuid.UUID] = None
    resume_file_name: Optional[str] = None
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GitHubEvidenceItem(BaseModel):
    id: uuid.UUID
    repo_id: Optional[uuid.UUID] = None
    repo_name: str
    repo_full_name: Optional[str] = None
    repo_url: Optional[str] = None
    evidence_type: str
    file_path: Optional[str] = None
    artifact_name: Optional[str] = None
    matched_content: Optional[str] = None
    confidence_score: float
    detected_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DemonstratedSkillSummary(BaseModel):
    confidence_score: float
    evidence_level: str
    evidence_count: int
    repository_count: int
    last_verified_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateEvidenceData(BaseModel):
    has_evidence: bool
    resume_claims: List[ResumeEvidenceItem] = Field(default_factory=list)
    github_demonstrated: Optional[DemonstratedSkillSummary] = None
    github_artifacts: List[GitHubEvidenceItem] = Field(default_factory=list)


class MarketEvidenceData(BaseModel):
    role_id: uuid.UUID
    role_title: str
    role_slug: str
    location: str
    demand_score: float
    growth_rate: float
    sample_size: int
    data_updated_at: Optional[str] = None


class DeterministicReasoningData(BaseModel):
    classification_reason: str
    priority_reason: str
    scoring_version: str = "v1"


class SkillGapEvidenceResponseData(BaseModel):
    skill_id: uuid.UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    status: str = Field(description="Deterministic status: STRONG, PARTIAL, or MISSING")
    priority_score: Optional[float] = None
    priority_level: Optional[str] = None
    candidate_evidence: CandidateEvidenceData
    market_evidence: MarketEvidenceData
    reasoning: DeterministicReasoningData


class SkillGapEvidenceResponse(BaseModel):
    data: SkillGapEvidenceResponseData
    meta: SkillGapMeta
