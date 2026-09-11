"""
SkillForge AI service.

Flow: validated ChatRequest -> render SkillForge context -> build system prompt
-> trim history -> call QwenClient -> normalise into ChatResponse.

``recommendations`` and ``sources`` in the response are derived
deterministically from the supplied context, never parsed from model output,
so the API cannot surface a model-invented priority or source.
"""
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Tuple

from app.qwen_ai.config import QwenSettings
from app.qwen_ai.context import RenderedContext, SkillForgeContext, render_context
from app.qwen_ai.prompts import build_system_prompt
from app.qwen_ai.qwen_client import QwenClient, QwenMessage, QwenRuntimeStatus
from app.qwen_ai.schemas import (
    ChatAnswer,
    ChatMessage,
    ChatMeta,
    ChatRequest,
    ChatResponse,
    Recommendation,
    SourceReference,
)
from app.qwen_ai.exceptions import QwenResponseError

logger = logging.getLogger(__name__)

MAX_RECOMMENDATIONS = 10
_PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
_BRACKETS = re.compile(r"\[([^\[\]]{1,40})\]")


def trim_history(history: Sequence[ChatMessage], max_messages: int, max_chars: int) -> List[ChatMessage]:
    """Keep the most recent turns that fit both the message and character budgets."""
    kept: List[ChatMessage] = []
    used = 0
    for msg in reversed(history):
        if len(kept) >= max_messages or used + len(msg.content) > max_chars:
            break
        kept.append(msg)
        used += len(msg.content)
    kept.reverse()
    return kept


def derive_recommendations(ctx: Optional[SkillForgeContext]) -> List[Recommendation]:
    """Echo SkillForge's own priorities, preferring the most authoritative source available."""
    if ctx is None:
        return []

    if ctx.roadmap:
        steps = sorted(enumerate(ctx.roadmap), key=lambda p: (p[1].order is None, p[1].order or 0, p[0]))
        items = [(s.skill, s.priority, "roadmap") for _, s in steps]
    elif ctx.skill_gaps:
        actionable = [(i, g) for i, g in enumerate(ctx.skill_gaps) if g.status != "STRONG"]
        actionable.sort(key=lambda p: (
            -(p[1].priority_score if p[1].priority_score is not None else -1.0),
            _PRIORITY_RANK.get(p[1].priority_level or "", 3),
            p[0],
        ))
        items = [(g.skill, g.priority_level, "skill_gap_engine") for _, g in actionable]
    elif ctx.priority_skills:
        items = [(s, None, "priority_skills") for s in ctx.priority_skills]
    elif ctx.missing_skills:
        items = [(s, None, "missing_skills") for s in ctx.missing_skills]
    else:
        return []

    return [
        Recommendation(rank=rank, skill=skill, priority=priority, origin=origin)  # type: ignore[arg-type]
        for rank, (skill, priority, origin) in enumerate(items[:MAX_RECOMMENDATIONS], start=1)
    ]


def cited_ids(answer: str) -> set:
    """Collect evidence ids cited like [E1] or [E1, E3]."""
    ids = set()
    for group in _BRACKETS.findall(answer):
        ids.update(part.strip().upper() for part in group.split(","))
    return ids


class QwenService:
    def __init__(self, client: QwenClient, settings: QwenSettings) -> None:
        self._client = client
        self._settings = settings

    def build_messages(self, request: ChatRequest) -> Tuple[List[QwenMessage], RenderedContext, int]:
        rendered = render_context(request.context, self._settings.QWEN_MAX_CONTEXT_CHARS)
        history = trim_history(
            request.conversation_history,
            self._settings.QWEN_MAX_HISTORY_MESSAGES,
            self._settings.QWEN_MAX_HISTORY_CHARS,
        )
        messages = [QwenMessage(role="system", content=build_system_prompt(rendered.text))]
        messages += [QwenMessage(role=m.role, content=m.content) for m in history]
        messages.append(QwenMessage(role="user", content=request.message))
        return messages, rendered, len(history)

    async def chat(self, request: ChatRequest) -> ChatResponse:
        conversation_id = request.conversation_id or uuid.uuid4()
        messages, rendered, history_used = self.build_messages(request)

        started = time.perf_counter()
        result = await self._client.chat(messages)
        latency_ms = int((time.perf_counter() - started) * 1000)

        answer = result.content.strip()
        if not answer:
            # e.g. the model only emitted a tool call, which this endpoint does not execute yet.
            raise QwenResponseError(detail="Model returned no text content for a chat request")

        cited = cited_ids(answer)
        sources = [
            SourceReference(id=eid, source=item.source, title=item.title,
                            evidence_type=item.evidence_type, cited=eid in cited)
            for eid, item in rendered.evidence
        ]

        logger.info(
            "qwen chat conversation=%s model=%s latency_ms=%d history=%d sections=%s prompt_tokens=%s completion_tokens=%s",
            conversation_id, result.model, latency_ms, history_used, ",".join(rendered.sections) or "-",
            result.prompt_tokens, result.completion_tokens,
        )

        return ChatResponse(
            data=ChatAnswer(
                answer=answer,
                conversation_id=conversation_id,
                grounded=rendered.text is not None,
                sources=sources,
                recommendations=derive_recommendations(request.context),
            ),
            meta=ChatMeta(
                model=result.model,
                generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                latency_ms=latency_ms,
                context_sections=rendered.sections,
                context_truncated=rendered.truncated,
                history_messages_used=history_used,
                answer_truncated=result.truncated,
            ),
        )

    async def health(self) -> QwenRuntimeStatus:
        return await self._client.check_health()