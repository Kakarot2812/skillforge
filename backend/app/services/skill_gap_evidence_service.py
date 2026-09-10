import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import (
    JobRole,
    IndustrySkillDemand,
    Skill,
    UserClaimedSkill,
    Resume,
    DemonstratedSkill,
    ProjectEvidence,
    GitHubRepository,
    SkillGap,
)
from app.schemas.skill_gap_evidence import (
    ResumeEvidenceItem,
    GitHubEvidenceItem,
    DemonstratedSkillSummary,
    CandidateEvidenceData,
    MarketEvidenceData,
    DeterministicReasoningData,
    SkillGapEvidenceResponseData,
)
from app.services.skill_gap_service import skill_gap_service, SCORING_VERSION
from app.services.demonstrated_skill_service import (
    is_repo_owned_by_user,
    aggregate_repository_scores,
    compute_evidence_level,
)


def build_classification_explanation(
    status: str,
    claimed: bool,
    demonstrated: bool,
    demonstrated_score: float,
    evidence_level: Optional[str] = None,
    raw_mention: Optional[str] = None,
    evidence_count: int = 0,
    repository_count: int = 0,
) -> str:
    """
    Deterministic explanation for why the gap status (STRONG, PARTIAL, MISSING) was assigned.
    Grounded purely in actual database records.
    """
    if status == "STRONG":
        return (
            f"Strong because verified GitHub code artifacts demonstrate this skill at HIGH confidence "
            f"({round(demonstrated_score * 100)}%) across {repository_count} repository(ies) with {evidence_count} evidence artifact(s)."
        )
    elif status == "PARTIAL":
        if claimed and demonstrated:
            return (
                f"Partial because this skill was claimed in your resume ({raw_mention or 'documented claim'}) and has verified GitHub artifacts "
                f"({evidence_count} artifact(s) across {repository_count} repo(s)), but code demonstration score ({round(demonstrated_score * 100)}%) "
                f"is below the strong threshold (85%)."
            )
        elif claimed:
            return (
                f"Partial because this skill was claimed in your resume ({raw_mention or 'documented claim'}), "
                f"but no verified GitHub code demonstration was found."
            )
        else:
            return (
                f"Partial because verified GitHub code evidence exists ({evidence_count} artifact(s) across {repository_count} repo(s)), "
                f"but demonstrated confidence ({round(demonstrated_score * 100)}%) is below the strong threshold (85%)."
            )
    else:  # MISSING
        return "Missing because neither a resume claim nor verified GitHub code evidence was found."


def build_priority_explanation(
    status: str,
    priority_level: Optional[str],
    priority_score: Optional[float],
    demand_score: float,
    growth_rate: float,
) -> str:
    """
    Deterministic explanation for why the priority tier was assigned.
    Connects gap severity + market demand + YoY growth.
    """
    if status == "STRONG":
        return "Skill is already sufficiently demonstrated (STRONG). It is not considered an actionable gap."

    level = priority_level or "LOW"
    severity_text = "missing from your candidate profile" if status == "MISSING" else "only partially demonstrated"

    if demand_score >= 0.70:
        demand_text = f"high market demand ({round(demand_score * 100)}%)"
    elif demand_score >= 0.40:
        demand_text = f"moderate market demand ({round(demand_score * 100)}%)"
    else:
        demand_text = f"lower market demand ({round(demand_score * 100)}%)"

    if growth_rate > 0.05:
        growth_text = f"rapid industry growth (+{round(growth_rate * 100)}% YoY)"
    elif growth_rate < -0.05:
        growth_text = f"declining industry trend ({round(growth_rate * 100)}% YoY)"
    else:
        growth_text = f"stable market demand (+{round(growth_rate * 100)}% YoY)"

    return f"{level} priority because the skill is {severity_text}, combined with {demand_text} and {growth_text}."


