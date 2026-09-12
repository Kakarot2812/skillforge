import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.demand import (
    JobRoleItem,
    SkillDemandItem,
    DemandPaginationMeta,
    SkillDemandListResponse,
    RoleSkillDemandItem,
    RoleDemandDetailData,
    RoleDemandDetailMeta,
    RoleDemandDetailResponse,
    DemandQualityAuditReport,
    DemandQualityAuditResponse,
)
from app.services.demand_service import demand_service

router = APIRouter(tags=["Industry Demand"])


@router.get(
    "/audit/quality",
    response_model=DemandQualityAuditResponse,
    summary="Audit Demand Data Quality & Integrity",
)
def audit_demand_quality(
    db: Session = Depends(get_db),
) -> DemandQualityAuditResponse:
    """
    Executes deterministic validation on industry demand records and canonical roles.
    Verifies absence of orphans, out-of-bounds scores, non-positive sample sizes, and duplicates.
    """
    report = demand_service.audit_demand_data_quality(db)
    return DemandQualityAuditResponse(data=DemandQualityAuditReport(**report))


@router.get(
    "",
    response_model=SkillDemandListResponse,
    summary="List Industry Skill Demand",
)
def list_industry_demand(
    role_id: Optional[uuid.UUID] = Query(None, description="Filter by canonical job role ID"),
    skill_id: Optional[uuid.UUID] = Query(None, description="Filter by canonical skill ID"),
    location: str = Query("India", description="Market geographic scope"),
    limit: int = Query(20, ge=1, le=100, description="Maximum skills to return"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    db: Session = Depends(get_db),
) -> SkillDemandListResponse:
    """
    Retrieves empirical industry skill demand statistics.
    Demand score is a database-derived statistical metric calculated from structured market data.
    The LLM MUST NOT calculate, invent, or override demand_score.
    This is shared/canonical data not owned by any specific user.
    """
    items_raw, total = demand_service.get_industry_demand(
        db=db,
        role_id=role_id,
        skill_id=skill_id,
        location=location,
        limit=limit,
        offset=offset,
    )

    items = [SkillDemandItem(**it) for it in items_raw]
    freshness = demand_service.get_market_data_freshness(db)

    return SkillDemandListResponse(
        data=items,
        meta=DemandPaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            role_id=role_id,
            location=location,
            data_freshness=freshness,
        ),
    )


@router.get(
    "/{role_id}",
    response_model=RoleDemandDetailResponse,
    summary="Get Role Demand Profile",
)
def get_role_demand_breakdown(
    role_id: uuid.UUID,
    location: str = Query("India", description="Market geographic scope"),
    db: Session = Depends(get_db),
) -> RoleDemandDetailResponse:
    """
    Retrieves the complete skill demand profile and SQL-derived aggregate metrics for a canonical job role.
    Returns 404 if the role does not exist.
    """
    result = demand_service.get_role_demand_profile(
        db=db,
        role_id=role_id,
        location=location,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job role with id '{role_id}' not found.",
        )

    role, skills_raw, aggregates = result
    skills = [RoleSkillDemandItem(**s) for s in skills_raw]
    freshness = demand_service.get_market_data_freshness(db)

    return RoleDemandDetailResponse(
        data=RoleDemandDetailData(
            role=JobRoleItem(
                role_id=role.id,
                title=role.title,
                slug=role.slug,
                category=role.category,
                description=role.description,
            ),
            skills=skills,
        ),
        meta=RoleDemandDetailMeta(
            total=len(skills),
            location=location,
            data_freshness=freshness,
            total_demanded_skills=aggregates["total_demanded_skills"],
            average_demand_score=aggregates["average_demand_score"],
            highest_demand_score=aggregates["highest_demand_score"],
            lowest_demand_score=aggregates["lowest_demand_score"],
            average_growth_rate=aggregates["average_growth_rate"],
            top_skill=aggregates["top_skill"],
        ),
    )

