"""
AI Roadmap PDF Narrative Generation Service.
Post-MVP Career Roadmap PDF Feature (Phase 3).

Executes the pipeline:
VerifiedRoadmapPDFContext
        ↓
Gemini 2.5 Flash (via with_structured_output)
        ↓
Structured Pydantic output (RoadmapPDFPersonalizedNarrative)
        ↓
Reference-integrity validation (ReferenceIntegrityValidator)
        ↓
Validated personalized roadmap content (ValidatedRoadmapPDFContent)

Core Architectural Invariants:
- Exactly ONE structured Gemini invocation.
- "Deterministic systems decide what is true. AI explains, reasons over, and personalizes verified evidence."
- All authoritative metrics, classifications, ordering, and evidence are immutable from Phase 2.
- Fail-closed reference integrity validation.
"""

from datetime import datetime, timezone
import logging
from typing import List, Optional

from app.ai.context.roadmap_pdf_context import VerifiedRoadmapPDFContext
from app.ai.gemini.client import GeminiClient
from app.ai.gemini.exceptions import GeminiError
from app.ai.roadmap.exceptions import (
    NarrativeGenerationError,
    NarrativeValidationError,
    ReferenceIntegrityError,
)
from app.ai.roadmap.narrative_prompts import build_roadmap_narrative_messages
from app.ai.roadmap.narrative_schemas import (
    RoadmapPDFPersonalizedNarrative,
    ValidatedRoadmapPDFContent,
    ValidatedRoadmapPhase,
    ValidatedTopSkillGap,
)
from app.ai.roadmap.reference_validator import ReferenceIntegrityValidator

logger = logging.getLogger(__name__)


