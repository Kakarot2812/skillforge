"""
Verified Roadmap PDF Context Builder Service for SkillForge AI.
Post-MVP Career Roadmap PDF Feature (Phase 2).

Responsibilities:
- Enforce strict candidate ownership (IDOR defense).
- Assemble deterministic candidate identity facts without fabricating missing values.
- Re-use canonical RoadmapService to obtain the authoritative sequenced DAG roadmap.
- Re-use canonical SkillGapService to obtain deterministic readiness metrics, gap classifications,
  and priority rankings.
- Preserve curated ApprovedResource and ApprovedProject references without confusing curated challenges
  with candidate skill proof (is_candidate_proof=False).
- Collect candidate verification evidence (claims, repository demonstrations, milestone verifications).
- Compute deterministic SHA-256 verification hash over canonical facts.
- Return an immutable, bounded, pure Pydantic VerifiedRoadmapPDFContext.
- ZERO LLM calls, ZERO natural-language generation, ZERO PDF rendering.
"""

from collections import defaultdict
import logging
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.context.roadmap_pdf_context import (
    EvidenceStatusType,
    PriorityTierLevel,
    SkillGapClassification,
    VerifiedApprovedProject,
    VerifiedApprovedResource,
    VerifiedCandidateEvidenceItem,
    VerifiedCandidateProfile,
    VerifiedMarketDemandFact,
    VerifiedPrioritizedGapsSummary,
    VerifiedReadinessMetrics,
    VerifiedRoadmapMilestoneContext,
    VerifiedRoadmapPDFContext,
    VerifiedRoadmapPrerequisite,
    VerifiedRoadmapSummary,
    VerifiedSkillGapFact,
    generate_deterministic_verification_hash,
)
from app.db.models import (
    ApprovedProject,
    ApprovedResource,
    CandidateRoadmap,
    DemonstratedSkill,
    IndustrySkillDemand,
    JobRole,
    MilestoneVerification,
    ProjectEvidence,
    RoadmapMilestone,
    Skill,
    User,
    UserClaimedSkill,
    UserProfile,
)
from app.schemas.roadmap import CanonicalRoadmapData
from app.services.roadmap_service import RoadmapService, roadmap_service as default_roadmap_service
from app.services.skill_gap_service import (
    ACTIONABLE_STATUS_SORT_RANK,
    SkillGapService,
    skill_gap_service as default_skill_gap_service,
)

logger = logging.getLogger(__name__)


