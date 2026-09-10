import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.db.models import DemonstratedSkill, GitHubRepository, ProjectEvidence, Skill


def compute_evidence_level(confidence_score: float) -> str:
    """
    Assigns deterministic evidence tier based strictly on demonstrated confidence:
    - HIGH: confidence >= 0.85
    - MEDIUM: 0.70 <= confidence < 0.85
    - LOW: confidence < 0.70
    """
    if confidence_score >= 0.85:
        return "HIGH"
    elif confidence_score >= 0.70:
        return "MEDIUM"
    return "LOW"


def aggregate_repository_scores(repo_scores: List[float]) -> float:
    """
    Bounded independent multi-repository evidence aggregation formula:
    1. Single repository: raw score is the repository's maximum evidence confidence.
    2. Multiple independent repositories: bounded noisy-OR formula
       multi_repo_score = 1 - PRODUCT(1 - repo_score_i)
    3. Clamped to [0.0, 1.0] and rounded to 2 decimal places.
    """
    if not repo_scores:
        return 0.0

    if len(repo_scores) == 1:
        return min(1.0, max(0.0, round(repo_scores[0], 2)))

    product = 1.0
    for score in repo_scores:
        clamped_score = min(1.0, max(0.0, score))
        product *= (1.0 - clamped_score)

    combined = 1.0 - product
    return min(1.0, max(0.0, round(combined, 2)))


def is_repo_owned_by_user(repo_dict: Dict[str, Any], username: Optional[str]) -> bool:
    """
    Canonical source-of-truth helper determining whether a repository summary entry
    belongs to the specified candidate GitHub username.

    Safely and case-insensitively inspects:
    1. repo_url (e.g., https://github.com/Kakarot2812/skillforge, git@github.com:Kakarot2812/skillforge.git)
    2. full_name (e.g., Kakarot2812/skillforge)
    3. owner (e.g., Kakarot2812)
    4. repo_name (e.g., Kakarot2812/skillforge - only when prefixed with the username)

    Prevents substring collision: 'Kakarot2812' will NOT match 'Kakarot2812-other/repo'.
    A short repo_name alone without user prefix or surrounding ownership context is not considered ownership proof.
    """
    if not username or not isinstance(username, str) or not username.strip():
        return False

    clean_u = username.strip().lstrip("@").lower()
    if not clean_u:
        return False

    # 1. Inspect repo_url
    repo_url = (repo_dict.get("repo_url") or "").strip().lower()
    if repo_url:
        if (
            f"github.com/{clean_u}/" in repo_url
            or f"github.com:{clean_u}/" in repo_url
            or f"/{clean_u}/" in repo_url
            or repo_url.endswith(f"/{clean_u}")
        ):
            return True

    # 2. Inspect full_name (e.g. "Kakarot2812/skillforge")
    full_name = (repo_dict.get("full_name") or "").strip().lower()
    if full_name:
        if full_name.startswith(f"{clean_u}/") or f"/{clean_u}/" in full_name:
            return True

    # 3. Inspect owner field if explicitly stored
    owner = (repo_dict.get("owner") or "").strip().lower()
    if owner and owner == clean_u:
        return True

    # 4. Inspect repo_name if it was stored with owner prefix (e.g. "Kakarot2812/skillforge")
    rname = (repo_dict.get("repo_name") or "").strip().lower()
    if rname and (rname.startswith(f"{clean_u}/") or f"/{clean_u}/" in rname):
        return True

    return False


