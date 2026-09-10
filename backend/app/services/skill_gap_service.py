import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.models import JobRole, IndustrySkillDemand, Skill, UserClaimedSkill, DemonstratedSkill, SkillGap, Resume
from app.schemas.skill_gap import (
    SkillGapItem,
    SkillGapSummary,
    PrioritizedGapItem,
    PrioritizedGapsSummary,
)
from app.services.demonstrated_skill_service import (
    is_repo_owned_by_user,
    aggregate_repository_scores,
    compute_evidence_level,
)


class CandidateDemonstratedSkill:
    """Lightweight candidate-scoped projection of a DemonstratedSkill."""
    def __init__(
        self,
        skill_id: uuid.UUID,
        confidence_score: float,
        evidence_level: str,
        evidence_count: int,
        repository_count: int,
        skill_metadata: Optional[Dict[str, Any]] = None,
    ):
        self.skill_id = skill_id
        self.confidence_score = confidence_score
        self.evidence_level = evidence_level
        self.evidence_count = evidence_count
        self.repository_count = repository_count
        self.skill_metadata = skill_metadata or {}


# Named constant adhering to demonstrated_skill_service.compute_evidence_level HIGH tier
STRONG_DEMONSTRATED_THRESHOLD = 0.85

# Scoring version
SCORING_VERSION = "v1"

# Deterministic status ordering for gap analysis results: MISSING first, then PARTIAL, then STRONG
STATUS_SORT_RANK = {
    "MISSING": 0,
    "PARTIAL": 1,
    "STRONG": 2,
}

# Deterministic actionable status ordering for prioritized gaps
ACTIONABLE_STATUS_SORT_RANK = {
    "MISSING": 0,
    "PARTIAL": 1,
}

# Gap severity weights
SEVERITY_WEIGHTS = {
    "MISSING": 1.0,
    "PARTIAL": 0.5,
    "STRONG": 0.0,
}

# Priority category thresholds
PRIORITY_HIGH_THRESHOLD = 0.67
PRIORITY_MEDIUM_THRESHOLD = 0.34


def classify_skill_gap(
    claimed: bool,
    claim_confidence: float,
    demonstrated: bool,
    demonstrated_score: float,
    evidence_level: Optional[str] = None,
) -> str:
    """
    Deterministic skill gap classification:
    - STRONG: User has credible demonstrated evidence at the HIGH tier
              (evidence_level == 'HIGH' or demonstrated_score >= STRONG_DEMONSTRATED_THRESHOLD).
    - PARTIAL: User has some evidence (resume claim or demonstrated evidence below the strong threshold)
               that is insufficient to classify as STRONG.
    - MISSING: Neither claimed in resume nor demonstrated in GitHub code artifacts.
    """
    is_strong = demonstrated and (
        evidence_level == "HIGH" or demonstrated_score >= STRONG_DEMONSTRATED_THRESHOLD
    )
    if is_strong:
        return "STRONG"

    if claimed or demonstrated:
        return "PARTIAL"

    return "MISSING"


def normalize_growth_signal(growth_rate: float) -> float:
    """
    Normalizes growth into a bounded positive market-growth signal [0.0, 1.0].
    growth_signal = clamp((growth_rate + 1.0) / 2.0, 0.0, 1.0)
    """
    val = (growth_rate + 1.0) / 2.0
    return max(0.0, min(1.0, val))


def calculate_gap_priority(status: str, demand_score: float, growth_rate: float) -> float:
    """
    Deterministic priority score calculation:
    priority_score = gap_severity_weight * (0.70 * demand_score + 0.30 * growth_signal)
    Clamped to [0.0, 1.0] and rounded to 4 decimal places.
    """
    severity_weight = SEVERITY_WEIGHTS.get(status, 0.0)
    if severity_weight == 0.0:
        return 0.0

    clamped_demand = max(0.0, min(1.0, demand_score))
    growth_signal = normalize_growth_signal(growth_rate)

    raw_score = severity_weight * (0.70 * clamped_demand + 0.30 * growth_signal)
    clamped_score = max(0.0, min(1.0, raw_score))
    return round(clamped_score, 4)


