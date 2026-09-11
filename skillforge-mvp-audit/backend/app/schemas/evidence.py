from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.skill import PaginationMeta


class GitHubAnalyzeRequest(BaseModel):
    repository_id: Optional[UUID] = Field(None, description="Repository UUID to analyze")
    selected_repo_ids: Optional[List[UUID]] = Field(None, description="Optional batch repository UUIDs to analyze")
    include_forks: bool = Field(False, description="Whether to include forks (defaults to False)")


class DemonstratedSkillItem(BaseModel):
    skill_id: UUID
    skill_name: str
    name: str  # synonym for skill_name
    canonical_slug: str
    confidence_score: float
    evidence_type: str
    evidence_tier: str = "HIGH"

    model_config = ConfigDict(from_attributes=True)


class GitHubAnalyzeData(BaseModel):
    repository_id: Optional[UUID] = None
    repository_name: Optional[str] = None
    analyzed: bool = True
    repositories_analyzed: int = 1
    evidence_count: int
    evidence_items_detected: int  # synonym for API_SPEC.md compatibility
    demonstrated_skills: List[DemonstratedSkillItem]


class GitHubAnalyzeResponse(BaseModel):
    data: GitHubAnalyzeData


class ProjectEvidenceItem(BaseModel):
    evidence_id: UUID
    repository_id: Optional[UUID] = None
    repo_name: Optional[str] = None
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    evidence_type: str
    artifact_path: Optional[str] = None
    file_path: Optional[str] = None
    artifact_name: Optional[str] = None
    evidence_description: Optional[str] = None
    matched_content: Optional[str] = None
    confidence_score: float
    evidence_metadata: Dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectEvidenceListResponse(BaseModel):
    data: List[ProjectEvidenceItem]
    meta: PaginationMeta


class ProjectEvidenceDetailResponse(BaseModel):
    data: ProjectEvidenceItem
