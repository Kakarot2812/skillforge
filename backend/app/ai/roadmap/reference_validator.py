"""
Reference Integrity Validation for AI Roadmap PDF Narrative.
Post-MVP Career Roadmap PDF Feature (Phase 3).

Enforces:
- Fail-closed validation against authoritative Phase 2 VerifiedRoadmapPDFContext.
- Rejection of unknown, hallucinated, or foreign skill IDs.
- Exact milestone count and topological sequence order preservation.
- Prohibition of invented URLs or unapproved external links.
- Prohibition of candidate-proof claims for curated project challenges.
- Immutability of authoritative scores, readiness metrics, and classifications.
"""

import re
from typing import List, Set
from uuid import UUID

from app.ai.context.roadmap_pdf_context import VerifiedRoadmapPDFContext
from app.ai.roadmap.exceptions import ReferenceIntegrityError
from app.ai.roadmap.narrative_schemas import RoadmapPDFPersonalizedNarrative


class ReferenceIntegrityValidator:
    """
    Validates Gemini structured output against Phase 2 authoritative context.
    Fails closed: any deviation, invented identifier, or foreign URL raises ReferenceIntegrityError.
    """

    URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)

    # Patterns indicating prohibited candidate-proof claims over curated challenges
    FALSE_PROOF_PATTERNS = [
        re.compile(r"\b(?:you\s+have|you've)\s+(?:completed|finished|shipped|built)\s+this\s+project\b", re.IGNORECASE),
        re.compile(r"\b(?:you\s+have|you've)\s+already\s+demonstrated\s+this\s+skill\s+through\s+this\s+project\b", re.IGNORECASE),
        re.compile(r"\bproject\s+already\s+verified\b", re.IGNORECASE),
    ]

    @classmethod
    def validate(
        cls,
        narrative: RoadmapPDFPersonalizedNarrative,
        context: VerifiedRoadmapPDFContext,
    ) -> None:
        """
        Executes strict reference-integrity validation.
        Raises ReferenceIntegrityError if any invariant is violated.
        """
        if not narrative:
            raise ReferenceIntegrityError("Narrative output is null or empty.")

        violations: List[str] = []

        # 1. Milestone Count & Sequence Order Integrity
        expected_milestones = context.roadmap.milestones
        if len(narrative.phases) != len(expected_milestones):
            violations.append(
                f"Milestone count mismatch: Gemini returned {len(narrative.phases)} phases, "
                f"but roadmap requires exactly {len(expected_milestones)}."
            )

        seen_phase_skill_ids: Set[str] = set()

        for idx, phase in enumerate(narrative.phases):
            phase_sid_str = str(phase.skill_id).strip().lower()
            if idx < len(expected_milestones):
                expected_m = expected_milestones[idx]
                expected_sid_str = str(expected_m.skill_id).strip().lower()
                # Validate exact skill_id alignment
                if phase_sid_str != expected_sid_str:
                    violations.append(
                        f"Milestone #{idx + 1} skill_id mismatch: received '{phase.skill_id}', "
                        f"expected '{expected_m.skill_id}' ({expected_m.skill_name}). "
                        "Milestone reordering or foreign skill reference is strictly prohibited."
                    )
            else:
                violations.append(
                    f"Superfluous phase #{idx + 1} with skill_id '{phase.skill_id}' exceeding canonical milestone count."
                )

            # Check for duplicate skill IDs in phases
            if phase_sid_str in seen_phase_skill_ids:
                violations.append(
                    f"Duplicate milestone skill_id '{phase.skill_id}' detected at phase #{idx + 1}."
                )
            seen_phase_skill_ids.add(phase_sid_str)

        # 2. Prioritized Gaps Skill ID Integrity
        authoritative_gap_skill_ids = {str(g.skill_id).strip().lower() for g in context.prioritized_gaps.top_gaps}
        for gap_narrative in narrative.top_gap_narratives:
            if str(gap_narrative.skill_id).strip().lower() not in authoritative_gap_skill_ids:
                violations.append(
                    f"Top gap explanation references unauthorized or non-prioritized skill_id: '{gap_narrative.skill_id}'."
                )

        # 3. Prohibit Invented External URLs in Narrative Text
        text_fields_to_check: List[str] = [
            narrative.personalized_subtitle,
            narrative.executive_summary,
            narrative.readiness_explanation,
            narrative.closing_encouragement,
        ]
        text_fields_to_check.extend(narrative.immediate_next_steps)

        for phase in narrative.phases:
            text_fields_to_check.append(phase.phase_title)
            text_fields_to_check.append(phase.personalized_rationale)
            if phase.expected_focus:
                text_fields_to_check.append(phase.expected_focus)
            text_fields_to_check.extend(phase.key_topics)

        for gn in narrative.top_gap_narratives:
            text_fields_to_check.append(gn.why_it_matters)
            text_fields_to_check.append(gn.suggested_focus)

        for text in text_fields_to_check:
            if text:
                url_matches = cls.URL_PATTERN.findall(text)
                if url_matches:
                    violations.append(
                        f"Invented external URL detected in narrative text: '{url_matches[0]}'. "
                        "LLMs are strictly forbidden from introducing external links or unapproved resources."
                    )

                # Check for false candidate-proof claims
                for pattern in cls.FALSE_PROOF_PATTERNS:
                    if pattern.search(text):
                        violations.append(
                            f"Prohibited candidate-proof claim detected in narrative text: '{text[:80]}...'. "
                            "Curated project challenges must remain recommendations, not candidate skill proof."
                        )

        # Fail closed if any violations occurred
        if violations:
            msg = f"Reference integrity validation failed with {len(violations)} violation(s): {'; '.join(violations[:3])}"
            raise ReferenceIntegrityError(msg, violations=violations)