def classify_priority_level(priority_score: float) -> str:
    """
    Deterministic human-readable priority categories:
    - HIGH: priority_score >= 0.67
    - MEDIUM: 0.34 <= priority_score < 0.67
    - LOW: 0.0 <= priority_score < 0.34
    """
    if priority_score >= PRIORITY_HIGH_THRESHOLD:
        return "HIGH"
    elif priority_score >= PRIORITY_MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def generate_gap_explanation(
    status: str,
    demand_score: float,
    growth_rate: float,
    priority_level: str,
) -> str:
    """
    Deterministic rule-based explanation without an LLM.
    Explains the priority level based on gap severity, empirical market demand, and YoY growth.
    """
    severity_desc = "missing from your profile" if status == "MISSING" else "only partially demonstrated"

    if demand_score >= 0.70:
        demand_desc = f"high market demand ({round(demand_score * 100)}%)"
    elif demand_score >= 0.40:
        demand_desc = f"moderate market demand ({round(demand_score * 100)}%)"
    else:
        demand_desc = f"lower market demand ({round(demand_score * 100)}%)"

    if growth_rate > 0.05:
        growth_desc = f"rapidly growing (+{round(growth_rate * 100)}% YoY)"
    elif growth_rate < -0.05:
        growth_desc = f"declining trend ({round(growth_rate * 100)}% YoY)"
    else:
        growth_desc = f"stable demand (+{round(growth_rate * 100)}% YoY)"

    return f"{priority_level} priority: Skill is {severity_desc} with {demand_desc} and {growth_desc}."


