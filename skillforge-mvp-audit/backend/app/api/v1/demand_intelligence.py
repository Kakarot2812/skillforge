import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.demand import JobRoleItem, DemandPaginationMeta
from app.schemas.demand_intelligence import (
    SkillDemandRankingItem,
    RankingPaginationMeta,
    SkillDemandRankingResponse,
    SkillItem,
    SkillRoleDemandItem,
    SkillRoleDemandData,
    SkillRoleDemandMeta,
    SkillRoleDemandResponse,
    RoleCompareRequest,
    ComparedRoleItem,
    SharedSkillDemandItem,
    RoleSpecificSkillItem,
    RoleComparisonSummary,
    RoleCompareData,
    RoleCompareMeta,
    RoleCompareResponse,
    RoleSignalsMetricData,
    RoleSignalsSkillItem,
    RoleMarketSignalsData,
    RoleMarketSignalsMeta,
    RoleMarketSignalsResponse,
    DemandTrendItem,
    DemandTrendsResponse,
)
from app.services.demand_intelligence_service import demand_intelligence_service

router = APIRouter(tags=["Demand Intelligence"])


@router.get(
    "/skills/ranking",
    response_model=SkillDemandRankingResponse,
    summary="Get Global or Role-Specific Skill Demand Ranking",
)
def get_skill_ranking(
    location: str = Query("India", description="Geographic scope"),
    role_id: Optional[uuid.UUID] = Query(None, description="Optional target role filter"),
    limit: int = Query(50, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    db: Session = Depends(get_db),
) -> SkillDemandRankingResponse:
    """
    Ranks canonical skills by industry demand score.
    When role_id is omitted, returns global rankings computed via sample-size-weighted aggregation:
    SUM(demand_score * sample_size) / SUM(sample_size).
    """
    items_raw, total = demand_intelligence_service.get_skill_demand_ranking(
        db=db,
        location=location,
        role_id=role_id,
        limit=limit,
        offset=offset,
    )

    items = [SkillDemandRankingItem(**it) for it in items_raw]

    return SkillDemandRankingResponse(
        data=items,
        meta=RankingPaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            location=location,
            role_id=role_id,
            data_freshness="2026-09-01",
        ),
    )


@router.get(
    "/skills/{skill_id}/roles",
    response_model=SkillRoleDemandResponse,
    summary="Get Skill Demand Profile Across Job Roles",
)
def get_skill_across_roles(
    skill_id: uuid.UUID,
    location: str = Query("India", description="Geographic scope"),
    db: Session = Depends(get_db),
) -> SkillRoleDemandResponse:
    """
    Retrieves the demand profile of a canonical skill across all canonical job roles.
    Returns 404 if the skill does not exist.
    """
    result = demand_intelligence_service.get_skill_role_demand(
        db=db,
        skill_id=skill_id,
        location=location,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canonical skill with id '{skill_id}' not found.",
        )

    return SkillRoleDemandResponse(
        data=SkillRoleDemandData(
            skill=SkillItem(**result["skill"]),
            roles=[SkillRoleDemandItem(**r) for r in result["roles"]],
            average_demand_score=result["average_demand_score"],
            total_roles_demanding=result["total_roles_demanding"],
        ),
        meta=SkillRoleDemandMeta(
            location=location,
            data_freshness="2026-09-01",
        ),
    )


@router.post(
    "/roles/compare",
    response_model=RoleCompareResponse,
    summary="Compare 2-5 Canonical Job Roles",
)
def compare_job_roles(
    payload: RoleCompareRequest,
    db: Session = Depends(get_db),
) -> RoleCompareResponse:
    """
    Deterministically compares 2 to 5 canonical job roles.
    Identifies shared skills demanded across all compared roles and role-specific skills.
    Calculates demand score differentials and average growth trajectories.
    """
    try:
        comparison = demand_intelligence_service.compare_roles(
            db=db,
            role_ids=payload.role_ids,
            location=payload.location,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'"),
        )

    compared_roles = [ComparedRoleItem(**r) for r in comparison["roles"]]
    shared_skills = [SharedSkillDemandItem(**s) for s in comparison["shared_skills"]]

    role_specific: dict = {}
    for r_id_str, skill_list in comparison["role_specific_skills"].items():
        role_specific[r_id_str] = [RoleSpecificSkillItem(**sk) for sk in skill_list]

    summary = RoleComparisonSummary(**comparison["comparison_summary"])

    return RoleCompareResponse(
        data=RoleCompareData(
            roles=compared_roles,
            shared_skills=shared_skills,
            role_specific_skills=role_specific,
            comparison_summary=summary,
        ),
        meta=RoleCompareMeta(
            location=payload.location,
            data_freshness="2026-09-01",
        ),
    )


@router.get(
    "/roles/{role_id}/signals",
    response_model=RoleMarketSignalsResponse,
    summary="Get Role Market Demand Signals",
)
def get_role_signals(
    role_id: uuid.UUID,
    location: str = Query("India", description="Geographic scope"),
    db: Session = Depends(get_db),
) -> RoleMarketSignalsResponse:
    """
    Calculates deterministic market-demand signals for a canonical job role:
    Rising, stable, and declining skill counts, top 5 demanded skills, and top 5 fastest growing skills.
    Returns 404 if the role does not exist.
    """
    signals = demand_intelligence_service.get_role_market_signals(
        db=db,
        role_id=role_id,
        location=location,
    )
    if not signals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job role with id '{role_id}' not found.",
        )

    return RoleMarketSignalsResponse(
        data=RoleMarketSignalsData(
            role=JobRoleItem(**signals["role"]),
            metrics=RoleSignalsMetricData(**signals["metrics"]),
            top_demanded_skills=[RoleSignalsSkillItem(**s) for s in signals["top_demanded_skills"]],
            fastest_growing_skills=[RoleSignalsSkillItem(**s) for s in signals["fastest_growing_skills"]],
        ),
        meta=RoleMarketSignalsMeta(
            location=location,
            data_freshness="2026-09-01",
        ),
    )


@router.get(
    "/trends",
    response_model=DemandTrendsResponse,
    summary="List Demand Records Enriched with Growth Trends",
)
def get_demand_trends(
    location: str = Query("India", description="Geographic scope"),
    role_id: Optional[uuid.UUID] = Query(None, description="Optional target role filter"),
    limit: int = Query(20, ge=1, le=100, description="Page limit (1-100)"),
    offset: int = Query(0, ge=0, description="Records to skip"),
    db: Session = Depends(get_db),
) -> DemandTrendsResponse:
    """
    Retrieves demand records enriched with growth trends (RISING, STABLE, DECLINING).
    Ordered deterministically: highest growth first, with stable tie-breaking.
    """
    items_raw, total = demand_intelligence_service.get_demand_trends(
        db=db,
        location=location,
        role_id=role_id,
        limit=limit,
        offset=offset,
    )

    items = [DemandTrendItem(**it) for it in items_raw]

    return DemandTrendsResponse(
        data=items,
        meta=DemandPaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            role_id=role_id,
            location=location,
            data_freshness="2026-09-01",
        ),
    )
