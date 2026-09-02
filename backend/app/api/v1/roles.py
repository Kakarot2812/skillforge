import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.demand import (
    JobRoleItem,
    JobRoleListResponse,
    JobRoleDetailResponse,
    PaginationMeta,
)
from app.services.demand_service import demand_service

router = APIRouter(tags=["Job Roles"])


@router.get(
    "",
    response_model=JobRoleListResponse,
    summary="List Canonical Job Roles",
)
def list_job_roles(
    category: Optional[str] = Query(None, description="Filter by role category (e.g., Engineering, Data & AI)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    db: Session = Depends(get_db),
) -> JobRoleListResponse:
    """
    Retrieves canonical job roles supported by the platform.
    Job roles represent industry tracks for career progression and skill-gap evaluation.
    This is shared/canonical data not owned by any specific user.
    """
    roles, total = demand_service.get_job_roles(
        db=db,
        category=category,
        limit=limit,
        offset=offset,
    )

    items = [
        JobRoleItem(
            role_id=r.id,
            title=r.title,
            slug=r.slug,
            category=r.category,
            description=r.description,
        )
        for r in roles
    ]

    return JobRoleListResponse(
        data=items,
        meta=PaginationMeta(total=total, limit=limit, offset=offset),
    )


@router.get(
    "/{role_id}",
    response_model=JobRoleDetailResponse,
    summary="Get Canonical Job Role by ID",
)
def get_job_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobRoleDetailResponse:
    """
    Retrieves details for a specific canonical job role by its UUID.
    Returns 404 if the role does not exist.
    """
    role = demand_service.get_job_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job role with id '{role_id}' not found.",
        )

    return JobRoleDetailResponse(
        data=JobRoleItem(
            role_id=role.id,
            title=role.title,
            slug=role.slug,
            category=role.category,
            description=role.description,
        )
    )
