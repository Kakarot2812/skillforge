from datetime import datetime, date
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class JobRoleItem(BaseModel):
    role_id: UUID
    title: str
    slug: str
    category: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int


class JobRoleListResponse(BaseModel):
    data: List[JobRoleItem]
    meta: PaginationMeta


class JobRoleDetailResponse(BaseModel):
    data: JobRoleItem


class SkillDemandItem(BaseModel):
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    role_id: Optional[UUID] = None
    role_title: Optional[str] = None
    location: str
    sample_size: int
    demand_score: float
    growth_rate: float
    data_updated_at: str

    model_config = ConfigDict(from_attributes=True)


class DemandPaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    role_id: Optional[UUID] = None
    location: Optional[str] = "India"
    data_freshness: Optional[str] = "2026-09-01"


class SkillDemandListResponse(BaseModel):
    data: List[SkillDemandItem]
    meta: DemandPaginationMeta


class RoleSkillDemandItem(BaseModel):
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    demand_score: float
    growth_rate: float
    sample_size: int
    location: str
    data_updated_at: str

    model_config = ConfigDict(from_attributes=True)


class RoleDemandDetailData(BaseModel):
    role: JobRoleItem
    skills: List[RoleSkillDemandItem]


class RoleDemandDetailMeta(BaseModel):
    total: int
    location: str = "India"
    data_freshness: str = "2026-09-01"
    total_demanded_skills: Optional[int] = None
    average_demand_score: Optional[float] = None
    highest_demand_score: Optional[float] = None
    lowest_demand_score: Optional[float] = None
    average_growth_rate: Optional[float] = None
    top_skill: Optional[str] = None


class RoleDemandDetailResponse(BaseModel):
    data: RoleDemandDetailData
    meta: RoleDemandDetailMeta


class DemandQualityAuditReport(BaseModel):
    status: str
    total_roles: int
    total_demand_records: int
    roles_with_demand: int
    orphaned_roles: int
    orphaned_demand_records: int
    out_of_bounds_scores: int
    non_positive_sample_sizes: int
    duplicate_records: int
    data_freshness: str = "2026-09-01"
    audit_timestamp: str


class DemandQualityAuditResponse(BaseModel):
    data: DemandQualityAuditReport

