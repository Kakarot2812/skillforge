from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.demand import JobRoleItem, DemandPaginationMeta


class SkillDemandRankingItem(BaseModel):
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    demand_score: float
    average_growth_rate: float
    role_count: int
    total_sample_size: int
    trend: str

    model_config = ConfigDict(from_attributes=True)


class RankingPaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    location: str = "India"
    role_id: Optional[UUID] = None
    data_freshness: str = "2026-09-01"


class SkillDemandRankingResponse(BaseModel):
    data: List[SkillDemandRankingItem]
    meta: RankingPaginationMeta


class SkillItem(BaseModel):
    id: UUID
    name: str
    slug: str
    category: Optional[str] = None
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SkillRoleDemandItem(BaseModel):
    role_id: UUID
    role_title: str
    role_slug: str
    demand_score: float
    growth_rate: float
    sample_size: int
    trend: str
    location: str

    model_config = ConfigDict(from_attributes=True)


class SkillRoleDemandData(BaseModel):
    skill: SkillItem
    roles: List[SkillRoleDemandItem]
    average_demand_score: float
    total_roles_demanding: int


class SkillRoleDemandMeta(BaseModel):
    location: str = "India"
    data_freshness: str = "2026-09-01"


class SkillRoleDemandResponse(BaseModel):
    data: SkillRoleDemandData
    meta: SkillRoleDemandMeta


class RoleCompareRequest(BaseModel):
    role_ids: List[UUID]
    location: str = "India"


class ComparedRoleItem(BaseModel):
    role_id: UUID
    title: str
    slug: str
    category: str
    total_demanded_skills: int
    average_demand_score: float
    top_skill: Optional[str] = None


class RoleDemandPoint(BaseModel):
    role_id: UUID
    role_title: str
    demand_score: float
    growth_rate: float
    trend: str


class SharedSkillDemandItem(BaseModel):
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    average_demand_score: float
    demand_score_diff: float
    average_growth_rate: float
    demands_by_role: Dict[str, RoleDemandPoint]


class RoleSpecificSkillItem(BaseModel):
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    demand_score: float
    growth_rate: float
    trend: str


class RoleComparisonSummary(BaseModel):
    compared_roles_count: int
    total_unique_skills: int
    shared_skills_count: int
    role_specific_counts: Dict[str, int]


class RoleCompareData(BaseModel):
    roles: List[ComparedRoleItem]
    shared_skills: List[SharedSkillDemandItem]
    role_specific_skills: Dict[str, List[RoleSpecificSkillItem]]
    comparison_summary: RoleComparisonSummary


class RoleCompareMeta(BaseModel):
    location: str = "India"
    data_freshness: str = "2026-09-01"


class RoleCompareResponse(BaseModel):
    data: RoleCompareData
    meta: RoleCompareMeta


class RoleSignalsMetricData(BaseModel):
    total_demanded_skills: int
    average_demand_score: float
    highest_demand_score: float
    lowest_demand_score: float
    average_growth_rate: float
    rising_skill_count: int
    stable_skill_count: int
    declining_skill_count: int


class RoleSignalsSkillItem(BaseModel):
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    demand_score: float
    growth_rate: float
    trend: str


class RoleMarketSignalsData(BaseModel):
    role: JobRoleItem
    metrics: RoleSignalsMetricData
    top_demanded_skills: List[RoleSignalsSkillItem]
    fastest_growing_skills: List[RoleSignalsSkillItem]


class RoleMarketSignalsMeta(BaseModel):
    location: str = "India"
    data_freshness: str = "2026-09-01"


class RoleMarketSignalsResponse(BaseModel):
    data: RoleMarketSignalsData
    meta: RoleMarketSignalsMeta


class DemandTrendItem(BaseModel):
    skill_id: UUID
    skill_name: str
    canonical_slug: str
    category: Optional[str] = None
    role_id: UUID
    role_title: str
    demand_score: float
    growth_rate: float
    trend: str
    location: str
    sample_size: int


class DemandTrendsResponse(BaseModel):
    data: List[DemandTrendItem]
    meta: DemandPaginationMeta
