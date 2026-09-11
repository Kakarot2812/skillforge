import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LearningResourceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resource_type: str = Field(..., description="Resource type: DOCUMENTATION or YOUTUBE")
    title: str = Field(..., description="Resource title")
    url: str = Field(..., description="Resource URL")
    description: str = Field(..., description="Resource description")


class RoadmapPrerequisiteItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: uuid.UUID
    skill_name: str
    skill_slug: str
    difficulty: str


class PracticeProblemItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    problem_id: str
    title: str
    difficulty: str = Field(default="BEGINNER", description="BEGINNER, INTERMEDIATE, or ADVANCED")
    order: int
    objective: str
    problem_statement: str
    requirements: List[str] = Field(default_factory=list)
    concepts_tested: List[str] = Field(default_factory=list)
    expected_outcome: str
    optional_hints: List[str] = Field(default_factory=list)
    user_status: str = Field(default="NOT_STARTED", description="User practice status: NOT_STARTED, IN_PROGRESS, COMPLETED")


class RoadmapSkillItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage_id: uuid.UUID
    roadmap_id: uuid.UUID
    canonical_skill_id: Optional[uuid.UUID] = None
    name: str
    slug: str
    description: str
    difficulty: str
    skill_order: int
    key_topics: List[str] = Field(default_factory=list)
    practice_project: Optional[str] = None
    practice_problems: List[PracticeProblemItem] = Field(default_factory=list)
    role_relevance: Optional[str] = None
    user_status: str = Field(default="NOT_STARTED", description="User learning status: NOT_STARTED, LEARNING, DONE, SKIPPED")
    prerequisites: List[RoadmapPrerequisiteItem] = Field(default_factory=list)
    resources: List[LearningResourceItem] = Field(default_factory=list)

    # Integrated candidate gap & market demand fields (only populated for canonical roles with candidate data)
    gap_status: Optional[str] = Field(None, description="Candidate gap status: STRONG, PARTIAL, MISSING, or None")
    priority_level: Optional[str] = Field(None, description="Prioritized gap level: HIGH, MEDIUM, LOW, or None")
    priority_score: Optional[float] = Field(None, description="Deterministic priority score [0.0, 1.0]")
    demand_score: Optional[float] = Field(None, description="Canonical role market demand score [0.0, 1.0]")


class RoadmapStageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    roadmap_id: uuid.UUID
    name: str
    description: Optional[str] = None
    stage_order: int
    total_skills: int
    completed_skills: int
    skills: List[RoadmapSkillItem] = Field(default_factory=list)


class RoadmapListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role_id: Optional[uuid.UUID] = None
    slug: str
    title: str
    domain: str
    category: str
    description: str
    version: str
    has_market_data: bool
    total_stages: int
    total_skills: int
    last_reviewed: datetime


class RoadmapListResponse(BaseModel):
    data: List[RoadmapListItem]
    total: int


class RoadmapSummary(BaseModel):
    total_skills: int
    completed_skills: int
    learning_skills: int
    skipped_skills: int
    not_started_skills: int
    progress_percentage: float
    high_priority_gap_count: int
    medium_priority_gap_count: int


class RoadmapDetailData(BaseModel):
    roadmap: RoadmapListItem
    ordering: str = Field(default="curated", description="Viewing mode: curated or recommended")
    summary: RoadmapSummary
    stages: List[RoadmapStageItem]
    recommended_skills: Optional[List[RoadmapSkillItem]] = None


class RoadmapDetailResponse(BaseModel):
    data: RoadmapDetailData


class UserProgressUpdateRequest(BaseModel):
    status: str = Field(..., description="Updated status: NOT_STARTED, LEARNING, DONE, SKIPPED")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        norm = v.strip().upper()
        allowed = {"NOT_STARTED", "LEARNING", "DONE", "SKIPPED"}
        if norm not in allowed:
            raise ValueError(f"Invalid status '{v}'. Allowed statuses: {', '.join(sorted(allowed))}")
        return norm


class UserProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    roadmap_skill_id: uuid.UUID
    status: str
    updated_at: datetime


class UserProgressResponse(BaseModel):
    success: bool
    data: UserProgressItem


class UserPracticeProgressUpdateRequest(BaseModel):
    status: str = Field(..., description="Updated status: NOT_STARTED, IN_PROGRESS, COMPLETED")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        norm = v.strip().upper()
        allowed = {"NOT_STARTED", "IN_PROGRESS", "COMPLETED"}
        if norm not in allowed:
            raise ValueError(f"Invalid status '{v}'. Allowed statuses: {', '.join(sorted(allowed))}")
        return norm


class UserPracticeProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    roadmap_skill_id: uuid.UUID
    problem_id: str
    status: str
    completed_at: Optional[datetime] = None
    updated_at: datetime



class UserPracticeProgressResponse(BaseModel):
    success: bool
    data: UserPracticeProgressItem
