"""
Deterministic skill matcher and extraction engine for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-D.

Core principles:
- Deterministic extraction: "The LLM never decides what is true."
- Zero semantic models, embeddings, or external AI APIs.
- Strict token/word-boundary matching preventing substring false positives (e.g., 'Go' in 'good', 'C' in 'Cloud').
- Longest-phrase-first match priority to correctly resolve overlapping aliases (e.g., 'React Native' vs 'React').
- Deduplication: exactly one evidence entry per canonical skill per job.
- Preserves verbatim evidence text directly from source job text without rewriting.
"""

from dataclasses import dataclass
import logging
import re
from typing import Dict, List, Optional, Sequence, Set, Tuple
import uuid

from sqlalchemy.orm import Session

from app.db.models import Skill, SkillAlias
from app.services.market.models import MarketJobSkillEvidence

logger = logging.getLogger(__name__)

# Standard boundaries guarding against alphanumeric and programming symbol concatenation
LEFT_BOUNDARY = r"(?<![a-zA-Z0-9#+])"
RIGHT_BOUNDARY = r"(?![a-zA-Z0-9#+])"


def extract_evidence_snippet(text: str, start: int, end: int, window: int = 50) -> str:
    """
    Extracts a verbatim context snippet from text around a match span [start, end).
    Snaps to the nearest whitespace boundary where feasible.
    """
    if not text:
        return ""

    left = max(0, start - window)
    right = min(len(text), end + window)

    # Snap to nearest space boundaries
    if left > 0:
        space_pos = text.find(" ", left, start)
        if space_pos != -1:
            left = space_pos + 1

    if right < len(text):
        space_pos = text.rfind(" ", end, right)
        if space_pos != -1:
            right = space_pos

    snippet = text[left:right].strip()
    return snippet


@dataclass
class _CompiledTaxonomyRule:
    """Internal compiled rule for a canonical skill term or alias."""
    skill_id: uuid.UUID
    canonical_name: str
    matched_alias: str
    pattern: re.Pattern
    term_length: int
    is_multi_word: bool


def _build_regex_for_term(term: str) -> re.Pattern:
    """
    Compiles a word-boundary-aware regex pattern for a canonical skill term or alias.
    Handles programming symbols (C++, C#), multi-word phrases, and short terms (Go).
    """
    cleaned_term = term.strip()

    # Short skill "Go": case-sensitive to avoid matching English verb "go" or substrings in "good"
    if cleaned_term.lower() == "go":
        return re.compile(
            rf"{LEFT_BOUNDARY}(?:(?i:golang|go-lang)|\b(?:Go|GO)\b){RIGHT_BOUNDARY}"
        )

    # 1-character skills (e.g. C, R): case-sensitive boundary match
    if len(cleaned_term) == 1:
        return re.compile(
            rf"{LEFT_BOUNDARY}{re.escape(cleaned_term)}{RIGHT_BOUNDARY}"
        )

    # General terms: handle internal whitespace flexibly
    escaped = re.escape(cleaned_term)
    escaped = escaped.replace(r"\ ", r"\s+")

    # Use boundary assertions that respect # and +
    pattern_str = rf"{LEFT_BOUNDARY}{escaped}{RIGHT_BOUNDARY}"
    return re.compile(pattern_str, re.IGNORECASE)


