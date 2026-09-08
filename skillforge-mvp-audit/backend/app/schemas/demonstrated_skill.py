from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence import ProjectEvidenceItem
from app.schemas.skill import PaginationMeta


class SupportingRepositoryItem(BaseModel):
    repository_id: Optional[str] = None
    repo_name: str
    repo_url: Optional[str] = None
    max_confidence: float
    evidence_count: int

    model_config = ConfigDict(from_attributes=True)


class DemonstratedSkillSummaryItem(BaseModel):
    skill_id: UUID
    skill_name: str
    slug: str
    category: Optional[str] = None
    confidence_score: float
    evidence_level: str
    evidence_count: int
    repository_count: int
    last_verified_at: Optional[datetime] = None
    repositories: List[SupportingRepositoryItem] = Field(default_factory=list)
    evidence_types: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DemonstratedSkillListResponse(BaseModel):
    data: List[DemonstratedSkillSummaryItem]
    meta: PaginationMeta


class DemonstratedSkillDetailData(BaseModel):
    skill_id: UUID
    skill_name: str
    slug: str
    category: Optional[str] = None
    description: Optional[str] = None
    confidence_score: float
    evidence_level: str
    evidence_count: int
    repository_count: int
    last_verified_at: Optional[datetime] = None
    repositories: List[SupportingRepositoryItem] = Field(default_factory=list)
    evidence_types: List[str] = Field(default_factory=list)
    evidence: List[ProjectEvidenceItem] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DemonstratedSkillDetailResponse(BaseModel):
    data: DemonstratedSkillDetailData