class SkillGapEvidenceService:
    """
    Service responsible for constructing auditable, deterministic evidence chains for skill gaps:
    1. Candidate Resume Evidence
    2. Candidate GitHub Code Artifacts
    3. Industry Market Demand & Trajectory
    4. Deterministic Reasoning & Audit Trail
    """

    def get_gap_evidence(
        self,
        db: Session,
        role_id: uuid.UUID,
        skill_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        location: str = "India",
        include_resume: bool = True,
        include_github: bool = True,
        github_username: Optional[str] = None,
        resume_id: Optional[uuid.UUID] = None,
    ) -> SkillGapEvidenceResponseData:
        """
        Retrieves the complete deterministic evidence chain for a specific skill gap.
        Supports candidate profile scoping (include_resume, include_github, github_username, resume_id).
        Raises KeyError if role or skill not found.
        Raises ValueError if skill is not demanded for the role.
        """
        # 1. Validate role exists
        role = db.query(JobRole).filter(JobRole.id == role_id).first()
        if not role:
            raise KeyError(f"Job role with id '{role_id}' not found.")

        # 2. Validate skill exists
        skill = db.query(Skill).filter(Skill.id == skill_id).first()
        if not skill:
            raise KeyError(f"Skill with id '{skill_id}' not found.")

        # 3. Validate skill is demanded by the role in this location
        demand_query = db.query(IndustrySkillDemand).filter(
            IndustrySkillDemand.role_id == role_id,
            IndustrySkillDemand.skill_id == skill_id,
        )
        if location:
            demand_query = demand_query.filter(
                func.lower(IndustrySkillDemand.location) == location.strip().lower()
            )
        demand = demand_query.first()
        if not demand:
            raise ValueError(
                f"Skill '{skill.name}' is not demanded by role '{role.title}' for location '{location}'."
            )

        # 4. Ensure gap records are up to date and reconciled with candidate scoping
        skill_gap_service.compute_and_persist_skill_gaps(
            db=db,
            role_id=role_id,
            user_id=user_id,
            location=location,
            include_resume=include_resume,
            include_github=include_github,
            github_username=github_username,
            resume_id=resume_id,
        )

        # 5. Fetch gap record for status and priority metrics
        gap_query = db.query(SkillGap).filter(
            SkillGap.role_id == role_id,
            SkillGap.skill_id == skill_id,
        )
        if location:
            gap_query = gap_query.filter(
                func.lower(SkillGap.location) == location.strip().lower()
            )
        if user_id:
            gap_query = gap_query.filter(SkillGap.user_id == user_id)
        else:
            gap_query = gap_query.filter(SkillGap.user_id.is_(None))
        gap_record = gap_query.first()

        status = gap_record.status if gap_record else "MISSING"
        priority_score = gap_record.priority_score if gap_record else None
        priority_level = gap_record.priority_level if gap_record else None
        scoring_version = gap_record.scoring_version if gap_record else SCORING_VERSION

        # 6. Retrieve Resume Evidence
        resume_items: List[ResumeEvidenceItem] = []
        raw_mention_sample = None
        if include_resume:
            # Resolve authoritative candidate resume scope:
            # - If resume_id is provided, restrict strictly to that resume ID.
            # - When resume_id is absent: do NOT union all historical anonymous resumes.
            #   For authenticated users: resolve the latest resume for that user.
            #   For unauthenticated sessions: resolve the latest anonymous resume deterministically.
            effective_resume_id = resume_id
            if effective_resume_id is None:
                if user_id is not None:
                    latest_resume = (
                        db.query(Resume)
                        .filter(Resume.user_id == user_id)
                        .order_by(Resume.created_at.desc())
                        .first()
                    )
                    if latest_resume:
                        effective_resume_id = latest_resume.id
                else:
                    latest_resume = (
                        db.query(Resume)
                        .filter(Resume.user_id.is_(None))
                        .order_by(Resume.created_at.desc())
                        .first()
                    )
                    if latest_resume:
                        effective_resume_id = latest_resume.id

            resume_query = (
                db.query(UserClaimedSkill, Resume)
                .outerjoin(Resume, UserClaimedSkill.resume_id == Resume.id)
                .filter(UserClaimedSkill.skill_id == skill_id)
            )
            if effective_resume_id:
                resume_query = resume_query.filter(UserClaimedSkill.resume_id == effective_resume_id)
                if user_id is not None:
                    resume_query = resume_query.filter(Resume.user_id == user_id)
                else:
                    resume_query = resume_query.filter(Resume.user_id.is_(None))
            elif user_id is not None:
                # Fallback for authenticated direct claims created without a resume entity (e.g. unit tests)
                resume_query = resume_query.filter(UserClaimedSkill.user_id == user_id)
            else:
                # No resume exists in unauthenticated context; do NOT aggregate historical claims
                resume_query = resume_query.filter(False)

            resume_rows = resume_query.all()
            # Deterministic ordering: confidence_score DESC, source ASC, claim_id ASC
            resume_rows.sort(
                key=lambda item: (
                    -item[0].confidence_score,
                    item[0].source,
                    str(item[0].id),
                )
            )

            for cs, r in resume_rows:
                if not raw_mention_sample and cs.raw_mention:
                    raw_mention_sample = cs.raw_mention
                resume_items.append(
                    ResumeEvidenceItem(
                        id=cs.id,
                        raw_mention=cs.raw_mention,
                        confidence_score=round(cs.confidence_score, 2),
                        source=cs.source,
                        resume_id=cs.resume_id,
                        resume_file_name=r.file_name if r else None,
                        created_at=cs.created_at.isoformat() if cs.created_at else None,
                    )
                )

        # 7. Retrieve GitHub Demonstrated Evidence
        demo_summary = None
        if include_github:
            demo_query = db.query(DemonstratedSkill).filter(
                DemonstratedSkill.skill_id == skill_id
            )
            if user_id:
                demo_query = demo_query.filter(DemonstratedSkill.user_id == user_id)
            else:
                demo_query = demo_query.filter(DemonstratedSkill.user_id.is_(None))
            demos = demo_query.all()
            if github_username and github_username.strip():
                clean_handle = github_username.strip().lstrip("@").lower()
                for d in demos:
                    repos = (d.skill_metadata or {}).get("repositories", [])
                    matching_repos = [r for r in repos if is_repo_owned_by_user(r, clean_handle)]
                    if matching_repos:
                        repo_scores = []
                        for r in matching_repos:
                            s = r.get("max_confidence")
                            if s is None:
                                s = r.get("confidence_score")
                            if s is None:
                                s = d.confidence_score
                            repo_scores.append(float(s) if s is not None else 0.0)
                        cand_score = aggregate_repository_scores(repo_scores)
                        cand_level = compute_evidence_level(cand_score)
                        cand_ev_count = sum(r.get("evidence_count", 1) for r in matching_repos)
                        cand_repo_count = len(matching_repos)
                        demo_summary = DemonstratedSkillSummary(
                            confidence_score=round(cand_score, 2),
                            evidence_level=cand_level,
                            evidence_count=cand_ev_count,
                            repository_count=cand_repo_count,
                            last_verified_at=d.last_verified_at.isoformat() if d.last_verified_at else None,
                        )
                        break
            elif demos:
                demo = demos[0]
                demo_summary = DemonstratedSkillSummary(
                    confidence_score=round(demo.confidence_score, 2),
                    evidence_level=demo.evidence_level,
                    evidence_count=demo.evidence_count,
                    repository_count=demo.repository_count,
                    last_verified_at=demo.last_verified_at.isoformat() if demo.last_verified_at else None,
                )

        # Retrieve individual project evidence artifacts
        github_items: List[GitHubEvidenceItem] = []
        if include_github:
            evidence_query = (
                db.query(ProjectEvidence, GitHubRepository)
                .outerjoin(GitHubRepository, ProjectEvidence.repo_id == GitHubRepository.id)
                .filter(ProjectEvidence.skill_id == skill_id)
            )
            if user_id:
                evidence_query = evidence_query.filter(ProjectEvidence.user_id == user_id)
            else:
                evidence_query = evidence_query.filter(ProjectEvidence.user_id.is_(None))

            if github_username and github_username.strip():
                clean_handle = github_username.strip().lstrip("@").lower()
                evidence_query = evidence_query.filter(
                    (GitHubRepository.full_name.ilike(f"{clean_handle}/%"))
                    | (GitHubRepository.repo_url.ilike(f"%github.com/{clean_handle}/%"))
                    | (GitHubRepository.repo_url.ilike(f"%/{clean_handle}/%"))
                )

            evidence_rows = evidence_query.all()
            # Deterministic ordering: repo_name ASC, evidence_type ASC, confidence DESC, id ASC
            evidence_rows.sort(
                key=lambda item: (
                    (item[1].repo_name.lower() if item[1] else ""),
                    item[0].evidence_type,
                    -item[0].confidence_score,
                    str(item[0].id),
                )
            )

            for pe, repo in evidence_rows:
                github_items.append(
                    GitHubEvidenceItem(
                        id=pe.id,
                        repo_id=pe.repo_id,
                        repo_name=repo.repo_name if repo else "unknown-repo",
                        repo_full_name=repo.full_name if repo else None,
                        repo_url=repo.repo_url if repo else None,
                        evidence_type=pe.evidence_type,
                        file_path=pe.file_path,
                        artifact_name=pe.artifact_name,
                        matched_content=pe.matched_content,
                        confidence_score=round(pe.confidence_score, 2),
                        detected_at=pe.detected_at.isoformat() if pe.detected_at else None,
                    )
                )

        # 8. Candidate evidence package
        has_evidence = len(resume_items) > 0 or len(github_items) > 0 or demo_summary is not None
        candidate_evidence = CandidateEvidenceData(
            has_evidence=has_evidence,
            resume_claims=resume_items,
            github_demonstrated=demo_summary,
            github_artifacts=github_items,
        )

        # 9. Market evidence package
        market_evidence = MarketEvidenceData(
            role_id=role.id,
            role_title=role.title,
            role_slug=role.slug,
            location=demand.location,
            demand_score=round(demand.demand_score, 2),
            growth_rate=round(demand.growth_rate, 2),
            sample_size=demand.sample_size,
            data_updated_at=demand.data_updated_at.isoformat() if demand.data_updated_at else None,
        )

        # 10. Deterministic reasoning package
        claimed = len(resume_items) > 0
        demonstrated = demo_summary is not None
        demo_score = demo_summary.confidence_score if demo_summary else 0.0
        ev_level = demo_summary.evidence_level if demo_summary else None
        ev_count = demo_summary.evidence_count if demo_summary else 0
        repo_count = demo_summary.repository_count if demo_summary else 0

        classification_reason = build_classification_explanation(
            status=status,
            claimed=claimed,
            demonstrated=demonstrated,
            demonstrated_score=demo_score,
            evidence_level=ev_level,
            raw_mention=raw_mention_sample,
            evidence_count=ev_count,
            repository_count=repo_count,
        )

        priority_reason = build_priority_explanation(
            status=status,
            priority_level=priority_level,
            priority_score=priority_score,
            demand_score=demand.demand_score,
            growth_rate=demand.growth_rate,
        )

        reasoning = DeterministicReasoningData(
            classification_reason=classification_reason,
            priority_reason=priority_reason,
            scoring_version=scoring_version,
        )

        return SkillGapEvidenceResponseData(
            skill_id=skill.id,
            skill_name=skill.name,
            canonical_slug=skill.slug,
            category=skill.category,
            status=status,
            priority_score=round(priority_score, 2) if priority_score is not None else None,
            priority_level=priority_level,
            candidate_evidence=candidate_evidence,
            market_evidence=market_evidence,
            reasoning=reasoning,
        )


skill_gap_evidence_service = SkillGapEvidenceService()
