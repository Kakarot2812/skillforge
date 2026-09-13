"""
Pydantic Schemas for Static Skill Roadmap Catalog and User Progress.
Phase 3: Static Roadmap Schemas & Service.
"""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


# -----------------------------------------------------------------------------
# Learning Resource Schemas
# -----------------------------------------------------------------------------

class LearningResourceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource_type: str = Field(..., description="Resource type: DOCUMENTATION or YOUTUBE")
    title: str = Field(..., description="Resource title")
    url: str = Field(..., description="Resource URL")
    description: str = Field(..., description="Resource description")


# -----------------------------------------------------------------------------
# Prerequisite Schemas
# -----------------------------------------------------------------------------

class RoadmapPrerequisiteItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: UUID
    skill_name: str
    skill_slug: str
    difficulty: str


# -----------------------------------------------------------------------------
# Practice Problem Schemas
# -----------------------------------------------------------------------------

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
    user_status: str = Field(
        default="NOT_STARTED",
        description="User practice status: NOT_STARTED, IN_PROGRESS, COMPLETED",
    )


# -----------------------------------------------------------------------------
# Roadmap Skill Schemas
# -----------------------------------------------------------------------------

class RoadmapSkillItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stage_id: UUID
    roadmap_id: UUID
    canonical_skill_id: Optional[UUID] = None
    name: str
    slug: str
    description: str
    difficulty: str
    skill_order: int
    key_topics: List[str] = Field(default_factory=list)
    practice_project: Optional[str] = None
    practice_problems: List[PracticeProblemItem] = Field(default_factory=list)
    role_relevance: Optional[str] = None
    user_status: str = Field(
        default="NOT_STARTED",
        description="User learning status: NOT_STARTED, LEARNING, DONE, SKIPPED",
    )
    prerequisites: List[RoadmapPrerequisiteItem] = Field(default_factory=list)
    resources: List[LearningResourceItem] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Roadmap Stage Schemas
# -----------------------------------------------------------------------------

class RoadmapStageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    roadmap_id: UUID
    name: str
    description: Optional[str] = None
    stage_order: int
    total_skills: int
    completed_skills: int
    skills: List[RoadmapSkillItem] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Roadmap Catalog List Schemas
# -----------------------------------------------------------------------------

class RoadmapListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role_id: Optional[UUID] = None
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


# -----------------------------------------------------------------------------
# Roadmap Detail & Summary Schemas
# -----------------------------------------------------------------------------

class RoadmapSummary(BaseModel):
    total_skills: int
    completed_skills: int
    learning_skills: int
    skipped_skills: int
    not_started_skills: int
    progress_percentage: float


class RoadmapDetailData(BaseModel):
    roadmap: RoadmapListItem
    ordering: str = Field(default="curated", description="Viewing mode: curated or recommended")
    summary: RoadmapSummary
    stages: List[RoadmapStageItem]
    recommended_skills: Optional[List[RoadmapSkillItem]] = None


class RoadmapDetailResponse(BaseModel):
    data: RoadmapDetailData


# -----------------------------------------------------------------------------
# User Progress Update & Response Schemas
# -----------------------------------------------------------------------------

class UserProgressUpdateRequest(BaseModel):
    status: str = Field(..., description="Updated status: NOT_STARTED, LEARNING, DONE, SKIPPED")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Status must be a string.")
        norm = v.strip().upper()
        allowed = {"NOT_STARTED", "LEARNING", "DONE", "SKIPPED"}
        if norm not in allowed:
            raise ValueError(f"Invalid status '{v}'. Allowed statuses: {', '.join(sorted(allowed))}")
        return norm


class UserProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    roadmap_skill_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime


class UserProgressResponse(BaseModel):
    success: bool = True
    data: UserProgressItem


# -----------------------------------------------------------------------------
# User Practice Progress Update & Response Schemas
# -----------------------------------------------------------------------------

class UserPracticeProgressUpdateRequest(BaseModel):
    status: str = Field(..., description="Updated status: NOT_STARTED, IN_PROGRESS, COMPLETED")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Status must be a string.")
        norm = v.strip().upper()
        allowed = {"NOT_STARTED", "IN_PROGRESS", "COMPLETED"}
        if norm not in allowed:
            raise ValueError(f"Invalid status '{v}'. Allowed statuses: {', '.join(sorted(allowed))}")
        return norm


class UserPracticeProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    roadmap_skill_id: UUID
    problem_id: str
    status: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class UserPracticeProgressResponse(BaseModel):
    success: bool = True
    data: UserPracticeProgressItem


# -----------------------------------------------------------------------------
# User Roadmap Progress Summary Read Model
# -----------------------------------------------------------------------------

class UserRoadmapProgressSummary(BaseModel):
    roadmap_id: UUID
    total_skills: int
    completed_skills: int
    learning_skills: int
    skipped_skills: int
    not_started_skills: int
    progress_percentage: float
    total_practice_problems: int
    completed_practice_problems: int