class DemonstratedSkillService:
    """
    Service layer providing deterministic, auditable aggregation of project_evidence
    into canonical DemonstratedSkill representations.
    """

    def recompute_demonstrated_skill(
        self,
        db: Session,
        skill_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[DemonstratedSkill]:
        """
        Idempotently recomputes demonstrated skill state for a specific skill and user.
        If no evidence remains, any existing demonstrated skill record is deleted.
        """
        # 1. Query all evidence items for this skill and user
        evidence_query = (
            db.query(ProjectEvidence, GitHubRepository)
            .outerjoin(GitHubRepository, ProjectEvidence.repo_id == GitHubRepository.id)
            .filter(ProjectEvidence.skill_id == skill_id)
        )

        if user_id:
            evidence_query = evidence_query.filter(ProjectEvidence.user_id == user_id)
        else:
            evidence_query = evidence_query.filter(ProjectEvidence.user_id.is_(None))

        evidence_rows = evidence_query.all()

        # Locate existing demonstrated skill record
        existing_record_query = db.query(DemonstratedSkill).filter(DemonstratedSkill.skill_id == skill_id)
        if user_id:
            existing_record_query = existing_record_query.filter(DemonstratedSkill.user_id == user_id)
        else:
            existing_record_query = existing_record_query.filter(DemonstratedSkill.user_id.is_(None))

        existing_record = existing_record_query.first()

        # If no evidence remains: clean up materialized record
        if not evidence_rows:
            if existing_record:
                db.delete(existing_record)
                db.commit()
            return None

        # 2. Group evidence by repository
        repo_evidence_map: Dict[Optional[uuid.UUID], List[Tuple[ProjectEvidence, Optional[GitHubRepository]]]] = {}
        all_evidence_types: Set[str] = set()
        latest_verified_at: Optional[datetime] = None

        for ev, repo in evidence_rows:
            repo_evidence_map.setdefault(ev.repo_id, []).append((ev, repo))
            all_evidence_types.add(ev.evidence_type)
            if ev.created_at:
                if not latest_verified_at or ev.created_at > latest_verified_at:
                    latest_verified_at = ev.created_at

        # 3. Calculate max confidence per repository (prevents duplicate scans from inflating score)
        repo_scores: List[float] = []
        repo_summaries: List[Dict[str, Any]] = []

        for repo_id_key, items in repo_evidence_map.items():
            max_repo_score = max(ev.confidence_score for ev, _ in items)
            repo_scores.append(max_repo_score)

            sample_repo = items[0][1]
            repo_name = sample_repo.repo_name if sample_repo else "unknown-repo"
            repo_url = sample_repo.repo_url if sample_repo else None
            full_name = sample_repo.full_name if sample_repo else None
            owner = None
            if full_name and "/" in full_name:
                owner = full_name.split("/")[0]
            elif repo_url and "github.com/" in repo_url:
                parts = repo_url.split("github.com/")[-1].split("/")
                if len(parts) >= 2:
                    owner = parts[0]

            repo_summaries.append(
                {
                    "repository_id": str(repo_id_key) if repo_id_key else None,
                    "repo_name": repo_name,
                    "full_name": full_name,
                    "owner": owner,
                    "repo_url": repo_url,
                    "max_confidence": round(max_repo_score, 2),
                    "evidence_count": len(items),
                }
            )

        # 4. Multi-repository aggregation
        aggregated_confidence = aggregate_repository_scores(repo_scores)
        evidence_level = compute_evidence_level(aggregated_confidence)

        now = datetime.now()
        skill_metadata = {
            "repositories": repo_summaries,
            "evidence_types": sorted(list(all_evidence_types)),
            "recomputed_at": now.isoformat(),
        }

        # 5. Idempotent upsert
        if existing_record:
            existing_record.confidence_score = aggregated_confidence
            existing_record.evidence_level = evidence_level
            existing_record.evidence_count = len(evidence_rows)
            existing_record.repository_count = len(repo_evidence_map)
            existing_record.last_verified_at = latest_verified_at or now
            existing_record.skill_metadata = skill_metadata
            existing_record.updated_at = now
            record_to_return = existing_record
        else:
            new_record = DemonstratedSkill(
                id=uuid.uuid4(),
                user_id=user_id,
                skill_id=skill_id,
                confidence_score=aggregated_confidence,
                evidence_level=evidence_level,
                evidence_count=len(evidence_rows),
                repository_count=len(repo_evidence_map),
                last_verified_at=latest_verified_at or now,
                skill_metadata=skill_metadata,
                created_at=now,
                updated_at=now,
            )
            db.add(new_record)
            record_to_return = new_record

        db.commit()
        db.refresh(record_to_return)
        return record_to_return

    def recompute_demonstrated_skills_for_user(
        self,
        db: Session,
        user_id: Optional[uuid.UUID] = None,
    ) -> List[DemonstratedSkill]:
        """
        Finds all distinct skill IDs with project evidence for this user,
        recomputes each demonstrated skill, and returns the aggregated list.
        """
        # Find distinct skills with evidence
        query = db.query(ProjectEvidence.skill_id).distinct()
        if user_id:
            query = query.filter(ProjectEvidence.user_id == user_id)
        else:
            query = query.filter(ProjectEvidence.user_id.is_(None))

        skill_ids = [row[0] for row in query.all()]
        results: List[DemonstratedSkill] = []

        for sid in skill_ids:
            dem = self.recompute_demonstrated_skill(db=db, skill_id=sid, user_id=user_id)
            if dem:
                results.append(dem)

        # Remove any lingering demonstrated skills for this user that have no evidence
        existing_dem_query = db.query(DemonstratedSkill)
        if user_id:
            existing_dem_query = existing_dem_query.filter(DemonstratedSkill.user_id == user_id)
        else:
            existing_dem_query = existing_dem_query.filter(DemonstratedSkill.user_id.is_(None))

        all_existing = existing_dem_query.all()
        for old in all_existing:
            if old.skill_id not in skill_ids:
                db.delete(old)

        db.commit()
        return results

    def get_demonstrated_skills(
        self,
        db: Session,
        user_id: Optional[uuid.UUID] = None,
        username: Optional[str] = None,
        repository_id: Optional[uuid.UUID] = None,
        skill_id: Optional[uuid.UUID] = None,
        evidence_level: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieves paginated demonstrated skills joined with canonical skill metadata,
        supporting filtering by username, repository_id, skill_id, or evidence_level.
        """
        query = (
            db.query(DemonstratedSkill, Skill)
            .join(Skill, DemonstratedSkill.skill_id == Skill.id)
            .filter(DemonstratedSkill.evidence_count > 0)
        )

        # Active project evidence subquery to guarantee zero orphan skills are ever returned
        active_ev_subquery = db.query(ProjectEvidence.skill_id).distinct()
        if user_id:
            query = query.filter(DemonstratedSkill.user_id == user_id)
            active_ev_subquery = active_ev_subquery.filter(ProjectEvidence.user_id == user_id)
        else:
            query = query.filter(DemonstratedSkill.user_id.is_(None))
            active_ev_subquery = active_ev_subquery.filter(ProjectEvidence.user_id.is_(None))

        if username:
            safe_u = username.strip().lower()
            user_ev_subquery = (
                db.query(ProjectEvidence.skill_id)
                .join(GitHubRepository, ProjectEvidence.repo_id == GitHubRepository.id)
                .filter(
                    (GitHubRepository.full_name.ilike(f"{safe_u}/%"))
                    | (GitHubRepository.repo_url.ilike(f"%github.com/{safe_u}/%"))
                    | (GitHubRepository.repo_url.ilike(f"%/{safe_u}/%"))
                )
                .distinct()
            )
            query = query.filter(DemonstratedSkill.skill_id.in_(user_ev_subquery))
            active_ev_subquery = active_ev_subquery.filter(ProjectEvidence.skill_id.in_(user_ev_subquery))

        query = query.filter(DemonstratedSkill.skill_id.in_(active_ev_subquery))

        if skill_id:
            query = query.filter(DemonstratedSkill.skill_id == skill_id)
        if evidence_level:
            query = query.filter(DemonstratedSkill.evidence_level == evidence_level.upper())

        # If filtered by repository_id: ensure the skill has evidence in that repository
        if repository_id:
            subquery = (
                db.query(ProjectEvidence.skill_id)
                .filter(ProjectEvidence.repo_id == repository_id)
                .distinct()
            )
            query = query.filter(DemonstratedSkill.skill_id.in_(subquery))

        total = query.count()
        results = (
            query.order_by(
                DemonstratedSkill.confidence_score.desc(),
                Skill.name.asc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = []
        for dem, skill in results:
            meta = dem.skill_metadata or {}
            raw_repos = meta.get("repositories", [])
            if username:
                raw_repos = [r for r in raw_repos if is_repo_owned_by_user(r, username)]
                repo_scores = []
                for r in raw_repos:
                    s = r.get("max_confidence")
                    if s is None:
                        s = r.get("confidence_score")
                    if s is None:
                        s = dem.confidence_score
                    repo_scores.append(float(s) if s is not None else 0.0)
                user_conf = aggregate_repository_scores(repo_scores)
                user_level = compute_evidence_level(user_conf)
                user_ev_count = sum(r.get("evidence_count", 1) for r in raw_repos)
                user_repo_count = len(raw_repos)
            else:
                user_conf = dem.confidence_score
                user_level = dem.evidence_level
                user_ev_count = dem.evidence_count
                user_repo_count = dem.repository_count

            items.append(
                {
                    "skill_id": str(skill.id),
                    "skill_name": skill.name,
                    "slug": skill.slug,
                    "category": skill.category,
                    "confidence_score": user_conf,
                    "evidence_level": user_level,
                    "evidence_count": user_ev_count,
                    "repository_count": user_repo_count,
                    "last_verified_at": dem.last_verified_at.isoformat() if dem.last_verified_at else None,
                    "repositories": raw_repos,
                    "evidence_types": meta.get("evidence_types", []),
                }
            )

        return items, total


demonstrated_skill_service = DemonstratedSkillService()
