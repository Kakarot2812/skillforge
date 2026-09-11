import uuid
from datetime import datetime
from typing import List, Optional, Set
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.v1.gaps import resolve_user_id, verify_user_exists
from app.db.database import get_db
from app.db.models import GitHubRepository, Skill, ProjectEvidence
from app.schemas.github import (
    GitHubConnectRequest,
    GitHubConnectData,
    GitHubConnectResponse,
    GitHubRepositoryItem,
    GitHubRepositoryListResponse,
    GitHubRepositoryDetailData,
    GitHubRepositoryDetailResponse,
)
from app.schemas.evidence import (
    GitHubAnalyzeRequest,
    GitHubAnalyzeData,
    GitHubAnalyzeResponse,
    DemonstratedSkillItem,
)
from app.schemas.skill import PaginationMeta
from app.services.github_service import github_service, validate_github_username
from app.services.github_analyzer import github_analyzer
from app.services.demonstrated_skill_service import demonstrated_skill_service

router = APIRouter(prefix="/github", tags=["GitHub Intelligence"])


@router.post(
    "/connect",
    response_model=GitHubConnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Connect GitHub Account and Discover Repositories",
)
def connect_github(
    payload: GitHubConnectRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    user_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
) -> GitHubConnectResponse:
    """
    Connects to GitHub, discovers public repositories, excludes forks,
    and idempotently persists repository metadata into PostgreSQL.
    Tokens are strictly handled as volatile secrets and never returned.
    """
    effective_user_id = resolve_user_id(user_id, x_user_id)
    verify_user_exists(db, effective_user_id)

    clean_username = payload.github_username.strip()
    synced_records = github_service.sync_repositories(
        db=db,
        username=clean_username,
        user_id=effective_user_id,
        token=payload.access_token,
    )

    items = [
        GitHubRepositoryItem(
            repo_id=r.id,
            github_repository_id=r.github_repository_id,
            repo_name=r.repo_name,
            full_name=r.full_name,
            repo_url=r.repo_url,
            description=r.description,
            default_branch=r.default_branch,
            visibility=r.visibility,
            primary_language=r.primary_language,
            is_fork=r.is_fork,
            stars_count=r.stars_count,
            forks_count=r.forks_count,
            last_pushed_at=r.last_pushed_at,
            synced_at=r.synced_at,
        )
        for r in synced_records
    ]

    return GitHubConnectResponse(
        data=GitHubConnectData(
            github_username=clean_username,
            connected=True,
            discovered_repositories=len(synced_records),
            connected_at=datetime.now(),
            repositories=items,
        )
    )