class DeterministicSkillMatcher:
    """
    Deterministic skill matcher indexing canonical skills and aliases from PostgreSQL.
    Extracts skill mentions from market job text using longest-match-first priority.
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        skills: Optional[Sequence[Skill]] = None,
        aliases: Optional[Sequence[SkillAlias]] = None,
    ):
        """
        Initializes matcher by loading skills and aliases from database or explicit lists.
        """
        if skills is None and db is not None:
            skills = db.query(Skill).all()
        if aliases is None and db is not None:
            aliases = db.query(SkillAlias).all()

        self._skills: List[Skill] = list(skills or [])
        self._aliases: List[SkillAlias] = list(aliases or [])
        self._rules: List[_CompiledTaxonomyRule] = []

        self._compile_rules()

    def _compile_rules(self) -> None:
        """
        Compiles and sorts regex rules for all canonical skills and aliases.
        Longest terms are placed first to guarantee longest-match-first resolution.
        """
        rules_map: Dict[Tuple[uuid.UUID, str], _CompiledTaxonomyRule] = {}

        # 1. Canonical skill names and slugs
        for skill in self._skills:
            # Canonical name
            key_name = (skill.id, skill.name.lower())
            if key_name not in rules_map:
                rules_map[key_name] = _CompiledTaxonomyRule(
                    skill_id=skill.id,
                    canonical_name=skill.name,
                    matched_alias=skill.name,
                    pattern=_build_regex_for_term(skill.name),
                    term_length=len(skill.name),
                    is_multi_word=" " in skill.name,
                )

            # Canonical slug if distinct from name
            if skill.slug and skill.slug.lower() != skill.name.lower() and len(skill.slug) > 2:
                key_slug = (skill.id, skill.slug.lower())
                if key_slug not in rules_map:
                    rules_map[key_slug] = _CompiledTaxonomyRule(
                        skill_id=skill.id,
                        canonical_name=skill.name,
                        matched_alias=skill.slug,
                        pattern=_build_regex_for_term(skill.slug),
                        term_length=len(skill.slug),
                        is_multi_word="-" in skill.slug or " " in skill.slug,
                    )

        # 2. Skill aliases from taxonomy
        skills_by_id = {s.id: s for s in self._skills}
        for alias in self._aliases:
            parent_skill = skills_by_id.get(alias.skill_id)
            if not parent_skill:
                continue

            clean_alias = alias.alias.strip()
            if not clean_alias:
                continue

            key_alias = (parent_skill.id, clean_alias.lower())
            if key_alias not in rules_map:
                rules_map[key_alias] = _CompiledTaxonomyRule(
                    skill_id=parent_skill.id,
                    canonical_name=parent_skill.name,
                    matched_alias=clean_alias,
                    pattern=_build_regex_for_term(clean_alias),
                    term_length=len(clean_alias),
                    is_multi_word=" " in clean_alias or "-" in clean_alias,
                )

        # Sort rules strictly by term length descending (longest first)
        # Secondary sort by canonical name to guarantee deterministic ordering
        self._rules = sorted(
            rules_map.values(),
            key=lambda r: (-r.term_length, r.canonical_name, r.matched_alias),
        )

        logger.debug("Compiled %d deterministic skill matching rules", len(self._rules))

    def match_text_spans(
        self,
        text: Optional[str],
        source_field: str,
        market_job_id: Optional[uuid.UUID] = None,
    ) -> List[MarketJobSkillEvidence]:
        """
        Extracts non-overlapping skill matches from a given text string.
        Enforces longest-match-first priority.
        """
        if not text or not text.strip():
            return []

        clean_text = text.strip()
        claimed_spans: List[Tuple[int, int]] = []
        raw_matches: List[Tuple[int, MarketJobSkillEvidence]] = []

        for rule in self._rules:
            for match in rule.pattern.finditer(clean_text):
                start, end = match.start(), match.end()

                # Check if this match overlaps with an existing claimed (longer) span
                overlaps = any(
                    max(start, c_start) < min(end, c_end)
                    for c_start, c_end in claimed_spans
                )

                if overlaps:
                    continue

                claimed_spans.append((start, end))
                snippet = extract_evidence_snippet(clean_text, start, end)

                evidence = MarketJobSkillEvidence(
                    market_job_id=market_job_id,
                    skill_id=rule.skill_id,
                    canonical_skill_name=rule.canonical_name,
                    matched_alias=rule.matched_alias,
                    source_field=source_field,
                    evidence_text=snippet,
                    extraction_method="deterministic_taxonomy_match",
                    confidence_score=1.0,
                )
                raw_matches.append((start, evidence))

        # Sort matches by start position in text
        raw_matches.sort(key=lambda x: x[0])
        return [m[1] for m in raw_matches]

    def extract_skills_for_job(
        self,
        title: Optional[str],
        description: Optional[str],
        market_job_id: Optional[uuid.UUID] = None,
    ) -> List[MarketJobSkillEvidence]:
        """
        Extracts canonical skills from job title and description.
        Guarantees:
        - Each canonical skill appears at most once per job.
        - Title matches take precedence over description matches for source_field.
        - Deterministic output ordering.
        """
        extracted_by_skill_id: Dict[uuid.UUID, MarketJobSkillEvidence] = {}

        # 1. Scan title (highest precision)
        title_matches = self.match_text_spans(
            text=title,
            source_field="title",
            market_job_id=market_job_id,
        )
        for match in title_matches:
            if match.skill_id not in extracted_by_skill_id:
                extracted_by_skill_id[match.skill_id] = match

        # 2. Scan description (broad context)
        desc_matches = self.match_text_spans(
            text=description,
            source_field="description",
            market_job_id=market_job_id,
        )
        for match in desc_matches:
            # Only add if not already captured in title
            if match.skill_id not in extracted_by_skill_id:
                extracted_by_skill_id[match.skill_id] = match

        # Return deterministically sorted by canonical skill name
        return sorted(
            extracted_by_skill_id.values(),
            key=lambda e: e.canonical_skill_name,
        )
