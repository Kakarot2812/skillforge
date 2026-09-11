"""
AI Roadmap Explanation Service for SkillForge AI.
Post-MVP Phase 4.

Provides non-authoritative explanation of canonical roadmaps using local Qwen 3 8B.
Fails gracefully without affecting canonical roadmap persistence or presentation.
"""

import logging
from typing import Optional, Tuple
from uuid import UUID

from app.ai.qwen.client import QwenClient
from app.ai.qwen.exceptions import (
    QwenAPIError,
    QwenConnectionError,
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
)
from app.ai.roadmap.prompts import build_roadmap_explanation_messages
from app.schemas.roadmap import AIRoadmapExplainResponse, CanonicalRoadmapData

logger = logging.getLogger(__name__)


class AIRoadmapExplanationService:
    """Explains and personalizes canonical roadmaps using local Qwen 3 8B."""

    def __init__(self, qwen_client: Optional[QwenClient] = None):
        self._owns_client = qwen_client is None
        self.client = qwen_client or QwenClient()

    def close(self) -> None:
        if self._owns_client and hasattr(self.client, "close"):
            self.client.close()

    def explain(
        self,
        roadmap: CanonicalRoadmapData,
        user_query: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AIRoadmapExplainResponse:
        """
        Generates a non-authoritative explanatory summary of the canonical roadmap.
        Never alters milestone ordering, priority tiers, or required skills.
        """
        messages = build_roadmap_explanation_messages(
            roadmap=roadmap,
            user_query=user_query,
        )

        options = {
            "temperature": float(temperature),
            "num_predict": 1024,
        }

        try:
            resp = self.client.chat(messages=messages, options=options)
            content = resp.message.content.strip()
        except Exception as exc:
            logger.error("AI roadmap explanation failed: %s", exc)
            raise exc

        # Extract referenced skill slugs
        referenced_slugs = tuple(m.canonical_slug for m in roadmap.milestones)

        return AIRoadmapExplainResponse(
            roadmap_id=roadmap.id,
            target_role_title=roadmap.target_role_title,
            content=content,
            model=self.client.model,
            status="EXPLANATORY",
            referenced_skill_slugs=referenced_slugs,
        )
