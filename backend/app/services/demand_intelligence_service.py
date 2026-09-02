import uuid
from typing import List, Optional, Tuple, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import JobRole, IndustrySkillDemand, Skill


def classify_growth(growth_rate: float) -> str:
    """
    Deterministic classification based strictly on growth_rate:
    - RISING: growth_rate > 0.05
    - STABLE: -0.05 <= growth_rate <= 0.05
    - DECLINING: growth_rate < -0.05
    """
    if growth_rate > 0.05:
        return "RISING"
    elif growth_rate < -0.05:
        return "DECLINING"
    else:
        return "STABLE"


class DemandIntelligenceService:
    """
    Deterministic cross-role demand intelligence and ranking service.
    All quantitative metrics are derived strictly from PostgreSQL data.
    LLMs are prohibited from generating, modifying, or inferring demand metrics.
    """

    def get_skill_demand_ranking(
        self,
        db: Session,
        location: str = "India",
        role_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Ranks canonical skills by industry demand.
        - If role_id is provided: ranks skills for that specific role.
        - If role_id is None: calculates global skill demand across all roles weighted by sample size:
          weighted_average_demand = SUM(demand_score * sample_size) / SUM(sample_size).
        Ordered deterministically: demand_score DESC, skill_name ASC, skill_id ASC.
        """
        if role_id:
            # Rank skills for a specific role
            query = (
                db.query(IndustrySkillDemand, Skill)
                .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
                .filter(IndustrySkillDemand.role_id == role_id)
            )
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
            for demand, skill in rows:
                items.append(
                    {
                        "skill_id": skill.id,
                        "skill_name": skill.name,
                        "canonical_slug": skill.slug,
                        "category": skill.category,
                        "demand_score": round(demand.demand_score, 2),
                        "average_growth_rate": round(demand.growth_rate, 2),
                        "role_count": 1,
                        "total_sample_size": demand.sample_size,
                        "trend": classify_growth(demand.growth_rate),
                    }
                )
            return items, total

        # Global skill ranking across all roles
        weighted_expr = func.sum(IndustrySkillDemand.demand_score * IndustrySkillDemand.sample_size) / func.sum(
            IndustrySkillDemand.sample_size
        )

        query = (
            db.query(
                Skill.id.label("skill_id"),
                Skill.name.label("skill_name"),
                Skill.slug.label("canonical_slug"),
                Skill.category.label("category"),
                weighted_expr.label("weighted_demand"),
                func.avg(IndustrySkillDemand.growth_rate).label("avg_growth"),
                func.count(IndustrySkillDemand.role_id).label("role_count"),
                func.sum(IndustrySkillDemand.sample_size).label("total_sample_size"),
            )
            .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
        )

        if location:
            query = query.filter(func.lower(IndustrySkillDemand.location) == location.strip().lower())

        grouped_query = query.group_by(Skill.id, Skill.name, Skill.slug, Skill.category)

        # Count total distinct ranked skills
        subq = grouped_query.subquery()
        total = db.query(func.count()).select_from(subq).scalar() or 0

        rows = (
            grouped_query.order_by(
                weighted_expr.desc(),
                Skill.name.asc(),
                Skill.id.asc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = []
        for r in rows:
            w_score = float(r.weighted_demand) if r.weighted_demand is not None else 0.0
            avg_g = float(r.avg_growth) if r.avg_growth is not None else 0.0
            items.append(
                {
                    "skill_id": r.skill_id,
                    "skill_name": r.skill_name,
                    "canonical_slug": r.canonical_slug,
                    "category": r.category,
                    "demand_score": round(w_score, 2),
                    "average_growth_rate": round(avg_g, 2),
                    "role_count": int(r.role_count),
                    "total_sample_size": int(r.total_sample_size or 0),
                    "trend": classify_growth(avg_g),
                }
            )

        return items, total

    def get_skill_role_demand(
        self,
        db: Session,
        skill_id: uuid.UUID,
        location: str = "India",
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves the demand profile of one canonical skill across all job roles.
        Ordered deterministically: demand_score DESC, role_title ASC, role_id ASC.
        Returns None if the skill does not exist.
        """
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            return None

        query = (
            db.query(IndustrySkillDemand, JobRole)
            .join(JobRole, IndustrySkillDemand.role_id == JobRole.id)
            .filter(IndustrySkillDemand.skill_id == skill_id)
        )
        if location:
            query = query.filter(func.lower(IndustrySkillDemand.location) == location.strip().lower())

        rows = (
            query.order_by(
                IndustrySkillDemand.demand_score.desc(),
                JobRole.title.asc(),
                JobRole.id.asc(),
            )
            .all()
        )

        role_items = []
        scores = []
        for demand, role in rows:
            scores.append(demand.demand_score)
            role_items.append(
                {
                    "role_id": role.id,
                    "role_title": role.title,
                    "role_slug": role.slug,
                    "demand_score": round(demand.demand_score, 2),
                    "growth_rate": round(demand.growth_rate, 2),
                    "sample_size": demand.sample_size,
                    "trend": classify_growth(demand.growth_rate),
                    "location": demand.location,
                }
            )

        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        return {
            "skill": {
                "id": skill.id,
                "name": skill.name,
                "slug": skill.slug,
                "category": skill.category,
                "description": skill.description,
            },
            "roles": role_items,
            "average_demand_score": avg_score,
            "total_roles_demanding": len(role_items),
        }

    def compare_roles(
        self,
        db: Session,
        role_ids: List[uuid.UUID],
        location: str = "India",
    ) -> Dict[str, Any]:
        """
        Compares between 2 and 5 canonical job roles deterministically.
        Identifies:
        - Shared skills (demanded by every compared role).
        - Role-specific skills (demanded by only one compared role).
        - Detailed demand score and growth differentials.
        """
        if len(role_ids) < 2:
            raise ValueError("Role comparison requires at least 2 roles.")
        if len(role_ids) > 5:
            raise ValueError("Role comparison supports a maximum of 5 roles.")
        if len(set(role_ids)) != len(role_ids):
            raise ValueError("Duplicate role IDs are not permitted in role comparison.")

        # Verify all roles exist
        roles = db.query(JobRole).filter(JobRole.id.in_(role_ids)).all()
        if len(roles) != len(role_ids):
            found_ids = {r.id for r in roles}
            missing_ids = [str(rid) for rid in role_ids if rid not in found_ids]
            raise KeyError(f"Job roles not found: {', '.join(missing_ids)}")

        # Maintain original order of roles provided in request
        roles_map = {r.id: r for r in roles}
        ordered_roles = [roles_map[rid] for rid in role_ids]

        # Fetch demand records for all compared roles in a single query
        query = (
            db.query(IndustrySkillDemand, Skill, JobRole)
            .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
            .join(JobRole, IndustrySkillDemand.role_id == JobRole.id)
            .filter(IndustrySkillDemand.role_id.in_(role_ids))
        )
        if location:
            query = query.filter(func.lower(IndustrySkillDemand.location) == location.strip().lower())

        records = query.all()

        # Group demand by skill_id
        skill_info_map: Dict[uuid.UUID, Skill] = {}
        skill_role_demands: Dict[uuid.UUID, Dict[uuid.UUID, IndustrySkillDemand]] = {}
        role_demanded_skills: Dict[uuid.UUID, List[IndustrySkillDemand]] = {r.id: [] for r in ordered_roles}

        for dem, sk, rl in records:
            skill_info_map[sk.id] = sk
            if sk.id not in skill_role_demands:
                skill_role_demands[sk.id] = {}
            skill_role_demands[sk.id][rl.id] = dem
            role_demanded_skills[rl.id].append(dem)

        compared_role_items = []
        for r in ordered_roles:
            demands = role_demanded_skills[r.id]
            scores = [d.demand_score for d in demands]
            avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
            top_dem = (
                max(demands, key=lambda d: d.demand_score)
                if demands
                else None
            )
            top_skill_name = skill_info_map[top_dem.skill_id].name if top_dem else None

            compared_role_items.append(
                {
                    "role_id": r.id,
                    "title": r.title,
                    "slug": r.slug,
                    "category": r.category,
                    "total_demanded_skills": len(demands),
                    "average_demand_score": avg_score,
                    "top_skill": top_skill_name,
                }
            )

        shared_skills_list = []
        role_specific_map: Dict[str, List[Dict[str, Any]]] = {str(r.id): [] for r in ordered_roles}

        all_unique_skills = set(skill_role_demands.keys())
        target_role_count = len(ordered_roles)

        for sk_id, roles_dict in skill_role_demands.items():
            sk = skill_info_map[sk_id]
            if len(roles_dict) == target_role_count:
                # Skill is shared across ALL compared roles
                demands = list(roles_dict.values())
                scores = [d.demand_score for d in demands]
                growths = [d.growth_rate for d in demands]

                avg_dem = round(sum(scores) / len(scores), 2)
                diff = round(max(scores) - min(scores), 2)
                avg_gr = round(sum(growths) / len(growths), 2)

                demands_by_role = {}
                for r in ordered_roles:
                    d = roles_dict[r.id]
                    demands_by_role[str(r.id)] = {
                        "role_id": r.id,
                        "role_title": r.title,
                        "demand_score": round(d.demand_score, 2),
                        "growth_rate": round(d.growth_rate, 2),
                        "trend": classify_growth(d.growth_rate),
                    }

                shared_skills_list.append(
                    {
                        "skill_id": sk.id,
                        "skill_name": sk.name,
                        "canonical_slug": sk.slug,
                        "category": sk.category,
                        "average_demand_score": avg_dem,
                        "demand_score_diff": diff,
                        "average_growth_rate": avg_gr,
                        "demands_by_role": demands_by_role,
                    }
                )
            elif len(roles_dict) == 1:
                # Skill is specific to exactly ONE compared role
                sole_role_id = next(iter(roles_dict.keys()))
                d = roles_dict[sole_role_id]
                role_specific_map[str(sole_role_id)].append(
                    {
                        "skill_id": sk.id,
                        "skill_name": sk.name,
                        "canonical_slug": sk.slug,
                        "category": sk.category,
                        "demand_score": round(d.demand_score, 2),
                        "growth_rate": round(d.growth_rate, 2),
                        "trend": classify_growth(d.growth_rate),
                    }
                )

        # Deterministic ordering for shared skills: avg demand_score DESC, skill.name ASC, skill.id ASC
        shared_skills_list.sort(
            key=lambda x: (-x["average_demand_score"], x["skill_name"], str(x["skill_id"]))
        )

        # Deterministic ordering for role-specific skills: demand_score DESC, skill.name ASC, skill.id ASC
        for r_id_str in role_specific_map:
            role_specific_map[r_id_str].sort(
                key=lambda x: (-x["demand_score"], x["skill_name"], str(x["skill_id"]))
            )

        role_specific_counts = {r_id: len(skills) for r_id, skills in role_specific_map.items()}

        return {
            "roles": compared_role_items,
            "shared_skills": shared_skills_list,
            "role_specific_skills": role_specific_map,
            "comparison_summary": {
                "compared_roles_count": len(ordered_roles),
                "total_unique_skills": len(all_unique_skills),
                "shared_skills_count": len(shared_skills_list),
                "role_specific_counts": role_specific_counts,
            },
        }

    def get_role_market_signals(
        self,
        db: Session,
        role_id: uuid.UUID,
        location: str = "India",
    ) -> Optional[Dict[str, Any]]:
        """
        Calculates deterministic market-demand signals for a canonical job role:
        - Rising, stable, and declining skill counts.
        - Top 5 demanded skills.
        - Top 5 fastest growing skills.
        Returns None if role does not exist.
        """
        role = db.query(JobRole).filter(JobRole.id == role_id).first()
        if not role:
            return None

        query = (
            db.query(IndustrySkillDemand, Skill)
            .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
            .filter(IndustrySkillDemand.role_id == role_id)
        )
        if location:
            query = query.filter(func.lower(IndustrySkillDemand.location) == location.strip().lower())

        rows = query.all()

        if not rows:
            return {
                "role": {
                    "role_id": role.id,
                    "title": role.title,
                    "slug": role.slug,
                    "category": role.category,
                    "description": role.description,
                },
                "metrics": {
                    "total_demanded_skills": 0,
                    "average_demand_score": 0.0,
                    "highest_demand_score": 0.0,
                    "lowest_demand_score": 0.0,
                    "average_growth_rate": 0.0,
                    "rising_skill_count": 0,
                    "stable_skill_count": 0,
                    "declining_skill_count": 0,
                },
                "top_demanded_skills": [],
                "fastest_growing_skills": [],
            }

        scores = [d.demand_score for d, _ in rows]
        growths = [d.growth_rate for d, _ in rows]

        rising = 0
        stable = 0
        declining = 0

        skill_records = []
        for d, s in rows:
            tr = classify_growth(d.growth_rate)
            if tr == "RISING":
                rising += 1
            elif tr == "DECLINING":
                declining += 1
            else:
                stable += 1

            skill_records.append(
                {
                    "skill_id": s.id,
                    "skill_name": s.name,
                    "canonical_slug": s.slug,
                    "category": s.category,
                    "demand_score": round(d.demand_score, 2),
                    "growth_rate": round(d.growth_rate, 2),
                    "trend": tr,
                }
            )

        # Top 5 demanded skills
        top_demanded = sorted(
            skill_records,
            key=lambda x: (-x["demand_score"], x["skill_name"], str(x["skill_id"])),
        )[:5]

        # Top 5 fastest growing skills
        fastest_growing = sorted(
            skill_records,
            key=lambda x: (-x["growth_rate"], x["skill_name"], str(x["skill_id"])),
        )[:5]

        return {
            "role": {
                "role_id": role.id,
                "title": role.title,
                "slug": role.slug,
                "category": role.category,
                "description": role.description,
            },
            "metrics": {
                "total_demanded_skills": len(rows),
                "average_demand_score": round(sum(scores) / len(scores), 2),
                "highest_demand_score": round(max(scores), 2),
                "lowest_demand_score": round(min(scores), 2),
                "average_growth_rate": round(sum(growths) / len(growths), 2),
                "rising_skill_count": rising,
                "stable_skill_count": stable,
                "declining_skill_count": declining,
            },
            "top_demanded_skills": top_demanded,
            "fastest_growing_skills": fastest_growing,
        }

    def get_demand_trends(
        self,
        db: Session,
        location: str = "India",
        role_id: Optional[uuid.UUID] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves demand records enriched with growth trends (RISING, STABLE, DECLINING).
        Ordered deterministically:
        growth_rate DESC, demand_score DESC, skill.name ASC, skill.id ASC.
        """
        query = (
            db.query(IndustrySkillDemand, Skill, JobRole)
            .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
            .join(JobRole, IndustrySkillDemand.role_id == JobRole.id)
        )

        if location:
            query = query.filter(func.lower(IndustrySkillDemand.location) == location.strip().lower())
        if role_id:
            query = query.filter(IndustrySkillDemand.role_id == role_id)

        total = query.count()

        rows = (
            query.order_by(
                IndustrySkillDemand.growth_rate.desc(),
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
            items.append(
                {
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "canonical_slug": skill.slug,
                    "category": skill.category,
                    "role_id": role.id,
                    "role_title": role.title,
                    "demand_score": round(demand.demand_score, 2),
                    "growth_rate": round(demand.growth_rate, 2),
                    "trend": classify_growth(demand.growth_rate),
                    "location": demand.location,
                    "sample_size": demand.sample_size,
                }
            )

        return items, total


demand_intelligence_service = DemandIntelligenceService()
