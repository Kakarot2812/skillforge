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
from app.ai.chatbot.langchain_history import (
    get_langchain_history,
    langchain_messages_to_provider,
)
from app.ai.chatbot.personalization import (
    PersonalizationContext,
    ProfileContext,
    assemble_personalization_context,
)
from app.ai.chatbot.prompts import (
    build_career_chat_langchain_messages,
    build_career_chat_messages,
)
from langchain_core.messages import BaseMessage
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
from app.services.conversation_service import (
    ConversationService,
    conversation_service as default_conversation_service,
)
from app.services.user_profile_service import (
    UserProfileNotFoundError,
    UserProfileService,
    user_profile_service as default_user_profile_service,
    UserNotFoundError,
)
from sqlalchemy.orm import Session
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
        conversation_service: Optional[ConversationService] = None,
        user_profile_service: Optional[UserProfileService] = None,
        client: Optional[QwenClient] = None,
    ):
        effective_client = qwen_client or client
        self._owns_client = effective_client is None
        self.client = effective_client or QwenClient()
        self.rag_service = rag_service
        self.conversation_service = conversation_service or default_conversation_service
        self.user_profile_service = user_profile_service or default_user_profile_service
        self._last_messages: Optional[List[Dict[str, str]]] = None
        self._last_langchain_messages: Optional[List[BaseMessage]] = None

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

    def chat(
        self,
        request: CareerChatRequest,
        db: Optional[Session] = None,
        user_id: Optional[UUID] = None,
    ) -> CareerChatResponse:
        """
        Executes an evidence-grounded chat interaction.

        1. If persistent conversation requested, verifies ownership and persists user message.
        2. Deterministically validates VerifiedContext.
        3. Validates query boundaries.
        4. Checks deterministic evidence sufficiency.
        5. Serializes context, incorporates LangChain dialogue history, and builds prompt.
        6. Calls local QwenClient.
        7. If persistent conversation, persists assistant message on success.
        8. Returns typed CareerChatResponse.
        """
        # Step 0: Persistent Conversation Validation & User Message Persistence
        is_persistent = request.conversation_id is not None
        user_msg_rec = None
        if is_persistent:
            if db is None or user_id is None:
                raise CareerChatValidationError(
                    "Database session and user_id are required when conversation_id is provided."
                )
            # Verify ownership and persist user message via ConversationService
            user_msg_rec = self.conversation_service.add_message(
                db=db,
                conversation_id=request.conversation_id,
                user_id=user_id,
                role="user",
                content=request.user_query,
            )

        # Step 0b: Load User Profile via UserProfileService (service layer access only)
        profile_model = None
        if db is not None and user_id is not None:
            try:
                profile_model = self.user_profile_service.get_profile(db=db, user_id=user_id)
            except (UserProfileNotFoundError, UserNotFoundError):
                profile_model = None

        profile_context = ProfileContext.from_model(profile_model)

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
            insufficient_text = reason or "The available verified evidence is insufficient to answer this question."
            asst_msg_id = None
            if is_persistent and db is not None and user_id is not None:
                asst_rec = self.conversation_service.add_message(
                    db=db,
                    conversation_id=request.conversation_id,
                    user_id=user_id,
                    role="assistant",
                    content=insufficient_text,
                )
                asst_msg_id = asst_rec.id

            return CareerChatResponse(
                explanation=insufficient_text,
                model=self.client.model,
                status=ChatResponseStatus.INSUFFICIENT_EVIDENCE,
                referenced_skill_ids=referenced_skill_ids,
                retrieved_evidence=(),
                usage=None,
                conversation_id=request.conversation_id,
                message_id=asst_msg_id,
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

        # Step 4: Prompt Construction with Verified Ground Truth + Supporting Evidence + LangChain History + Profile
        history_messages = None
        if is_persistent and db is not None and user_id is not None:
            history_messages = get_langchain_history(
                db=db,
                conversation_id=request.conversation_id,
                user_id=user_id,
                conversation_service=self.conversation_service,
                limit=20,
                exclude_message_id=user_msg_rec.id if user_msg_rec else None,
            )

        # Assemble immutable PersonalizationContext
        personalization_context = assemble_personalization_context(
            verified_context=request.verified_context,
            profile=profile_model,
            chat_history=history_messages,
        )

        lc_messages = build_career_chat_langchain_messages(
            context=request.verified_context,
            user_query=request.user_query,
            retrieved_evidence=retrieved_evidence,
            history_messages=history_messages,
            profile_context=profile_context,
        )
        self._last_langchain_messages = lc_messages
        messages = langchain_messages_to_provider(lc_messages)
        self._last_messages = messages

        options: Dict[str, float] = {
            "temperature": float(request.temperature),
            "num_predict": int(request.max_tokens),
        }

        # Step 5: Qwen Execution with typed exception mapping
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

        # Step 6: Persist Assistant Response on Successful Generation
        asst_msg_id = None
        explanation_text = chat_resp.message.content.strip()
        if is_persistent and db is not None and user_id is not None:
            asst_rec = self.conversation_service.add_message(
                db=db,
                conversation_id=request.conversation_id,
                user_id=user_id,
                role="assistant",
                content=explanation_text,
            )
            asst_msg_id = asst_rec.id

        # Step 7: Format strongly typed explanatory response
        usage_stats = ChatUsageStats(
            total_duration=chat_resp.total_duration,
            load_duration=chat_resp.load_duration,
            prompt_eval_count=chat_resp.prompt_eval_count,
            eval_count=chat_resp.eval_count,
        )

        return CareerChatResponse(
            explanation=explanation_text,
            model=chat_resp.model,
            status=ChatResponseStatus.EXPLANATORY,
            referenced_skill_ids=referenced_skill_ids,
            retrieved_evidence=tuple(retrieved_evidence),
            usage=usage_stats,
            conversation_id=request.conversation_id,
            message_id=asst_msg_id,
        )