class SkillGapService:
    """
    Deterministic skill gap service combining:
    - Target role skill demand (Industry Demand Engine)
    - Resume claimed skills (Resume Intelligence)
    - GitHub demonstrated skills (GitHub Intelligence)
    - Deterministic gap prioritization (Phase 5 Checkpoint 2)
    All calculations are strictly database-derived. LLMs are strictly prohibited from
    evaluating, assigning, or modifying gap statuses or priorities.
    """

    def compute_and_persist_skill_gaps(
        self,
        db: Session,
        role_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        location: str = "India",
        include_resume: bool = True,
        include_github: bool = True,
        github_username: Optional[str] = None,
        resume_id: Optional[uuid.UUID] = None,
    ) -> Tuple[JobRole, SkillGapSummary, List[SkillGapItem]]:
        """
        Idempotently computes and persists the user's skill gap state for a target canonical role.
        Supports explicit candidate scoping:
        - include_resume: If False, resume claims are excluded.
        - include_github: If False, GitHub demonstrated skills are excluded.
        - github_username: If provided, demonstrated skills are scoped to that GitHub handle.
        - resume_id: If provided, claims are scoped to that specific resume.
        """
        role = db.query(JobRole).filter(JobRole.id == role_id).first()
        if not role:
            raise KeyError(f"Job role with id '{role_id}' not found.")

        # 1. Fetch required skills from industry demand for the target role and location
        demand_query = (
            db.query(IndustrySkillDemand, Skill)
            .join(Skill, IndustrySkillDemand.skill_id == Skill.id)
            .filter(IndustrySkillDemand.role_id == role_id)
        )
        if location:
            demand_query = demand_query.filter(
                func.lower(IndustrySkillDemand.location) == location.strip().lower()
            )
        demanded_rows = demand_query.all()

        # 2. Fetch candidate claimed skills for this user
        if not include_resume:
            claimed_map = {}
        else:
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

            claimed_query = (
                db.query(UserClaimedSkill)
                .outerjoin(Resume, UserClaimedSkill.resume_id == Resume.id)
            )
            if effective_resume_id:
                claimed_query = claimed_query.filter(UserClaimedSkill.resume_id == effective_resume_id)
                if user_id is not None:
                    claimed_query = claimed_query.filter(Resume.user_id == user_id)
                else:
                    claimed_query = claimed_query.filter(Resume.user_id.is_(None))
            elif user_id is not None:
                # Fallback for authenticated direct claims created without a resume entity (e.g. unit tests)
                claimed_query = claimed_query.filter(UserClaimedSkill.user_id == user_id)
            else:
                # No resume exists in unauthenticated context; do NOT aggregate historical claims
                claimed_query = claimed_query.filter(False)

            claimed_map = {cs.skill_id: cs for cs in claimed_query.all()}

        # 3. Fetch candidate demonstrated skills for this user
        if not include_github:
            demonstrated_map = {}
        else:
            demo_query = db.query(DemonstratedSkill)
            if user_id:
                demo_query = demo_query.filter(DemonstratedSkill.user_id == user_id)
            else:
                demo_query = demo_query.filter(DemonstratedSkill.user_id.is_(None))
            all_demos = demo_query.all()
            if github_username and github_username.strip():
                clean_handle = github_username.strip().lstrip("@").lower()
                demonstrated_map = {}
                for ds in all_demos:
                    repos = (ds.skill_metadata or {}).get("repositories", [])
                    matching_repos = [r for r in repos if is_repo_owned_by_user(r, clean_handle)]
                    if matching_repos:
                        repo_scores = []
                        for r in matching_repos:
                            s = r.get("max_confidence")
                            if s is None:
                                s = r.get("confidence_score")
                            if s is None:
                                s = ds.confidence_score
                            repo_scores.append(float(s) if s is not None else 0.0)
                        cand_score = aggregate_repository_scores(repo_scores)
                        cand_level = compute_evidence_level(cand_score)
                        cand_ev_count = sum(r.get("evidence_count", 1) for r in matching_repos)
                        cand_repo_count = len(matching_repos)
                        demonstrated_map[ds.skill_id] = CandidateDemonstratedSkill(
                            skill_id=ds.skill_id,
                            confidence_score=cand_score,
                            evidence_level=cand_level,
                            evidence_count=cand_ev_count,
                            repository_count=cand_repo_count,
                            skill_metadata={
                                "repositories": matching_repos,
                                "evidence_types": (ds.skill_metadata or {}).get("evidence_types", []),
                            },
                        )
            else:
                demonstrated_map = {ds.skill_id: ds for ds in all_demos}

        # 4. Fetch existing gap records for this (user_id, role_id, location)
        gap_query = db.query(SkillGap).filter(SkillGap.role_id == role_id)
        if location:
            gap_query = gap_query.filter(func.lower(SkillGap.location) == location.strip().lower())
        if user_id:
            gap_query = gap_query.filter(SkillGap.user_id == user_id)
        else:
            gap_query = gap_query.filter(SkillGap.user_id.is_(None))
        existing_gaps = {g.skill_id: g for g in gap_query.all()}

        # 5. Classify each demanded skill, calculate priority, & update or insert into skill_gaps
        current_demanded_skill_ids: Set[uuid.UUID] = set()
        gap_items: List[Tuple[SkillGap, Skill]] = []
        strong_count = 0
        partial_count = 0
        missing_count = 0

        now = datetime.now(timezone.utc)

        for demand, skill in demanded_rows:
            current_demanded_skill_ids.add(skill.id)
            cs = claimed_map.get(skill.id)
            ds = demonstrated_map.get(skill.id)

            claimed = cs is not None
            claim_conf = cs.confidence_score if cs else 0.0

            demonstrated = ds is not None
            demo_score = ds.confidence_score if ds else 0.0
            ev_level = ds.evidence_level if ds else None
            ev_count = ds.evidence_count if ds else 0

            status = classify_skill_gap(
                claimed=claimed,
                claim_confidence=claim_conf,
                demonstrated=demonstrated,
                demonstrated_score=demo_score,
                evidence_level=ev_level,
            )

            if status == "STRONG":
                strong_count += 1
                priority_score = 0.0
                priority_level = None
            else:
                if status == "PARTIAL":
                    partial_count += 1
                else:
                    missing_count += 1
                priority_score = calculate_gap_priority(status, demand.demand_score, demand.growth_rate)
                priority_level = classify_priority_level(priority_score)

            gap_record = existing_gaps.get(skill.id)
            if gap_record:
                # Update existing record idempotently
                gap_record.status = status
                gap_record.demand_score = demand.demand_score
                gap_record.growth_rate = demand.growth_rate
                gap_record.claimed = claimed
                gap_record.claim_confidence = claim_conf
                gap_record.demonstrated = demonstrated
                gap_record.demonstrated_score = demo_score
                gap_record.evidence_level = ev_level
                gap_record.evidence_count = ev_count
                gap_record.priority_score = priority_score
                gap_record.priority_level = priority_level
                gap_record.scoring_version = SCORING_VERSION
                gap_record.computed_at = now
                gap_record.updated_at = now
            else:
                # Insert new record
                gap_record = SkillGap(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    role_id=role_id,
                    skill_id=skill.id,
                    location=demand.location,
                    status=status,
                    demand_score=demand.demand_score,
                    growth_rate=demand.growth_rate,
                    claimed=claimed,
                    claim_confidence=claim_conf,
                    demonstrated=demonstrated,
                    demonstrated_score=demo_score,
                    evidence_level=ev_level,
                    evidence_count=ev_count,
                    priority_score=priority_score,
                    priority_level=priority_level,
                    scoring_version=SCORING_VERSION,
                    computed_at=now,
                    created_at=now,
                    updated_at=now,
                )
                db.add(gap_record)

            gap_items.append((gap_record, skill))

        # 6. Reconcile stale gap records (skills no longer demanded by role)
        for stale_skill_id, stale_record in existing_gaps.items():
            if stale_skill_id not in current_demanded_skill_ids:
                db.delete(stale_record)

        db.commit()

        # 7. Deterministic sorting:
        # 1. status rank: MISSING (0), PARTIAL (1), STRONG (2)
        # 2. demand_score DESC
        # 3. skill.name ASC
        # 4. skill.id ASC
        gap_items.sort(
            key=lambda item: (
                STATUS_SORT_RANK.get(item[0].status, 99),
                -item[0].demand_score,
                item[1].name,
                str(item[1].id),
            )
        )

        # Build schema items
        result_items = [
            SkillGapItem(
                id=gap.id,
                skill_id=skill.id,
                skill_name=skill.name,
                canonical_slug=skill.slug,
                category=skill.category,
                status=gap.status,
                demand_score=round(gap.demand_score, 2),
                growth_rate=round(gap.growth_rate, 2),
                claimed=gap.claimed,
                claim_confidence=round(gap.claim_confidence, 2),
                demonstrated=gap.demonstrated,
                demonstrated_score=round(gap.demonstrated_score, 2),
                evidence_level=gap.evidence_level,
                evidence_count=gap.evidence_count,
                priority_score=round(gap.priority_score, 2) if gap.priority_score is not None else None,
                priority_level=gap.priority_level,
                scoring_version=gap.scoring_version,
            )
            for gap, skill in gap_items
        ]

        summary = SkillGapSummary(
            total_required_skills=len(result_items),
            strong_count=strong_count,
            partial_count=partial_count,
            missing_count=missing_count,
        )

        return role, summary, result_items

    def get_prioritized_gaps(
        self,
        db: Session,
        role_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        location: str = "India",
        include_resume: bool = True,
        include_github: bool = True,
        github_username: Optional[str] = None,
        resume_id: Optional[uuid.UUID] = None,
    ) -> Tuple[JobRole, PrioritizedGapsSummary, List[PrioritizedGapItem]]:
        """
        Retrieves and returns deterministically prioritized actionable gaps (MISSING and PARTIAL only).
        STRONG skills are already sufficiently demonstrated and are excluded.

        Deterministic ordering:
        1. priority_score DESC
        2. MISSING before PARTIAL (status rank)
        3. demand_score DESC
        4. growth_rate DESC
        5. skill.name ASC
        6. skill.id ASC
        """
        # Ensure fresh, reconciled and persisted gap data
        role, _, _ = self.compute_and_persist_skill_gaps(
            db=db,
            role_id=role_id,
            user_id=user_id,
            location=location,
            include_resume=include_resume,
            include_github=include_github,
            github_username=github_username,
            resume_id=resume_id,
        )

        # Fetch actionable records (MISSING and PARTIAL only)
        query = (
            db.query(SkillGap, Skill)
            .join(Skill, SkillGap.skill_id == Skill.id)
            .filter(
                SkillGap.role_id == role_id,
                SkillGap.status.in_(["MISSING", "PARTIAL"]),
            )
        )
        if location:
            query = query.filter(func.lower(SkillGap.location) == location.strip().lower())
        if user_id:
            query = query.filter(SkillGap.user_id == user_id)
        else:
            query = query.filter(SkillGap.user_id.is_(None))

        actionable_rows = query.all()

        # Deterministic sorting
        actionable_rows.sort(
            key=lambda item: (
                -round(item[0].priority_score or 0.0, 4),
                ACTIONABLE_STATUS_SORT_RANK.get(item[0].status, 99),
                -item[0].demand_score,
                -item[0].growth_rate,
                item[1].name.lower(),
                str(item[1].id),
            )
        )

        high_count = 0
        med_count = 0
        low_count = 0
        missing_count = 0
        partial_count = 0

        prioritized_items: List[PrioritizedGapItem] = []

        for gap, skill in actionable_rows:
            p_score = round(gap.priority_score or 0.0, 2)
            p_level = gap.priority_level or classify_priority_level(p_score)

            if p_level == "HIGH":
                high_count += 1
            elif p_level == "MEDIUM":
                med_count += 1
            else:
                low_count += 1

            if gap.status == "MISSING":
                missing_count += 1
            elif gap.status == "PARTIAL":
                partial_count += 1

            explanation = generate_gap_explanation(
                status=gap.status,
                demand_score=gap.demand_score,
                growth_rate=gap.growth_rate,
                priority_level=p_level,
            )

            prioritized_items.append(
                PrioritizedGapItem(
                    skill_id=skill.id,
                    skill_name=skill.name,
                    canonical_slug=skill.slug,
                    category=skill.category,
                    status=gap.status,
                    priority_score=p_score,
                    priority_level=p_level,
                    demand_score=round(gap.demand_score, 2),
                    growth_rate=round(gap.growth_rate, 2),
                    claimed=gap.claimed,
                    claim_confidence=round(gap.claim_confidence, 2),
                    demonstrated=gap.demonstrated,
                    demonstrated_score=round(gap.demonstrated_score, 2),
                    evidence_level=gap.evidence_level,
                    evidence_count=gap.evidence_count,
                    location=gap.location,
                    explanation=explanation,
                )
            )

        summary = PrioritizedGapsSummary(
            total_actionable_gaps=len(prioritized_items),
            high_priority_count=high_count,
            medium_priority_count=med_count,
            low_priority_count=low_count,
            missing_count=missing_count,
            partial_count=partial_count,
        )

        return role, summary, prioritized_items


skill_gap_service = SkillGapService()