@router.get(
    "/repositories",
    response_model=GitHubRepositoryListResponse,
    summary="List Discovered Repositories",
)
def list_repositories(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user_id: Optional[uuid.UUID] = Query(None, description="Optional user ownership filter"),
    username: Optional[str] = Query(None, description="Optional GitHub account username/owner filter"),
    db: Session = Depends(get_db),
) -> GitHubRepositoryListResponse:
    """
    Retrieves paginated list of non-forked discovered repositories
    ordered deterministically by last_pushed_at descending.
    If username is provided, restricts strictly to repositories owned by that GitHub account.
    """
    query = db.query(GitHubRepository).filter(GitHubRepository.is_fork.is_(False))
    if user_id:
        query = query.filter(GitHubRepository.user_id == user_id)
    if username:
        safe_username = validate_github_username(username)
        query = query.filter(
            (GitHubRepository.full_name.ilike(f"{safe_username}/%"))
            | (GitHubRepository.repo_url.ilike(f"%github.com/{safe_username}/%"))
        )

    total = query.count()
    repos = (
        query.order_by(
            GitHubRepository.last_pushed_at.desc().nullslast(),
            GitHubRepository.stars_count.desc(),
            GitHubRepository.repo_name.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        GitHubRepositoryItem(
            repo_id=r.id,
            github_repository_id=r.github_repository_id,
            repo_name=r.repo_name,
            full_name=r.full_name,
            repo_url=r.repo_url,
            description=r.description,
            default_branch=r.default_branch,
            visibility=r.visibility,
            primary_language=r.primary_language,
            is_fork=r.is_fork,
            stars_count=r.stars_count,
            forks_count=r.forks_count,
            last_pushed_at=r.last_pushed_at,
            synced_at=r.synced_at,
        )
        for r in repos
    ]

    return GitHubRepositoryListResponse(
        data=items,
        meta=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.get(
    "/repositories/{repo_id}",
    response_model=GitHubRepositoryDetailResponse,
    summary="Get Repository Details",
)
def get_repository(
    repo_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = Query(None, description="Optional user ownership scope"),
    db: Session = Depends(get_db),
) -> GitHubRepositoryDetailResponse:
    """
    Retrieves stored repository metadata and artifact scanning indicators.
    Reads from the local database without making redundant GitHub API calls.
    """
    query = db.query(GitHubRepository).filter(GitHubRepository.id == repo_id)
    if user_id:
        query = query.filter(GitHubRepository.user_id == user_id)

    repo = query.first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"GitHub repository with id '{repo_id}' not found.",
        )

    return GitHubRepositoryDetailResponse(
        data=GitHubRepositoryDetailData(
            repo_id=repo.id,
            github_repository_id=repo.github_repository_id,
            repo_name=repo.repo_name,
            full_name=repo.full_name,
            repo_url=repo.repo_url,
            description=repo.description,
            default_branch=repo.default_branch,
            visibility=repo.visibility,
            primary_language=repo.primary_language,
            is_fork=repo.is_fork,
            stars_count=repo.stars_count,
            forks_count=repo.forks_count,
            last_pushed_at=repo.last_pushed_at,
            repo_metadata=repo.repo_metadata or {},
            created_at=repo.created_at,
            synced_at=repo.synced_at,
        )
    )


@router.post(
    "/analyze",
    response_model=GitHubAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Repository Artifacts and Detect Demonstrated Skills",
)
def analyze_repository(
    payload: GitHubAnalyzeRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    user_id: Optional[uuid.UUID] = Query(None),
    db: Session = Depends(get_db),
) -> GitHubAnalyzeResponse:
    """
    Scans connected repository manifests, Dockerfiles, and CI workflows
    to extract concrete, auditable evidence of demonstrated skills.
    """
    effective_user_id = resolve_user_id(user_id, x_user_id)
    if effective_user_id is not None:
        verify_user_exists(db, effective_user_id)

    repo_ids: List[uuid.UUID] = []
    if payload.repository_id:
        repo_ids.append(payload.repository_id)
    if payload.selected_repo_ids:
        repo_ids.extend(payload.selected_repo_ids)

    if not repo_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify repository_id or selected_repo_ids to analyze.",
        )

    all_evidence: List[ProjectEvidence] = []
    analyzed_repo_names: List[str] = []
    all_affected_skill_ids: Set[uuid.UUID] = set()
    target_user_id = effective_user_id

    for r_id in repo_ids:
        repo = db.query(GitHubRepository).filter(GitHubRepository.id == r_id).first()
        if not repo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"GitHub repository with id '{r_id}' not found.",
            )

        if effective_user_id is not None and repo.user_id != effective_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-user access denied: repository does not belong to authenticated user context.",
            )

        if target_user_id is None:
            target_user_id = repo.user_id

        if repo.is_fork and not payload.include_forks:
            continue

        evidence_items, affected_skills = github_analyzer.analyze_repository(db=db, repo=repo)
        all_evidence.extend(evidence_items)
        all_affected_skill_ids.update(affected_skills)
        analyzed_repo_names.append(repo.repo_name)

    # Recompute demonstrated skills for all affected skills (including stale ones)
    demonstrated_skills: List[DemonstratedSkillItem] = []

    for sid in all_affected_skill_ids:
        dem = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db, skill_id=sid, user_id=target_user_id
        )
        if not dem:
            continue
        skill = db.query(Skill).filter(Skill.id == dem.skill_id).first()
        if not skill:
            continue
        meta = dem.skill_metadata or {}
        ev_types = meta.get("evidence_types", ["dependency"])
        primary_ev_type = ev_types[0] if ev_types else "dependency"

        demonstrated_skills.append(
            DemonstratedSkillItem(
                skill_id=skill.id,
                skill_name=skill.name,
                name=skill.name,
                canonical_slug=skill.slug,
                confidence_score=dem.confidence_score,
                evidence_type=primary_ev_type,
                evidence_tier=dem.evidence_level,
            )
        )

    # Sort demonstrated skills deterministically
    demonstrated_skills.sort(key=lambda s: (-s.confidence_score, s.skill_name))

    first_repo_id = repo_ids[0] if len(repo_ids) == 1 else None
    first_repo_name = analyzed_repo_names[0] if len(analyzed_repo_names) == 1 else None

    return GitHubAnalyzeResponse(
        data=GitHubAnalyzeData(
            repository_id=first_repo_id,
            repository_name=first_repo_name,
            analyzed=True,
            repositories_analyzed=len(analyzed_repo_names),
            evidence_count=len(all_evidence),
            evidence_items_detected=len(all_evidence),
            demonstrated_skills=demonstrated_skills,
        )
    )
