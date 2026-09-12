import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import JobRole, IndustrySkillDemand, Skill, MarketSkillDemandSnapshot


def get_market_data_freshness(db: Session) -> str:
    """
    Returns the latest market data freshness timestamp as 'YYYY-MM-DD'.
    Queries the newest snapshot from MarketSkillDemandSnapshot (post-P1-L).
    Falls back to '2026-09-01' if no snapshot exists.
    """
    row = (
        db.query(MarketSkillDemandSnapshot.snapshot_at)
        .order_by(MarketSkillDemandSnapshot.snapshot_at.desc())
        .first()
    )
    if row and row[0]:
        return row[0].strftime("%Y-%m-%d")
    return "2026-09-01"


class DemandService:
    """
    Deterministic data access layer for canonical job roles and industry skill demand.
    Data is global/shared and derived strictly from the PostgreSQL database.
    LLMs are strictly forbidden from generating or mutating demand scores.
    """

    def get_job_roles(
        self,
        db: Session,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[JobRole], int]:
        """
        Retrieves paginated canonical job roles ordered deterministically.
        """
        query = db.query(JobRole)
        if category:
            query = query.filter(func.lower(JobRole.category) == category.strip().lower())

        total = query.count()
        roles = (
            query.order_by(JobRole.category.asc(), JobRole.title.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return roles, total

    def get_job_role_by_id(
        self,
        db: Session,
        role_id: uuid.UUID,
    ) -> Optional[JobRole]:
        """
        Retrieves a canonical job role by its UUID primary key.
        """
        return db.query(JobRole).filter(JobRole.id == role_id).first()

    def get_industry_demand(
        self,
        db: Session,
        role_id: Optional[uuid.UUID] = None,
        skill_id: Optional[uuid.UUID] = None,
        location: Optional[str] = "India",
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves paginated industry skill demand records with skill and role joins,
        ordered deterministically by demand_score DESC, skill.name ASC.
        """
        query = (
            db.query(IndustrySkillDemand, Skill, JobRole)
            .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
            .join(JobRole, IndustrySkillDemand.role_id == JobRole.id)
        )

        if role_id:
            query = query.filter(IndustrySkillDemand.role_id == role_id)
        if skill_id:
            query = query.filter(IndustrySkillDemand.skill_id == skill_id)
        if location:
            query = query.filter(func.lower(IndustrySkillDemand.location) == location.strip().lower())

        total = query.count()
        rows = (
            query.order_by(
                IndustrySkillDemand.demand_score.desc(),
                Skill.name.asc(),
                Skill.id.asc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = []
        for demand, skill, role in rows:
            dt_str = demand.data_updated_at.strftime("%Y-%m-%d") if demand.data_updated_at else "2026-09-01"
            items.append(
                {
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "canonical_slug": skill.slug,
                    "category": skill.category,
                    "role_id": role.id,
                    "role_title": role.title,
                    "location": demand.location,
                    "sample_size": demand.sample_size,
                    "demand_score": round(demand.demand_score, 2),
                    "growth_rate": round(demand.growth_rate, 2),
                    "data_updated_at": dt_str,
                }
            )

        return items, total

    def get_role_demand_aggregates(
        self,
        db: Session,
        role_id: uuid.UUID,
        location: Optional[str] = "India",
    ) -> Dict[str, Any]:
        """
        Calculates deterministic SQL-level aggregate statistics for a job role's demand profile:
        - total_demanded_skills: COUNT(demand records)
        - average_demand_score: AVG(demand_score) rounded to 2 decimal places
        - highest_demand_score: MAX(demand_score) rounded to 2 decimal places
        - lowest_demand_score: MIN(demand_score) rounded to 2 decimal places
        - average_growth_rate: AVG(growth_rate) rounded to 2 decimal places
        - top_skill: Name of skill with highest demand score (deterministic tie-breaking)
        """
        query = db.query(
            func.count(IndustrySkillDemand.id).label("total_skills"),
            func.avg(IndustrySkillDemand.demand_score).label("avg_demand"),
            func.max(IndustrySkillDemand.demand_score).label("max_demand"),
            func.min(IndustrySkillDemand.demand_score).label("min_demand"),
            func.avg(IndustrySkillDemand.growth_rate).label("avg_growth"),
        ).filter(IndustrySkillDemand.role_id == role_id)

        if location:
            query = query.filter(func.lower(IndustrySkillDemand.location) == location.strip().lower())

        stats = query.one()
        total_skills = stats.total_skills or 0
        if total_skills == 0:
            return {
                "total_demanded_skills": 0,
                "average_demand_score": 0.0,
                "highest_demand_score": 0.0,
                "lowest_demand_score": 0.0,
                "average_growth_rate": 0.0,
                "top_skill": None,
            }

        # Deterministically identify the highest demand skill
        top_row_query = (
            db.query(IndustrySkillDemand, Skill)
            .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
            .filter(IndustrySkillDemand.role_id == role_id)
        )
        if location:
            top_row_query = top_row_query.filter(
                func.lower(IndustrySkillDemand.location) == location.strip().lower()
            )
        top_row = top_row_query.order_by(
            IndustrySkillDemand.demand_score.desc(),
            Skill.name.asc(),
            Skill.id.asc(),
        ).first()

        top_skill_name = top_row[1].name if top_row else None

        return {
            "total_demanded_skills": int(total_skills),
            "average_demand_score": round(float(stats.avg_demand or 0.0), 2),
            "highest_demand_score": round(float(stats.max_demand or 0.0), 2),
            "lowest_demand_score": round(float(stats.min_demand or 0.0), 2),
            "average_growth_rate": round(float(stats.avg_growth or 0.0), 2),
            "top_skill": top_skill_name,
        }

    def get_role_demand_profile(
        self,
        db: Session,
        role_id: uuid.UUID,
        location: Optional[str] = "India",
    ) -> Optional[Tuple[JobRole, List[Dict[str, Any]], Dict[str, Any]]]:
        """
        Retrieves complete demand profile and SQL aggregates for a specific canonical job role.
        """
        role = self.get_job_role_by_id(db, role_id)
        if not role:
            return None

        query = (
            db.query(IndustrySkillDemand, Skill)
            .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
            .filter(IndustrySkillDemand.role_id == role_id)
        )
        if location:
            query = query.filter(func.lower(IndustrySkillDemand.location) == location.strip().lower())

        rows = query.order_by(
            IndustrySkillDemand.demand_score.desc(),
            Skill.name.asc(),
            Skill.id.asc(),
        ).all()

        skills = []
        for demand, skill in rows:
            dt_str = demand.data_updated_at.strftime("%Y-%m-%d") if demand.data_updated_at else "2026-09-01"
            skills.append(
                {
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "canonical_slug": skill.slug,
                    "category": skill.category,
                    "demand_score": round(demand.demand_score, 2),
                    "growth_rate": round(demand.growth_rate, 2),
                    "sample_size": demand.sample_size,
                    "location": demand.location,
                    "data_updated_at": dt_str,
                }
            )

        aggregates = self.get_role_demand_aggregates(db, role_id, location)

        return role, skills, aggregates

    def audit_demand_data_quality(self, db: Session) -> Dict[str, Any]:
        """
        Executes a deterministic data-quality and integrity audit on the demand dataset:
        1. Checks total canonical roles and demand records.
        2. Verifies zero orphaned demand records (missing job role or canonical skill).
        3. Verifies zero out-of-bounds demand_scores (outside [0.0, 1.0]).
        4. Verifies zero non-positive sample_sizes (<= 0).
        5. Verifies zero duplicate (role_id, skill_id, location) combinations.
        6. Verifies coverage across canonical job roles.
        """
        from datetime import datetime, timezone

        total_roles = db.query(JobRole).count()
        total_demand = db.query(IndustrySkillDemand).count()

        # Check for orphaned demand records referencing non-existent role
        orphan_role_records = (
            db.query(IndustrySkillDemand)
            .outerjoin(JobRole, IndustrySkillDemand.role_id == JobRole.id)
            .filter(JobRole.id.is_(None))
            .count()
        )

        # Check for orphaned demand records referencing non-existent skill
        orphan_skill_records = (
            db.query(IndustrySkillDemand)
            .outerjoin(Skill, IndustrySkillDemand.skill_id == Skill.id)
            .filter(Skill.id.is_(None))
            .count()
        )
        total_orphaned = orphan_role_records + orphan_skill_records

        # Check for out-of-bounds demand_scores
        out_of_bounds_scores = (
            db.query(IndustrySkillDemand)
            .filter(
                (IndustrySkillDemand.demand_score < 0.0) | (IndustrySkillDemand.demand_score > 1.0)
            )
            .count()
        )

        # Check for non-positive sample_sizes
        non_positive_sample_sizes = (
            db.query(IndustrySkillDemand)
            .filter(IndustrySkillDemand.sample_size <= 0)
            .count()
        )

        # Check for duplicates
        duplicate_groups = (
            db.query(
                IndustrySkillDemand.role_id,
                IndustrySkillDemand.skill_id,
                IndustrySkillDemand.location,
                func.count(IndustrySkillDemand.id).label("cnt"),
            )
            .group_by(
                IndustrySkillDemand.role_id,
                IndustrySkillDemand.skill_id,
                IndustrySkillDemand.location,
            )
            .having(func.count(IndustrySkillDemand.id) > 1)
            .count()
        )

        # Roles with at least one demand record
        roles_with_demand = (
            db.query(JobRole.id)
            .join(IndustrySkillDemand, JobRole.id == IndustrySkillDemand.role_id)
            .distinct()
            .count()
        )
        orphaned_roles = total_roles - roles_with_demand

        status_str = "VALID"
        if (
            total_orphaned > 0
            or out_of_bounds_scores > 0
            or non_positive_sample_sizes > 0
            or duplicate_groups > 0
            or orphaned_roles > 0
        ):
            status_str = "CORRUPTED"

        return {
            "status": status_str,
            "total_roles": total_roles,
            "total_demand_records": total_demand,
            "roles_with_demand": roles_with_demand,
            "orphaned_roles": orphaned_roles,
            "orphaned_demand_records": total_orphaned,
            "out_of_bounds_scores": out_of_bounds_scores,
            "non_positive_sample_sizes": non_positive_sample_sizes,
            "duplicate_records": duplicate_groups,
            "data_freshness": self.get_market_data_freshness(db),
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_market_data_freshness(self, db: Session) -> str:
        """
        Delegates directly to get_market_data_freshness(db) to avoid duplicate query logic.
        """
        return get_market_data_freshness(db)


demand_service = DemandService()

