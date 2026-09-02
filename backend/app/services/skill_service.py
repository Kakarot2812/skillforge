import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.db.models import Resume, UserClaimedSkill, Skill
from app.services.skill_extractor import extract_candidate_mentions
from app.services.skill_normalizer import normalize_skills, NormalizedSkillMatch


def process_and_persist_resume_skills(
    db: Session,
    resume: Resume,
) -> List[UserClaimedSkill]:
    """
    Extracts candidate mentions from resume sections, normalizes them against the
    canonical taxonomy, and idempotently persists them into user_claimed_skills.
    """
    parsed_data = dict(resume.parsed_data or {})
    sections = parsed_data.get("sections", {})

    # Extract candidate mentions
    candidate_mentions = extract_candidate_mentions(sections)
    full_text = resume.raw_text or ""

    # Normalize against taxonomy
    normalized_matches: List[NormalizedSkillMatch] = normalize_skills(
        db, candidate_mentions, full_text_scan=full_text
    )

    claimed_skill_records: List[UserClaimedSkill] = []
    claimed_skills_summary: List[Dict[str, Any]] = []
    matched_skill_ids = set()

    for match in normalized_matches:
        matched_skill_ids.add(match.skill.id)

        # 1. Check if already persisted for this resume and skill
        existing = (
            db.query(UserClaimedSkill)
            .filter(
                UserClaimedSkill.resume_id == resume.id,
                UserClaimedSkill.skill_id == match.skill.id,
            )
            .first()
        )

        # 2. Check if already claimed by this user across any resume/input
        if not existing and resume.user_id:
            existing = (
                db.query(UserClaimedSkill)
                .filter(
                    UserClaimedSkill.user_id == resume.user_id,
                    UserClaimedSkill.skill_id == match.skill.id,
                )
                .first()
            )
            if existing:
                existing.resume_id = resume.id

        if not existing:
            new_record = UserClaimedSkill(
                id=uuid.uuid4(),
                user_id=resume.user_id,
                skill_id=match.skill.id,
                resume_id=resume.id,
                source="resume",
                raw_mention=match.raw_mention,
                confidence_score=match.confidence_score,
            )
            db.add(new_record)
            claimed_skill_records.append(new_record)
        else:
            # Update with higher confidence if applicable
            if match.confidence_score > existing.confidence_score:
                existing.confidence_score = match.confidence_score
                existing.raw_mention = match.raw_mention
            claimed_skill_records.append(existing)

        claimed_skills_summary.append(
            {
                "skill_id": str(match.skill.id),
                "skill_name": match.skill.name,
                "canonical_slug": match.skill.slug,
                "category": match.skill.category,
                "raw_mention": match.raw_mention,
                "confidence_score": match.confidence_score,
            }
        )

    # 3. If re-parsing: remove any previously associated claimed skills for this resume
    # that are no longer present in the updated text
    stale_records = (
        db.query(UserClaimedSkill)
        .filter(
            UserClaimedSkill.resume_id == resume.id,
            ~UserClaimedSkill.skill_id.in_(matched_skill_ids) if matched_skill_ids else True,
        )
        .all()
    )
    for stale in stale_records:
        db.delete(stale)

    # Update resume's parsed_data with the claimed skills summary
    parsed_data["claimed_skills_count"] = len(claimed_skills_summary)
    parsed_data["claimed_skills"] = claimed_skills_summary
    resume.parsed_data = parsed_data
    flag_modified(resume, "parsed_data")

    db.commit()
    for rec in claimed_skill_records:
        db.refresh(rec)

    return claimed_skill_records


def get_claimed_skills(
    db: Session,
    user_id: Optional[uuid.UUID] = None,
    resume_id: Optional[uuid.UUID] = None,
    limit: int = 20,
    offset: int = 0,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves claimed skills joined with canonical skill metadata,
    supporting filtering by user_id or resume_id with deterministic pagination.
    """
    query = (
        db.query(UserClaimedSkill, Skill)
        .join(Skill, UserClaimedSkill.skill_id == Skill.id)
    )

    if user_id:
        query = query.filter(UserClaimedSkill.user_id == user_id)
    if resume_id:
        query = query.filter(UserClaimedSkill.resume_id == resume_id)

    total = query.count()
    results = (
        query.order_by(UserClaimedSkill.created_at.desc(), Skill.name.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    claimed_list = []
    for claimed, skill in results:
        claimed_list.append(
            {
                "id": str(claimed.id),
                "skill_id": str(skill.id),
                "skill_name": skill.name,
                "canonical_slug": skill.slug,
                "category": skill.category,
                "source": claimed.source,
                "raw_mention": claimed.raw_mention,
                "confidence_score": claimed.confidence_score,
                "evidence_tier": "CLAIMED",
                "resume_id": str(claimed.resume_id) if claimed.resume_id else None,
                "created_at": claimed.created_at.isoformat() if claimed.created_at else None,
            }
        )

    return claimed_list, total
