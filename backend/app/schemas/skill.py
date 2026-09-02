from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SkillBase(BaseModel):
    name: str
    slug: str
    category: Optional[str] = None
    description: Optional[str] = None


class SkillCreate(SkillBase):
    pass


class SkillRead(SkillBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClaimedSkillItem(BaseModel):
    id: UUID
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    source: str = "resume"
    raw_mention: Optional[str] = None
    confidence_score: float
    evidence_tier: str = "CLAIMED"
    resume_id: Optional[UUID] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int


class ClaimedSkillsResponse(BaseModel):
    data: List[ClaimedSkillItem]
    meta: PaginationMeta
