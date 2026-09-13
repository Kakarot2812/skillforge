"""
Career Chatbot Service for SkillForge AI.
Post-MVP Phase 2, Checkpoint P2-C.

Core architectural invariants:
- "The LLM never decides what is true."
- "Deterministic systems decide what is true.
   AI explains, reasons over, and personalizes verified evidence."
- Chatbot is an evidence-grounded explanation layer over VerifiedContext.
- Deterministic sufficiency gate: rejects ungrounded queries before calling Qwen.
- Market facts alone never imply candidate skill possession or weakness.
- Zero database access, zero migrations, zero RAG, zero conversation persistence.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from uuid import UUID

from app.ai.chatbot.exceptions import (
    CareerChatError,
    CareerChatGenerationError,
    CareerChatServiceUnavailableError,
    CareerChatTimeoutError,
    CareerChatValidationError,
)
from app.ai.chatbot.models import (
    CareerChatRequest,
    CareerChatResponse,
    ChatResponseStatus,
    ChatUsageStats,
)
from app.ai.chatbot.prompts import build_career_chat_messages
from app.ai.context.exceptions import ContextValidationError
from app.ai.context.models import VerifiedContext
from app.ai.context.validation import validate_verified_context
from app.ai.qwen.client import QwenClient
from app.ai.qwen.exceptions import (
    QwenAPIError,
    QwenConnectionError,
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
)
from app.rag.exceptions import (
    RAGEmbeddingError,
    RAGRetrievalError,
    RAGStorageError,
)
from app.rag.models import RAGRetrievalFilter, RAGRetrievalResult
from app.rag.service import RAGService

logger = logging.getLogger(__name__)

# Common conversational stop words ignored when evaluating potential skill mentions
COMMON_QUERY_STOP_WORDS: Set[str] = {
    "a", "about", "all", "am", "an", "and", "any", "are", "as", "at", "be",
    "by", "can", "candidate", "could", "currently", "demand", "do", "first",
    "focus", "for", "from", "gap", "gaps", "github", "growth", "have", "high",
    "how", "i", "if", "in", "is", "it", "learn", "learning", "low", "market",
    "me", "medium", "missing", "more", "my", "next", "no", "not", "now", "of",
    "on", "or", "our", "partial", "priorities", "priority", "profile",
    "recommend", "resume", "score", "should", "skill", "skills", "so", "some",
    "status", "strong", "tell", "the", "their", "there", "these", "they",
    "this", "to", "was", "we", "weak", "what", "when", "where", "which", "who",
    "why", "will", "with", "would", "you", "your",
}


class CareerChatService:
    """
    Evidence-grounded explanation service.
    Orchestrates pre-Qwen validation, deterministic evidence sufficiency evaluation,
    prompt assembly, and local Qwen execution.
    """

    def __init__(
        self,
        qwen_client: Optional[QwenClient] = None,
        rag_service: Optional[RAGService] = None,
    ):
        self._owns_client = qwen_client is None
        self.client = qwen_client or QwenClient()
        self.rag_service = rag_service

    def __enter__(self) -> "CareerChatService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client and hasattr(self.client, "close"):
            self.client.close()

    def check_evidence_sufficiency(
        self,
        context: VerifiedContext,
        query: str,
    ) -> Tuple[bool, Optional[str], Tuple[UUID, ...]]:
        """
        Deterministically evaluates whether the verified context contains sufficient
        facts to ground an explanatory answer for the user query.

        Returns:
            (is_sufficient, failure_reason_if_insufficient, matched_skill_ids)
        """
        normalized_query = query.lower().strip()

        # Index verified skills present across different fact domains
        candidate_skill_map: Dict[str, UUID] = {
            s.skill_name.lower(): s.skill_id for s in context.skills
        }
        for e in context.evidence:
            candidate_skill_map[e.skill_name.lower()] = e.skill_id

        market_skill_map: Dict[str, UUID] = {
            m.skill_name.lower(): m.skill_id for m in context.market
        }
        priority_skill_map: Dict[str, UUID] = {
            p.skill_name.lower(): p.skill_id for p in context.priorities
        }

        all_context_skills: Dict[str, UUID] = {
            **candidate_skill_map,
            **market_skill_map,
            **priority_skill_map,
        }

        # 1. Match canonical skills in context against the query
        matched_skills: List[str] = []
        for name in all_context_skills:
            pattern = r"\b" + re.escape(name) + r"\b"
            if re.search(pattern, normalized_query):
                matched_skills.append(name)

        matched_skill_ids = tuple(all_context_skills[name] for name in matched_skills)

        # 2. Check if candidate query targets a specific unknown skill classification not in context
        target_skill_match = re.search(
            r"\b(?:weak at|strong in|partial in|missing in|status of)\s+([a-zA-Z0-9\+\#\.\-]+)\b",
            normalized_query,
        )
        if target_skill_match:
            potential_name = target_skill_match.group(1).lower().strip()
            if (
                potential_name
                and potential_name not in COMMON_QUERY_STOP_WORDS
                and potential_name not in all_context_skills
            ):
                return (
                    False,
                    f"The available verified evidence is insufficient to answer this question. "
                    f"The verified context contains no facts or classification for '{potential_name.capitalize()}'.",
                    (),
                )

        # 3. Intent classification: Candidate vs Market vs Priority
        is_candidate_intent = any(
            re.search(r"\b" + re.escape(w) + r"\b", normalized_query)
            for w in [
                "my", "resume", "github", "weak", "weakness",
                "weaknesses", "strong", "strength", "partial", "missing",
                "demonstrated", "score", "profile", "am i", "have i",
            ]
        )

        is_market_intent = any(
            re.search(r"\b" + re.escape(w) + r"\b", normalized_query)
            for w in ["market", "demand", "growth", "trend", "trending", "industry", "hiring", "adzuna"]
        )

        is_priority_intent = any(
            re.search(r"\b" + re.escape(w) + r"\b", normalized_query)
            for w in ["priority", "priorities", "prioritize", "what should i learn", "what to learn", "focus", "rank"]
        )

        # 4. If matched skills exist, enforce domain availability for those skills
        if matched_skills:
            for skill_name in matched_skills:
                # Rule 5: Market facts alone must never be interpreted as proof of candidate skill possession or weakness
                if is_candidate_intent and skill_name not in candidate_skill_map:
                    return (
                        False,
                        f"The available verified evidence is insufficient to evaluate candidate possession "
                        f"or weakness in '{skill_name.capitalize()}'. The context contains market demand data "
                        f"for this skill, but no candidate resume or GitHub evidence has been verified for you.",
                        matched_skill_ids,
                    )

                # If asking specifically about market for a skill with no market facts
                if is_market_intent and not is_candidate_intent and skill_name not in market_skill_map:
                    return (
                        False,
                        f"The available verified evidence is insufficient to explain market demand for "
                        f"'{skill_name.capitalize()}'. No verified market facts exist for this skill in the context.",
                        matched_skill_ids,
                    )

            # Skill has relevant facts for the query intent
            return True, None, matched_skill_ids

        # 5. Non-skill-specific queries: evaluate aggregate domain presence
        if is_priority_intent:
            if not context.priorities and not context.skills:
                return (
                    False,
                    "The available verified evidence is insufficient to provide learning priorities. "
                    "The verified context contains no priority rankings or classified skill gaps.",
                    (),
                )
            return True, None, ()

        if is_market_intent:
            if not context.market:
                return (
                    False,
                    "The available verified evidence is insufficient to explain market trends. "
                    "The verified context contains no market demand facts.",
                    (),
                )
            return True, None, ()

        if is_candidate_intent:
            if context.candidate is None and not context.skills and not context.evidence:
                return (
                    False,
                    "The available verified evidence is insufficient to answer questions about your profile. "
                    "The verified context contains no candidate scope, resume, or GitHub facts.",
                    (),
                )
            return True, None, ()

        # General, programming, or casual questions proceed to Qwen
        return True, None, ()

    def chat(self, request: CareerChatRequest) -> CareerChatResponse:
        """
        Executes an evidence-grounded chat interaction.

        1. Deterministically validates VerifiedContext.
        2. Validates query boundaries.
        3. Checks deterministic evidence sufficiency.
        4. Serializes context and builds deterministic prompt.
        5. Calls local QwenClient.
        6. Returns typed CareerChatResponse (status='EXPLANATORY').
        """
        # Step 1: Pre-validation of VerifiedContext
        try:
            validate_verified_context(request.verified_context)
        except ContextValidationError as exc:
            raise CareerChatValidationError(f"Invalid VerifiedContext: {str(exc)}") from exc

        # Step 2: Deterministic Evidence Sufficiency Gate
        is_sufficient, reason, referenced_skill_ids = self.check_evidence_sufficiency(
            context=request.verified_context,
            query=request.user_query,
        )

        if not is_sufficient:
            logger.info("Chatbot query rejected by deterministic sufficiency gate: %s", reason)
            return CareerChatResponse(
                explanation=reason or "The available verified evidence is insufficient to answer this question.",
                model=self.client.model,
                status=ChatResponseStatus.INSUFFICIENT_EVIDENCE,
                referenced_skill_ids=referenced_skill_ids,
                retrieved_evidence=(),
                usage=None,
            )

        # Step 3: Retrieve Supporting Evidence (if RAG service configured)
        retrieved_evidence: List[RAGRetrievalResult] = []
        if self.rag_service is not None:
            rag_filter = None
            if len(referenced_skill_ids) == 1:
                rag_filter = RAGRetrievalFilter(skill_id=referenced_skill_ids[0])
            try:
                retrieved_evidence = self.rag_service.retrieve(
                    query=request.user_query,
                    filters=rag_filter,
                )
            except RAGEmbeddingError as exc:
                logger.error("RAG embedding error during chat retrieval: %s", exc)
                raise CareerChatServiceUnavailableError(f"RAG embedding service error: {str(exc)}") from exc
            except (RAGStorageError, RAGRetrievalError) as exc:
                logger.error("RAG retrieval storage error: %s", exc)
                raise CareerChatGenerationError(f"RAG evidence retrieval failed: {str(exc)}") from exc
            except Exception as exc:
                logger.error("Unexpected error during RAG retrieval: %s", exc)
                raise CareerChatGenerationError(f"RAG retrieval failure: {str(exc)}") from exc

        # Step 4: Prompt Construction with Verified Ground Truth + Supporting Evidence
        messages = build_career_chat_messages(
            context=request.verified_context,
            user_query=request.user_query,
            retrieved_evidence=retrieved_evidence,
        )

        options: Dict[str, float] = {
            "temperature": float(request.temperature),
            "num_predict": int(request.max_tokens),
        }

        # Step 5: Qwen Execution with typed exception mapping
        # Note: QwenTimeoutError is a subclass of QwenConnectionError, so catch it first!
        try:
            chat_resp = self.client.chat(
                messages=messages,
                options=options,
            )
        except QwenTimeoutError as exc:
            logger.error("Local Ollama request timed out: %s", exc)
            raise CareerChatTimeoutError(
                f"Local AI explanation request timed out: {str(exc)}"
            ) from exc
        except (QwenConnectionError, QwenModelNotFoundError) as exc:
            logger.error("Local Ollama service unavailable: %s", exc)
            raise CareerChatServiceUnavailableError(
                f"Local AI explanation service is unavailable: {str(exc)}"
            ) from exc
        except (QwenAPIError, QwenResponseError) as exc:
            logger.error("Local Ollama API/generation error: %s", exc)
            raise CareerChatGenerationError(
                f"Local AI explanation generation error: {str(exc)}"
            ) from exc
        except Exception as exc:
            logger.error("Unexpected error during Qwen chat: %s", exc)
            raise CareerChatGenerationError(
                f"Unexpected generation failure: {str(exc)}"
            ) from exc

        # Step 6: Format strongly typed explanatory response
        usage_stats = ChatUsageStats(
            total_duration=chat_resp.total_duration,
            load_duration=chat_resp.load_duration,
            prompt_eval_count=chat_resp.prompt_eval_count,
            eval_count=chat_resp.eval_count,
        )

        return CareerChatResponse(
            explanation=chat_resp.message.content.strip(),
            model=chat_resp.model,
            status=ChatResponseStatus.EXPLANATORY,
            referenced_skill_ids=referenced_skill_ids,
            retrieved_evidence=tuple(retrieved_evidence),
            usage=usage_stats,
        )
