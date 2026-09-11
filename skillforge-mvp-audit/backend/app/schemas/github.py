from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.skill import PaginationMeta


class GitHubConnectRequest(BaseModel):
    github_username: str = Field(..., description="GitHub handle or organization name", min_length=1, max_length=39)
    access_token: Optional[str] = Field(None, description="Optional GitHub personal access token for private repos or rate limit elevation")


class GitHubRepositoryItem(BaseModel):
    repo_id: UUID
    github_repository_id: Optional[int] = None
    repo_name: str
    full_name: Optional[str] = None
    repo_url: str
    description: Optional[str] = None
    default_branch: Optional[str] = "main"
    visibility: Optional[str] = "public"
    primary_language: Optional[str] = None
    is_fork: bool = False
    stars_count: int = 0
    forks_count: int = 0
    last_pushed_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GitHubConnectData(BaseModel):
    github_username: str
    connected: bool = True
    discovered_repositories: int
    connected_at: datetime
    repositories: Optional[List[GitHubRepositoryItem]] = None


class GitHubConnectResponse(BaseModel):
    data: GitHubConnectData


class GitHubRepositoryListResponse(BaseModel):
    data: List[GitHubRepositoryItem]
    meta: PaginationMeta


class GitHubRepositoryDetailData(BaseModel):
    repo_id: UUID
    github_repository_id: Optional[int] = None
    repo_name: str
    full_name: Optional[str] = None
    repo_url: str
    description: Optional[str] = None
    default_branch: Optional[str] = "main"
    visibility: Optional[str] = "public"
    primary_language: Optional[str] = None
    is_fork: bool = False
    stars_count: int = 0
    forks_count: int = 0
    last_pushed_at: Optional[datetime] = None
    repo_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GitHubRepositoryDetailResponse(BaseModel):
    data: GitHubRepositoryDetailData