class RoadmapPDFContextService:
    """
    Deterministic context builder service for the personalized career roadmap PDF.
    Aggregates existing authoritative SkillForge data into an immutable Pydantic context.
    """

    def __init__(
        self,
        roadmap_svc: Optional[RoadmapService] = None,
        gap_svc: Optional[SkillGapService] = None,
    ):
        self.roadmap_service = roadmap_svc or default_roadmap_service
        self.gap_service = gap_svc or default_skill_gap_service

    def build_verified_context(
        self,
        db: Session,
        roadmap_id: UUID,
        authenticated_user_id: Optional[UUID],
    ) -> VerifiedRoadmapPDFContext:
        """
        Builds the immutable VerifiedRoadmapPDFContext for a candidate's roadmap.

        Enforces:
        - Strict authentication (401 Unauthorized if authenticated_user_id is None).
        - Existence check (404 Not Found if roadmap does not exist).
        - Candidate ownership / IDOR defense (403 Forbidden if roadmap belongs to another user).
        - Zero LLM invocation, zero fabricated values.
        """
        # 1. Enforce Authentication
        if authenticated_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required to access roadmap PDF context.",
            )

        # 2. Query and Authorize Roadmap (IDOR Defense)
        db_roadmap = db.query(CandidateRoadmap).filter(CandidateRoadmap.id == roadmap_id).first()
        if not db_roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Roadmap with id '{roadmap_id}' not found.",
            )

        if db_roadmap.user_id != authenticated_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cross-user access denied: target roadmap does not belong to authenticated user context.",
            )

        # 3. Retrieve Candidate User & Profile
        user = db.query(User).filter(User.id == authenticated_user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{authenticated_user_id}' not found.",
            )

        profile = db.query(UserProfile).filter(UserProfile.user_id == authenticated_user_id).first()

        candidate_profile = VerifiedCandidateProfile(
            user_id=user.id,
            email=user.email,
            name=profile.name if profile and profile.name else user.full_name,
            target_role=profile.target_role if profile and profile.target_role else (user.target_role or db_roadmap.target_role_title),
            experience_level=profile.experience_level if profile else None,
            college=profile.college if profile else None,
            degree=profile.degree if profile else None,
            branch=profile.branch if profile else None,
            semester=profile.semester if profile else None,
            education=profile.education if profile else None,
        )

        # 4. Re-use Canonical RoadmapService to Obtain Authoritative Roadmap
        canonical_roadmap: CanonicalRoadmapData = self.roadmap_service.get_roadmap_by_id(
            db=db,
            roadmap_id=roadmap_id,
            resolved_user_id=authenticated_user_id,
        )

        # 5. Re-use Canonical SkillGapService to Obtain Deterministic Gaps & Readiness
        summary_meta = db_roadmap.summary_metadata or {}
        location = db_roadmap.location or "India"
        resume_id_str = summary_meta.get("resume_id")
        resume_id = UUID(resume_id_str) if resume_id_str else None
        include_resume = summary_meta.get("include_resume", True)
        include_github = summary_meta.get("include_github", True)
        github_username = summary_meta.get("github_username")

        # Canonical gap calculation
        _, gap_summary, gap_items = self.gap_service.compute_and_persist_skill_gaps(
            db=db,
            role_id=db_roadmap.role_id,
            user_id=authenticated_user_id,
            location=location,
            include_resume=include_resume,
            include_github=include_github,
            github_username=github_username,
            resume_id=resume_id,
        )

        # Canonical readiness percentage
        total_req = gap_summary.total_required_skills
        readiness_pct = (
            round((gap_summary.strong_count / total_req) * 100)
            if total_req > 0
            else 0
        )

        readiness_metrics = VerifiedReadinessMetrics(
            readiness_percentage=readiness_pct,
            total_required_skills=total_req,
            strong_count=gap_summary.strong_count,
            partial_count=gap_summary.partial_count,
            missing_count=gap_summary.missing_count,
            has_resume=include_resume and bool(resume_id or user.resumes),
            has_github=include_github and bool(github_username or user.github_repositories),
            scoring_version="v1",
        )

        # Canonical prioritized actionable gaps
        _, prio_summary, prio_items = self.gap_service.get_prioritized_gaps(
            db=db,
            role_id=db_roadmap.role_id,
            user_id=authenticated_user_id,
            location=location,
            include_resume=include_resume,
            include_github=include_github,
            github_username=github_username,
            resume_id=resume_id,
        )

        # Assemble prioritized gaps summary
        top_gap_facts: List[VerifiedSkillGapFact] = []
        for p in prio_items:
            tier_enum = PriorityTierLevel(p.priority_level) if p.priority_level in PriorityTierLevel.__members__ else None
            top_gap_facts.append(
                VerifiedSkillGapFact(
                    skill_id=p.skill_id,
                    skill_name=p.skill_name,
                    canonical_slug=p.canonical_slug,
                    category=p.category,
                    gap_status=SkillGapClassification(p.status),
                    claimed=p.claimed,
                    claim_confidence=p.claim_confidence,
                    demonstrated=p.demonstrated,
                    demonstrated_score=p.demonstrated_score,
                    evidence_level=p.evidence_level,
                    evidence_count=p.evidence_count,
                    demand_score=p.demand_score,
                    growth_rate=p.growth_rate,
                    priority_score=p.priority_score,
                    priority_level=tier_enum,
                    deterministic_explanation=p.explanation,
                )
            )

        prioritized_gaps_summary = VerifiedPrioritizedGapsSummary(
            total_actionable_gaps=prio_summary.total_actionable_gaps,
            high_priority_count=prio_summary.high_priority_count,
            medium_priority_count=prio_summary.medium_priority_count,
            low_priority_count=prio_summary.low_priority_count,
            top_gaps=tuple(top_gap_facts),
        )

        # Assemble all role skill gaps (including STRONG skills)
        all_gap_facts: List[VerifiedSkillGapFact] = []
        for g in gap_items:
            tier_enum = PriorityTierLevel(g.priority_level) if g.priority_level in PriorityTierLevel.__members__ else None
            all_gap_facts.append(
                VerifiedSkillGapFact(
                    skill_id=g.skill_id,
                    skill_name=g.skill_name,
                    canonical_slug=g.canonical_slug,
                    category=g.category,
                    gap_status=SkillGapClassification(g.status),
                    claimed=g.claimed,
                    claim_confidence=g.claim_confidence,
                    demonstrated=g.demonstrated,
                    demonstrated_score=g.demonstrated_score,
                    evidence_level=g.evidence_level,
                    evidence_count=g.evidence_count,
                    demand_score=g.demand_score,
                    growth_rate=g.growth_rate,
                    priority_score=g.priority_score,
                    priority_level=tier_enum,
                    deterministic_explanation=None,
                )
            )

        # Deterministic sorting for all gap facts
        all_gap_facts.sort(
            key=lambda x: (
                ACTIONABLE_STATUS_SORT_RANK.get(x.gap_status.value, 99),
                -(x.priority_score or 0.0),
                -(x.demand_score or 0.0),
                x.skill_name.lower(),
                str(x.skill_id),
            )
        )

        # 6. Assemble Industry Market Demand Facts (Supporting Evidence)
        demanded_rows = (
            db.query(IndustrySkillDemand, Skill)
            .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
            .filter(
                IndustrySkillDemand.role_id == db_roadmap.role_id,
                func.lower(IndustrySkillDemand.location) == location.strip().lower(),
            )
            .order_by(IndustrySkillDemand.demand_score.desc(), Skill.name.asc())
            .all()
        )

        market_facts: List[VerifiedMarketDemandFact] = []
        for demand, skill in demanded_rows:
            if demand.growth_rate > 0.05:
                g_class = "RISING"
            elif demand.growth_rate < -0.05:
                g_class = "DECLINING"
            else:
                g_class = "STABLE"

            market_facts.append(
                VerifiedMarketDemandFact(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    canonical_slug=skill.slug,
                    demand_score=round(demand.demand_score, 4),
                    growth_rate=round(demand.growth_rate, 4),
                    growth_class=g_class,
                    location=demand.location,
                    data_source="adzuna",
                    freshness=demand.updated_at.strftime("%Y-%m-%d") if demand.updated_at else None,
                )
            )

        # 7. Collect Candidate Verification Evidence (Authoritative Proof)
        verifications = (
            db.query(MilestoneVerification)
            .filter(
                MilestoneVerification.roadmap_id == db_roadmap.id,
                MilestoneVerification.user_id == authenticated_user_id,
            )
            .order_by(MilestoneVerification.created_at.desc(), MilestoneVerification.id.asc())
            .all()
        )

        # Map latest verification per milestone
        latest_milestone_verif: Dict[UUID, VerifiedCandidateEvidenceItem] = {}
        verification_evidence_list: List[VerifiedCandidateEvidenceItem] = []

        skill_id_to_name = {s.id: s.name for _, s in demanded_rows}

        for v in verifications:
            # Resolve skill name from milestone
            milestone_row = db.query(RoadmapMilestone).filter(RoadmapMilestone.id == v.milestone_id).first()
            s_name = "Unknown Skill"
            s_id = v.milestone_id
            if milestone_row:
                s_id = milestone_row.skill_id
                s_name = skill_id_to_name.get(s_id, f"Skill-{str(s_id)[:8]}")

            ev_item = VerifiedCandidateEvidenceItem(
                evidence_id=v.id,
                skill_id=s_id,
                skill_name=s_name,
                evidence_type=EvidenceStatusType.VERIFIED,
                source="MILESTONE_VERIFICATION",
                status=v.status,
                confidence=v.confidence,
                artifact_reference=v.commit_sha,
                milestone_id=v.milestone_id,
            )
            verification_evidence_list.append(ev_item)
            if v.milestone_id not in latest_milestone_verif:
                latest_milestone_verif[v.milestone_id] = ev_item

        # Also collect DemonstratedSkill and UserClaimedSkill evidence items
        demo_skills = db.query(DemonstratedSkill, Skill).join(Skill, DemonstratedSkill.skill_id == Skill.id).filter(DemonstratedSkill.user_id == authenticated_user_id).all()
        for ds, sk in demo_skills:
            verification_evidence_list.append(
                VerifiedCandidateEvidenceItem(
                    evidence_id=ds.id,
                    skill_id=sk.id,
                    skill_name=sk.name,
                    evidence_type=EvidenceStatusType.DEMONSTRATED,
                    source="GITHUB",
                    status=ds.evidence_level or "DEMONSTRATED",
                    confidence=ds.confidence_score,
                    artifact_reference=f"{ds.repository_count} repositories, {ds.evidence_count} artifacts",
                    milestone_id=None,
                )
            )

        claimed_skills = db.query(UserClaimedSkill, Skill).join(Skill, UserClaimedSkill.skill_id == Skill.id).filter(UserClaimedSkill.user_id == authenticated_user_id).all()
        for cs, sk in claimed_skills:
            verification_evidence_list.append(
                VerifiedCandidateEvidenceItem(
                    evidence_id=cs.id,
                    skill_id=sk.id,
                    skill_name=sk.name,
                    evidence_type=EvidenceStatusType.CLAIMED,
                    source="RESUME",
                    status="CLAIMED",
                    confidence=cs.confidence_score,
                    artifact_reference=cs.raw_mention,
                    milestone_id=None,
                )
            )

        # Deterministic sorting for verification evidence
        verification_evidence_list.sort(
            key=lambda x: (
                x.evidence_type.value,
                x.skill_name.lower(),
                str(x.evidence_id),
            )
        )

        # 8. Assemble Ordered Milestones
        milestone_contexts: List[VerifiedRoadmapMilestoneContext] = []
        milestone_hash_tuples: List[Tuple[int, str, str, Optional[str]]] = []

        for m in canonical_roadmap.milestones:
            # Map prerequisites
            m_prereqs = [
                VerifiedRoadmapPrerequisite(
                    skill_id=p.skill_id,
                    skill_name=p.skill_name,
                    canonical_slug=p.canonical_slug,
                    dependency_type=p.dependency_type.value if hasattr(p.dependency_type, "value") else str(p.dependency_type),
                    is_satisfied=p.is_satisfied,
                )
                for p in m.prerequisites
            ]

            # Map resources (curated approved resources)
            m_resources = [
                VerifiedApprovedResource(
                    resource_id=r.id,
                    skill_id=m.skill_id,
                    skill_name=m.skill_name,
                    title=r.title,
                    url=r.url,
                    resource_type=r.resource_type,
                    provider=r.provider,
                    difficulty=r.difficulty,
                    estimated_minutes=r.estimated_minutes,
                    is_approved=True,
                )
                for r in m.resources
            ]

            # Map project (curated project challenge; NOT candidate proof)
            m_project = None
            if m.project:
                m_project = VerifiedApprovedProject(
                    project_id=m.project.id,
                    skill_id=m.skill_id,
                    skill_name=m.skill_name,
                    title=m.project.title,
                    description=m.project.description,
                    difficulty=m.project.difficulty,
                    deliverables=m.project.deliverables,
                    verification_criteria=m.project.verification_criteria,
                    estimated_hours=m.project.estimated_hours,
                    role_id=db_roadmap.role_id,
                    is_curated_challenge=True,
                    is_candidate_proof=False,
                )

            # Latest verification
            latest_v = latest_milestone_verif.get(m.milestone_id) if m.milestone_id else None

            p_level_enum = PriorityTierLevel(m.priority_level) if m.priority_level in PriorityTierLevel.__members__ else None

            m_ctx = VerifiedRoadmapMilestoneContext(
                milestone_id=m.milestone_id,
                order_index=m.order_index,
                skill_id=m.skill_id,
                skill_name=m.skill_name,
                canonical_slug=m.canonical_slug,
                category=m.category,
                gap_status=SkillGapClassification(m.gap_status),
                priority_score=m.priority_score,
                priority_level=p_level_enum,
                is_transitive_prerequisite=m.is_transitive_prerequisite,
                deterministic_reason=m.reason,
                status=m.status.value if hasattr(m.status, "value") else str(m.status),
                prerequisites=tuple(m_prereqs),
                learning_objectives=m.learning_objectives,
                resources=tuple(m_resources),
                project=m_project,
                latest_verification=latest_v,
            )
            milestone_contexts.append(m_ctx)
            milestone_hash_tuples.append((
                m.order_index,
                str(m.skill_id),
                m.gap_status,
                m.priority_level,
            ))

        # 9. Assemble Roadmap Summary
        roadmap_summary = VerifiedRoadmapSummary(
            roadmap_id=db_roadmap.id,
            user_id=authenticated_user_id,
            role_id=db_roadmap.role_id,
            target_role_title=db_roadmap.target_role_title,
            location=location,
            status=canonical_roadmap.status.value if hasattr(canonical_roadmap.status, "value") else str(canonical_roadmap.status),
            roadmap_version=canonical_roadmap.roadmap_version,
            total_milestones=len(milestone_contexts),
            high_priority_count=canonical_roadmap.high_priority_count,
            medium_priority_count=canonical_roadmap.medium_priority_count,
            low_priority_count=canonical_roadmap.low_priority_count,
            transitive_prerequisite_count=canonical_roadmap.transitive_prerequisite_count,
            milestones=tuple(milestone_contexts),
        )

        # 10. Generate Deterministic Verification Hash
        verification_hash = generate_deterministic_verification_hash(
            roadmap_id=db_roadmap.id,
            user_id=authenticated_user_id,
            role_id=db_roadmap.role_id,
            target_role_title=db_roadmap.target_role_title,
            readiness_percentage=readiness_metrics.readiness_percentage,
            strong_count=readiness_metrics.strong_count,
            partial_count=readiness_metrics.partial_count,
            missing_count=readiness_metrics.missing_count,
            milestone_tuples=tuple(milestone_hash_tuples),
        )

        # 11. Assemble Root Verified Context
        return VerifiedRoadmapPDFContext(
            schema_version="v1.0",
            candidate=candidate_profile,
            readiness=readiness_metrics,
            prioritized_gaps=prioritized_gaps_summary,
            all_gap_facts=tuple(all_gap_facts),
            roadmap=roadmap_summary,
            market_facts=tuple(market_facts),
            verification_evidence=tuple(verification_evidence_list),
            weekly_hours_recommendation=None,  # Rule: never fabricate; None if unconfigured
            verification_hash=verification_hash,
        )


roadmap_pdf_context_service = RoadmapPDFContextService()
