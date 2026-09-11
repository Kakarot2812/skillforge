import re
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.db.models import Skill, SkillAlias


def normalize_string_key(s: str) -> str:
    """Produces a stripped alphanumeric key for comparison (e.g. 'React.js' -> 'reactjs')."""
    return re.sub(r"[^a-zA-Z0-9#+]", "", s).lower()


class NormalizedSkillMatch:
    def __init__(
        self,
        skill: Skill,
        raw_mention: str,
        confidence_score: float,
        match_type: str,
    ):
        self.skill = skill
        self.raw_mention = raw_mention
        self.confidence_score = confidence_score
        self.match_type = match_type

    def __repr__(self) -> str:
        return f"<Match: {self.raw_mention} -> {self.skill.name} ({self.confidence_score})>"


class SkillTaxonomyCache:
    """In-memory indexing of canonical skills and aliases for deterministic normalization."""

    def __init__(self, db: Session):
        self.skills: List[Skill] = db.query(Skill).all()
        self.aliases: List[SkillAlias] = db.query(SkillAlias).all()

        # Build fast lookup indices
        self.canonical_by_name_lower: Dict[str, Skill] = {}
        self.canonical_by_normalized: Dict[str, Skill] = {}
        self.skill_by_id: Dict[str, Skill] = {str(s.id): s for s in self.skills}

        for skill in self.skills:
            self.canonical_by_name_lower[skill.name.lower()] = skill
            self.canonical_by_normalized[normalize_string_key(skill.name)] = skill
            self.canonical_by_normalized[normalize_string_key(skill.slug)] = skill

        self.alias_by_name_lower: Dict[str, Skill] = {}
        self.alias_by_normalized: Dict[str, Skill] = {}

        for alias in self.aliases:
            parent_skill = self.skill_by_id.get(str(alias.skill_id))
            if parent_skill:
                self.alias_by_name_lower[alias.alias.lower()] = parent_skill
                self.alias_by_normalized[normalize_string_key(alias.alias)] = parent_skill
                self.alias_by_normalized[alias.normalized_alias.lower()] = parent_skill

    def resolve_mention(self, raw_mention: str) -> Optional[NormalizedSkillMatch]:
        mention_clean = raw_mention.strip()
        if not mention_clean:
            return None

        mention_lower = mention_clean.lower()
        mention_norm = normalize_string_key(mention_clean)

        # 1. Exact canonical name match (very high confidence)
        if mention_lower in self.canonical_by_name_lower:
            return NormalizedSkillMatch(
                skill=self.canonical_by_name_lower[mention_lower],
                raw_mention=mention_clean,
                confidence_score=0.95,
                match_type="canonical_exact",
            )

        # 2. Exact alias match (high confidence)
        if mention_lower in self.alias_by_name_lower:
            return NormalizedSkillMatch(
                skill=self.alias_by_name_lower[mention_lower],
                raw_mention=mention_clean,
                confidence_score=0.90,
                match_type="alias_exact",
            )

        # 3. Normalized canonical match (handles ReactJS, NextJS, Python3)
        if mention_norm in self.canonical_by_normalized:
            return NormalizedSkillMatch(
                skill=self.canonical_by_normalized[mention_norm],
                raw_mention=mention_clean,
                confidence_score=0.88,
                match_type="canonical_normalized",
            )

        # 4. Normalized alias match (handles react.js, postgre sql, k-8-s)
        if mention_norm in self.alias_by_normalized:
            return NormalizedSkillMatch(
                skill=self.alias_by_normalized[mention_norm],
                raw_mention=mention_clean,
                confidence_score=0.85,
                match_type="alias_normalized",
            )

        return None


def normalize_skills(
    db: Session,
    candidate_mentions: List[Tuple[str, str]],
    full_text_scan: Optional[str] = None,
) -> List[NormalizedSkillMatch]:
    """
    Resolves candidate mentions against the canonical taxonomy.
    Deduplicates by canonical skill ID, keeping the highest confidence score.
    """
    cache = SkillTaxonomyCache(db)
    resolved_by_skill_id: Dict[str, NormalizedSkillMatch] = {}

    # 1. Resolve explicit candidate mentions
    for mention, section_source in candidate_mentions:
        match = cache.resolve_mention(mention)
        if match:
            skill_id = str(match.skill.id)
            if skill_id not in resolved_by_skill_id or match.confidence_score > resolved_by_skill_id[skill_id].confidence_score:
                resolved_by_skill_id[skill_id] = match

    # 2. Scan full text for high-value canonical skills that might appear in narrative text
    if full_text_scan:
        for skill in cache.skills:
            skill_id = str(skill.id)
            if skill_id in resolved_by_skill_id:
                continue

            # Check boundary match for skills with distinct names (> 2 chars to avoid short false positives)
            if len(skill.name) > 2:
                pattern = rf"\b{re.escape(skill.name)}\b"
                if re.search(pattern, full_text_scan, re.IGNORECASE):
                    resolved_by_skill_id[skill_id] = NormalizedSkillMatch(
                        skill=skill,
                        raw_mention=skill.name,
                        confidence_score=0.80,
                        match_type="text_mention",
                    )

    return list(resolved_by_skill_id.values())