class RoadmapPDFNarrativeService:
    """
    Orchestrates the generation and reference-integrity validation of personalized
    narratives for the Career Roadmap PDF using Gemini 2.5 Flash.
    """

    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        validator: Optional[ReferenceIntegrityValidator] = None,
    ):
        self._gemini_client = gemini_client
        self.validator = validator or ReferenceIntegrityValidator()

    @property
    def gemini_client(self) -> GeminiClient:
        """Lazily initialize GeminiClient if not provided during construction."""
        if self._gemini_client is None:
            self._gemini_client = GeminiClient()
        return self._gemini_client

    def generate_validated_narrative(
        self,
        context: VerifiedRoadmapPDFContext,
    ) -> ValidatedRoadmapPDFContent:
        """
        Generates and validates personalized narrative text over the supplied
        Phase 2 VerifiedRoadmapPDFContext.

        Args:
            context: Authoritative deterministic context from Phase 2.

        Returns:
            ValidatedRoadmapPDFContent: Fully assembled, reference-validated document.

        Raises:
            NarrativeValidationError: If input context is invalid.
            NarrativeGenerationError: If Gemini fails to generate structured output.
            ReferenceIntegrityError: If Gemini output violates reference integrity.
        """
        if not context or not isinstance(context, VerifiedRoadmapPDFContext):
            raise NarrativeValidationError("A valid VerifiedRoadmapPDFContext instance is required.")

        # 1. Format bounded, privacy-conscious prompt messages
        messages = build_roadmap_narrative_messages(context)

        # 2. Invoke Gemini 2.5 Flash via LangChain with_structured_output exactly once
        try:
            structured_runnable = self.gemini_client.with_structured_output(
                RoadmapPDFPersonalizedNarrative
            )
            narrative = structured_runnable.invoke(messages)
        except GeminiError as exc:
            logger.error("Gemini invocation failed during roadmap narrative generation: %s", exc.message)
            raise NarrativeGenerationError(
                f"Gemini structured output generation failed: {exc.message}",
                original_exception=exc,
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error during roadmap narrative generation: %s", str(exc))
            raise NarrativeGenerationError(
                f"Unexpected generation failure during narrative synthesis: {str(exc)}",
                original_exception=exc,
            ) from exc

        # 3. Guard against null or malformed response
        if not narrative or not isinstance(narrative, RoadmapPDFPersonalizedNarrative):
            raise NarrativeGenerationError(
                "Gemini structured output invocation returned empty or malformed result."
            )

        # 4. Perform fail-closed reference integrity validation
        self.validator.validate(narrative, context)

        # 5. Assemble authoritative immutable document
        return self._assemble_validated_content(narrative, context)

    def _assemble_validated_content(
        self,
        narrative: RoadmapPDFPersonalizedNarrative,
        context: VerifiedRoadmapPDFContext,
    ) -> ValidatedRoadmapPDFContent:
        """
        Assembles the final ValidatedRoadmapPDFContent.
        All authoritative metrics, counts, and identifiers are copied directly from
        the Phase 2 context; Gemini only enriches approved narrative fields.
        """
        # Merge authoritative roadmap milestones with validated narrative phase descriptions
        validated_phases: List[ValidatedRoadmapPhase] = []
        for milestone, phase_narrative in zip(context.roadmap.milestones, narrative.phases):
            v_phase = ValidatedRoadmapPhase(
                # Authoritative Phase 2 facts
                milestone_id=milestone.milestone_id,
                order_index=milestone.order_index,
                skill_id=milestone.skill_id,
                skill_name=milestone.skill_name,
                canonical_slug=milestone.canonical_slug,
                category=milestone.category,
                gap_status=milestone.gap_status,
                priority_score=milestone.priority_score,
                priority_level=milestone.priority_level,
                is_transitive_prerequisite=milestone.is_transitive_prerequisite,
                deterministic_reason=milestone.deterministic_reason,
                status=milestone.status,
                prerequisites=milestone.prerequisites,
                learning_objectives=milestone.learning_objectives,
                resources=milestone.resources,
                project=milestone.project,
                latest_verification=milestone.latest_verification,
                # Enriched narrative fields
                phase_title=phase_narrative.phase_title,
                personalized_rationale=phase_narrative.personalized_rationale,
                key_topics=tuple(phase_narrative.key_topics),
                expected_focus=phase_narrative.expected_focus,
            )
            validated_phases.append(v_phase)

        # Merge authoritative top gaps with validated explanations
        gap_narrative_map = {str(gn.skill_id).strip().lower(): gn for gn in narrative.top_gap_narratives}
        validated_top_gaps: List[ValidatedTopSkillGap] = []
        for gap in context.prioritized_gaps.top_gaps:
            gn = gap_narrative_map.get(str(gap.skill_id).strip().lower())
            v_gap = ValidatedTopSkillGap(
                # Authoritative Phase 2 facts
                skill_id=gap.skill_id,
                skill_name=gap.skill_name,
                canonical_slug=gap.canonical_slug,
                category=gap.category,
                gap_status=gap.gap_status,
                priority_score=gap.priority_score,
                priority_level=gap.priority_level,
                demand_score=gap.demand_score,
                growth_rate=gap.growth_rate,
                # Validated narrative fields
                why_it_matters=gn.why_it_matters if gn else None,
                suggested_focus=gn.suggested_focus if gn else None,
            )
            validated_top_gaps.append(v_gap)

        return ValidatedRoadmapPDFContent(
            schema_version="v1.0",
            generated_at=datetime.now(timezone.utc),
            # Authoritative Phase 2 facts (immutable)
            roadmap_id=context.roadmap.roadmap_id,
            candidate=context.candidate,
            readiness=context.readiness,
            target_role_title=context.roadmap.target_role_title,
            location=context.roadmap.location,
            total_milestones=context.roadmap.total_milestones,
            high_priority_count=context.roadmap.high_priority_count,
            medium_priority_count=context.roadmap.medium_priority_count,
            low_priority_count=context.roadmap.low_priority_count,
            transitive_prerequisite_count=context.roadmap.transitive_prerequisite_count,
            market_facts=context.market_facts,
            verification_evidence=context.verification_evidence,
            weekly_hours_recommendation=None,  # Strictly None - never fabricated
            verification_hash=context.verification_hash,
            # Validated Gemini Narrative facts
            personalized_subtitle=narrative.personalized_subtitle,
            executive_summary=narrative.executive_summary,
            readiness_explanation=narrative.readiness_explanation,
            validated_top_gaps=tuple(validated_top_gaps),
            validated_phases=tuple(validated_phases),
            immediate_next_steps=tuple(narrative.immediate_next_steps),
            closing_encouragement=narrative.closing_encouragement,
        )


# Global singleton helper
roadmap_pdf_narrative_service = RoadmapPDFNarrativeService()
