"""
Roadmap Orchestration Service for SkillForge AI.
Post-MVP Phase 4.

Coordinates:
- Candidate authentication and ownership validation (IDOR defense).
- Deterministic skill gap retrieval via SkillGapService.
- Dependency graph loading and validation.
- Approved resource and project catalog lookups.
- Execution of the deterministic RoadmapEngine.
- In-memory execution for anonymous candidates vs transactional persistence for authenticated candidates.
"""

from collections import defaultdict
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import (
    ApprovedProject,
    ApprovedResource,
    CandidateRoadmap,
    DemonstratedSkill,
    GitHubRepository,
    IndustrySkillDemand,
    JobRole,
    MarketSkillDemand,
    MarketSkillDemandGrowth,
    Resume,
    RoadmapMilestone,
    Skill,
    SkillDependency,
    SkillGap,
    User,
    UserClaimedSkill,
)
from app.schemas.roadmap import (
    CanonicalRoadmapData,
    DependencyType,
    MilestoneStatus,
    RoadmapGenerateRequest,
    RoadmapLifecycleStatus,
    RoadmapMilestoneItem,
    RoadmapPrerequisiteItem,
    RoadmapProjectItem,
    RoadmapResourceItem,
)
from app.services.roadmap_engine import RoadmapEngine
from app.services.skill_gap_service import (
    SkillGapService,
    classify_skill_gap,
    skill_gap_service,
)

logger = logging.getLogger(__name__)


class RoadmapService:
    """Orchestrates candidate roadmap generation, authorization, and persistence."""

    def __init__(self, gap_service: Optional[SkillGapService] = None):
        self.gap_service = gap_service or skill_gap_service

    def verify_candidate_ownership(
        self,
        db: Session,
        user_id: Optional[UUID],
        resume_id: Optional[UUID],
        github_username: Optional[str],
    ) -> None:
        """
        Enforces candidate data ownership:
        1. If user_id is provided, verifies user exists.
        2. If resume_id is provided, verifies it belongs to user_id (403 on IDOR mismatch).
        3. If github_username is provided and user_id is provided, verifies no cross-user repository collision.
        4. If user_id is None (anonymous), ensures resume and github data are not owned by an authenticated user.
        """
        if user_id is not None:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id '{user_id}' not found.",
                )

        if resume_id is not None:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Resume with id '{resume_id}' not found.",
                )
            if user_id is not None:
                if resume.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cross-user access denied: target resume does not belong to authenticated user context.",
                    )
            else:
                if resume.user_id is not None:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cross-user access denied: target resume belongs to an authenticated user.",
                    )

        if github_username is not None and github_username.strip():
            clean_username = github_username.strip().lower()
            # Check if repositories under this handle are owned by a different authenticated user
            foreign_repo = (
                db.query(GitHubRepository)
                .filter(
                    func.lower(GitHubRepository.full_name).startswith(f"{clean_username}/"),
                    GitHubRepository.user_id.isnot(None),
                )
                .first()
            )
            if foreign_repo:
                if user_id is None or foreign_repo.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cross-user access denied: GitHub username belongs to another authenticated candidate.",
                    )

    def generate_candidate_roadmap(
        self,
        db: Session,
        request: RoadmapGenerateRequest,
        resolved_user_id: Optional[UUID],
    ) -> CanonicalRoadmapData:
        """
        Generates a canonical roadmap for the candidate.
        If resolved_user_id is present, persists the roadmap to PostgreSQL.
        If resolved_user_id is None, generates in-memory and returns without persistence.
        """
        # Step 1: Strict Ownership and IDOR Verification
        self.verify_candidate_ownership(
            db=db,
            user_id=resolved_user_id,
            resume_id=request.resume_id,
            github_username=request.github_username,
        )

        role = db.query(JobRole).filter(JobRole.id == request.role_id).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job role with id '{request.role_id}' not found.",
            )

        # Step 2: Retrieve candidate actionable gaps & mastered skills using existing SkillGapService
        _, _, all_gap_items = self.gap_service.compute_and_persist_skill_gaps(
            db=db,
            role_id=request.role_id,
            user_id=resolved_user_id,
            location=request.location,
            include_resume=request.include_resume,
            include_github=request.include_github,
            github_username=request.github_username,
            resume_id=request.resume_id,
        )

        _, _, actionable_gaps = self.gap_service.get_prioritized_gaps(
            db=db,
            role_id=request.role_id,
            user_id=resolved_user_id,
            location=request.location,
            include_resume=request.include_resume,
            include_github=request.include_github,
            github_username=request.github_username,
            resume_id=request.resume_id,
        )

        # Identify skills where candidate already possesses STRONG evidence
        strong_skill_ids: Set[UUID] = {
            item.skill_id for item in all_gap_items if item.status == "STRONG"
        }

        # Step 3: Load all canonical skills, dependencies, approved resources, and projects
        skills = db.query(Skill).all()
        all_skills_map: Dict[UUID, Skill] = {s.id: s for s in skills}

        dependencies = db.query(SkillDependency).all()
        approved_res_rows = db.query(ApprovedResource).filter(ApprovedResource.is_approved == True).all()
        approved_resources_map: Dict[UUID, List[ApprovedResource]] = {}
        for res in approved_res_rows:
            approved_resources_map.setdefault(res.skill_id, []).append(res)

        approved_proj_rows = db.query(ApprovedProject).all()
        approved_projects_map: Dict[UUID, List[ApprovedProject]] = {}
        for proj in approved_proj_rows:
            approved_projects_map.setdefault(proj.skill_id, []).append(proj)

        # Step 4: Gather candidate & market facts for potential transitive-only prerequisites
        transitive_candidate_facts: Dict[UUID, Tuple[str, float]] = {}
        transitive_market_facts: Dict[UUID, Tuple[Optional[float], Optional[float]]] = {}

        for skill in skills:
            # Candidate claims
            claimed = False
            claim_conf = 0.0
            if request.include_resume:
                claimed_query = db.query(UserClaimedSkill).filter(UserClaimedSkill.skill_id == skill.id)
                if request.resume_id:
                    claimed_query = claimed_query.filter(UserClaimedSkill.resume_id == request.resume_id)
                elif resolved_user_id:
                    claimed_query = claimed_query.filter(UserClaimedSkill.user_id == resolved_user_id)
                c_record = claimed_query.first()
                if c_record:
                    claimed = True
                    claim_conf = c_record.confidence_score

            # Candidate code demonstration
            demonstrated = False
            demo_score = 0.0
            ev_level = None
            if request.include_github:
                demo_query = db.query(DemonstratedSkill).filter(DemonstratedSkill.skill_id == skill.id)
                if resolved_user_id:
                    demo_query = demo_query.filter(DemonstratedSkill.user_id == resolved_user_id)
                d_record = demo_query.first()
                if d_record:
                    demonstrated = True
                    demo_score = d_record.confidence_score
                    ev_level = d_record.evidence_level

            cand_status = classify_skill_gap(
                claimed=claimed,
                claim_confidence=claim_conf,
                demonstrated=demonstrated,
                demonstrated_score=demo_score,
                evidence_level=ev_level,
            )
            transitive_candidate_facts[skill.id] = (cand_status, demo_score)
            if cand_status == "STRONG":
                strong_skill_ids.add(skill.id)

            # Market facts for transitive skills
            mkt_record = (
                db.query(MarketSkillDemand)
                .filter(MarketSkillDemand.skill_id == skill.id)
                .first()
            )
            if mkt_record:
                growth_record = (
                    db.query(MarketSkillDemandGrowth)
                    .filter(MarketSkillDemandGrowth.skill_id == skill.id)
                    .first()
                )
                mkt_growth = growth_record.growth_rate if growth_record else 0.0
                transitive_market_facts[skill.id] = (mkt_record.demand_score, mkt_growth)
            else:
                # Fallback to industry demand table
                ind_record = (
                    db.query(IndustrySkillDemand)
                    .filter(IndustrySkillDemand.skill_id == skill.id)
                    .first()
                )
                if ind_record:
                    transitive_market_facts[skill.id] = (ind_record.demand_score, ind_record.growth_rate)
                else:
                    transitive_market_facts[skill.id] = (None, None)

        # Step 5: Execute pure deterministic RoadmapEngine
        is_persisted = (resolved_user_id is not None)
        canonical_roadmap = RoadmapEngine.generate_roadmap(
            target_role_id=role.id,
            target_role_title=role.title,
            location=request.location,
            actionable_gaps=actionable_gaps,
            strong_skill_ids=strong_skill_ids,
            all_skills_map=all_skills_map,
            dependencies=dependencies,
            approved_resources=approved_resources_map,
            approved_projects=approved_projects_map,
            transitive_skill_market_facts=transitive_market_facts,
            transitive_candidate_gap_facts=transitive_candidate_facts,
            user_id=resolved_user_id,
            persisted=is_persisted,
        )

        # Step 6: Persistence for Authenticated Users (Correction 3)
        if is_persisted and resolved_user_id:
            # Archive prior active roadmaps for this role and candidate
            db.query(CandidateRoadmap).filter(
                CandidateRoadmap.user_id == resolved_user_id,
                CandidateRoadmap.role_id == role.id,
                CandidateRoadmap.status == "ACTIVE",
            ).update({"status": "ARCHIVED"})

            now = datetime.now(timezone.utc)
            db_roadmap = CandidateRoadmap(
                user_id=resolved_user_id,
                role_id=role.id,
                target_role_title=role.title,
                location=request.location,
                status="ACTIVE",
                roadmap_version="v1",
                summary_metadata={
                    "total_milestones": canonical_roadmap.total_milestones,
                    "high_priority_count": canonical_roadmap.high_priority_count,
                    "medium_priority_count": canonical_roadmap.medium_priority_count,
                    "low_priority_count": canonical_roadmap.low_priority_count,
                    "transitive_prerequisite_count": canonical_roadmap.transitive_prerequisite_count,
                },
                created_at=now,
                updated_at=now,
            )
            db.add(db_roadmap)
            db.flush()

            persisted_milestones: List[RoadmapMilestoneItem] = []
            for m in canonical_roadmap.milestones:
                db_milestone = RoadmapMilestone(
                    roadmap_id=db_roadmap.id,
                    skill_id=m.skill_id,
                    order_index=m.order_index,
                    status=MilestoneStatus.NOT_STARTED.value,
                    gap_status=m.gap_status,
                    priority_score=m.priority_score,
                    priority_level=m.priority_level,
                    reason=m.reason,
                    project_id=m.project.id if m.project else None,
                    milestone_metadata={
                        "is_transitive_prerequisite": m.is_transitive_prerequisite,
                        "demonstrated_score": m.demonstrated_score,
                        "demand_score": m.demand_score,
                        "growth_rate": m.growth_rate,
                        "learning_objectives": list(m.learning_objectives),
                    },
                    created_at=now,
                    updated_at=now,
                )
                db.add(db_milestone)
                db.flush()

                # Reconstruct milestone with assigned DB id
                persisted_milestones.append(
                    RoadmapMilestoneItem(
                        milestone_id=db_milestone.id,
                        order_index=m.order_index,
                        skill_id=m.skill_id,
                        skill_name=m.skill_name,
                        canonical_slug=m.canonical_slug,
                        category=m.category,
                        gap_status=m.gap_status,
                        demonstrated_score=m.demonstrated_score,
                        demand_score=m.demand_score,
                        growth_rate=m.growth_rate,
                        priority_score=m.priority_score,
                        priority_level=m.priority_level,
                        is_transitive_prerequisite=m.is_transitive_prerequisite,
                        reason=m.reason,
                        prerequisites=m.prerequisites,
                        learning_objectives=m.learning_objectives,
                        resources=m.resources,
                        project=m.project,
                        status=MilestoneStatus.NOT_STARTED,
                    )
                )

            db.commit()

            return CanonicalRoadmapData(
                id=db_roadmap.id,
                user_id=resolved_user_id,
                role_id=role.id,
                target_role_title=role.title,
                location=request.location,
                status=RoadmapLifecycleStatus.ACTIVE,
                roadmap_version="v1",
                persisted=True,
                total_milestones=canonical_roadmap.total_milestones,
                high_priority_count=canonical_roadmap.high_priority_count,
                medium_priority_count=canonical_roadmap.medium_priority_count,
                low_priority_count=canonical_roadmap.low_priority_count,
                transitive_prerequisite_count=canonical_roadmap.transitive_prerequisite_count,
                milestones=tuple(persisted_milestones),
                generated_at=now,
            )

        # Anonymous/demo path: return in-memory without persistence
        return canonical_roadmap

    def get_roadmap_by_id(
        self,
        db: Session,
        roadmap_id: UUID,
        resolved_user_id: Optional[UUID],
    ) -> CanonicalRoadmapData:
        """
        Retrieves a persisted canonical roadmap by ID.
        Requires authenticated resolved_user_id matching roadmap.user_id.
        """
        if resolved_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to retrieve persisted roadmaps.",
            )

        roadmap = db.query(CandidateRoadmap).filter(CandidateRoadmap.id == roadmap_id).first()
        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roadmap with id '{roadmap_id}' not found.",
            )

        # Enforce strict IDOR isolation
        if roadmap.user_id != resolved_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-user access denied: target roadmap does not belong to authenticated user.",
            )

        return self._serialize_persisted_roadmap(db, roadmap)

    def get_active_roadmap(
        self,
        db: Session,
        role_id: UUID,
        resolved_user_id: Optional[UUID],
    ) -> CanonicalRoadmapData:
        """Retrieves candidate's latest active roadmap for a target role."""
        if resolved_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to retrieve active roadmaps.",
            )

        roadmap = (
            db.query(CandidateRoadmap)
            .filter(
                CandidateRoadmap.user_id == resolved_user_id,
                CandidateRoadmap.role_id == role_id,
                CandidateRoadmap.status == "ACTIVE",
            )
            .order_by(CandidateRoadmap.created_at.desc())
            .first()
        )
        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active roadmap found for target role '{role_id}'.",
            )

        return self._serialize_persisted_roadmap(db, roadmap)

    def _serialize_persisted_roadmap(
        self,
        db: Session,
        roadmap: CandidateRoadmap,
    ) -> CanonicalRoadmapData:
        """Serializes a CandidateRoadmap ORM instance into frozen CanonicalRoadmapData."""
        milestone_rows = (
            db.query(RoadmapMilestone, Skill)
            .join(Skill, RoadmapMilestone.skill_id == Skill.id)
            .filter(RoadmapMilestone.roadmap_id == roadmap.id)
            .order_by(RoadmapMilestone.order_index.asc())
            .all()
        )

        all_dependencies = db.query(SkillDependency).all()
        dep_map: Dict[UUID, List[SkillDependency]] = defaultdict(list)
        for dep in all_dependencies:
            dep_map[dep.skill_id].append(dep)

        approved_res = db.query(ApprovedResource).filter(ApprovedResource.is_approved == True).all()
        res_map: Dict[UUID, List[ApprovedResource]] = defaultdict(list)
        for r in approved_res:
            res_map[r.skill_id].append(r)

        skills = db.query(Skill).all()
        all_skills = {s.id: s for s in skills}

        milestone_items: List[RoadmapMilestoneItem] = []
        high_cnt = 0
        med_cnt = 0
        low_cnt = 0
        trans_cnt = 0

        for m_row, skill in milestone_rows:
            meta = m_row.milestone_metadata or {}
            is_trans = meta.get("is_transitive_prerequisite", False)
            if is_trans:
                trans_cnt += 1
            else:
                if m_row.priority_level == "HIGH":
                    high_cnt += 1
                elif m_row.priority_level == "MEDIUM":
                    med_cnt += 1
                elif m_row.priority_level == "LOW":
                    low_cnt += 1

            # Prerequisites
            prereqs = []
            for dep in dep_map.get(skill.id, []):
                p_entity = all_skills.get(dep.prerequisite_skill_id)
                dep_type_enum = DependencyType.HARD if str(dep.dependency_type).upper() == "HARD" else DependencyType.RECOMMENDED
                prereqs.append(
                    RoadmapPrerequisiteItem(
                        skill_id=dep.prerequisite_skill_id,
                        skill_name=getattr(p_entity, "name", str(dep.prerequisite_skill_id)),
                        canonical_slug=getattr(p_entity, "slug", str(dep.prerequisite_skill_id)),
                        dependency_type=dep_type_enum,
                        is_satisfied=False,
                    )
                )

            # Resources
            resources = [
                RoadmapResourceItem(
                    id=r.id,
                    title=r.title,
                    url=r.url,
                    resource_type=r.resource_type,
                    provider=r.provider,
                    difficulty=r.difficulty,
                    estimated_minutes=r.estimated_minutes,
                )
                for r in res_map.get(skill.id, [])
            ]

            # Project
            proj_item = None
            if m_row.project_id:
                p_row = db.query(ApprovedProject).filter(ApprovedProject.id == m_row.project_id).first()
                if p_row:
                    delivs = p_row.deliverables if isinstance(p_row.deliverables, list) else []
                    crit = p_row.verification_criteria if isinstance(p_row.verification_criteria, list) else []
                    proj_item = RoadmapProjectItem(
                        id=p_row.id,
                        title=p_row.title,
                        description=p_row.description,
                        difficulty=p_row.difficulty,
                        deliverables=tuple(delivs),
                        verification_criteria=tuple(crit),
                        estimated_hours=p_row.estimated_hours,
                    )

            milestone_items.append(
                RoadmapMilestoneItem(
                    milestone_id=m_row.id,
                    order_index=m_row.order_index,
                    skill_id=skill.id,
                    skill_name=skill.name,
                    canonical_slug=skill.slug,
                    category=skill.category,
                    gap_status=m_row.gap_status,
                    demonstrated_score=meta.get("demonstrated_score", 0.0),
                    demand_score=meta.get("demand_score"),
                    growth_rate=meta.get("growth_rate"),
                    priority_score=m_row.priority_score,
                    priority_level=m_row.priority_level,
                    is_transitive_prerequisite=is_trans,
                    reason=m_row.reason,
                    prerequisites=tuple(prereqs),
                    learning_objectives=tuple(meta.get("learning_objectives", [])),
                    resources=tuple(resources),
                    project=proj_item,
                    status=MilestoneStatus(m_row.status),
                )
            )

        return CanonicalRoadmapData(
            id=roadmap.id,
            user_id=roadmap.user_id,
            role_id=roadmap.role_id,
            target_role_title=roadmap.target_role_title,
            location=roadmap.location,
            status=RoadmapLifecycleStatus(roadmap.status),
            roadmap_version=roadmap.roadmap_version,
            persisted=True,
            total_milestones=len(milestone_items),
            high_priority_count=high_cnt,
            medium_priority_count=med_cnt,
            low_priority_count=low_cnt,
            transitive_prerequisite_count=trans_cnt,
            milestones=tuple(milestone_items),
            generated_at=roadmap.created_at,
        )


roadmap_service = RoadmapService()
