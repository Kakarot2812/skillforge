import asyncio
import uuid
from typing import List, Sequence

import pytest

from app.qwen_ai.exceptions import QwenResponseError, QwenTimeoutError
from app.qwen_ai.prompts import NO_CONTEXT_NOTICE, SKILLFORGE_IDENTITY
from app.qwen_ai.qwen_client import QwenChatResult, QwenMessage
from app.qwen_ai.qwen_service import QwenService, cited_ids, derive_recommendations, trim_history
from app.qwen_ai.context import SkillForgeContext
from app.qwen_ai.schemas import ChatMessage, ChatRequest
from tests.qwen_ai.helpers import make_settings


class FakeClient:
    """Records messages and returns a canned reply; no network."""

    def __init__(self, reply: str = "Answer.", *, error: Exception = None, done_reason: str = "stop"):
        self.reply, self.error, self.done_reason = reply, error, done_reason
        self.calls: List[Sequence[QwenMessage]] = []

    async def chat(self, messages, **_):
        self.calls.append(list(messages))
        if self.error:
            raise self.error
        return QwenChatResult(content=self.reply, model="qwen3:8b", done_reason=self.done_reason)


def run_chat(request: ChatRequest, client: FakeClient = None, **settings):
    client = client or FakeClient()
    service = QwenService(client, make_settings(**settings))
    return asyncio.run(service.chat(request)), client


def test_prompt_without_context_is_labelled_general():
    response, client = run_chat(ChatRequest(message="What should I learn after Docker?"))
    messages = client.calls[0]
    assert messages[0].role == "system"
    assert messages[0].content.startswith(SKILLFORGE_IDENTITY)
    assert NO_CONTEXT_NOTICE in messages[0].content
    assert "<skillforge_context>\n" not in messages[0].content
    assert messages[-1] == QwenMessage("user", "What should I learn after Docker?")
    assert response.data.grounded is False
    assert response.data.recommendations == []


def test_prompt_contains_skillforge_rules():
    _, client = run_chat(ChatRequest(message="hi"))
    system = client.calls[0][0].content
    for phrase in ("source of truth", "Never invent", "Never promise", "clarifying question", "[E1]"):
        assert phrase in system


def test_context_is_injected_and_used_for_recommendations():
    ctx = {"target_role": "Backend Engineer", "current_skills": ["Python", "SQL", "REST"],
           "missing_skills": ["Docker", "AWS", "Kubernetes"], "priority_skills": ["Docker", "AWS"]}
    response, client = run_chat(ChatRequest(message="What should I learn next?", context=ctx))
    system = client.calls[0][0].content
    assert "<skillforge_context>\nTarget role: Backend Engineer" in system and NO_CONTEXT_NOTICE not in system
    assert "Priority skills (highest first): Docker, AWS" in system
    assert response.data.grounded is True
    assert [(r.rank, r.skill, r.origin) for r in response.data.recommendations] == [
        (1, "Docker", "priority_skills"), (2, "AWS", "priority_skills")]
    assert response.meta.context_sections == ["target", "current_skills", "missing_skills", "priority_skills"]


def test_conversation_history_is_forwarded_in_order():
    history = [ChatMessage(role="user", content="What is Docker?"),
               ChatMessage(role="assistant", content="Docker is a container platform.")]
    response, client = run_chat(ChatRequest(message="Why learn it for backend?", conversation_history=history))
    roles = [m.role for m in client.calls[0]]
    assert roles == ["system", "user", "assistant", "user"]
    assert client.calls[0][1].content == "What is Docker?"
    assert response.meta.history_messages_used == 2


def test_history_is_trimmed_to_budget():
    history = [ChatMessage(role="user" if i % 2 == 0 else "assistant", content=f"turn {i}") for i in range(30)]
    response, client = run_chat(ChatRequest(message="q", conversation_history=history),
                                QWEN_MAX_HISTORY_MESSAGES=4)
    assert response.meta.history_messages_used == 4
    assert client.calls[0][1].content == "turn 26"  # most recent kept


def test_trim_history_respects_char_budget():
    history = [ChatMessage(role="user", content="a" * 100), ChatMessage(role="assistant", content="b" * 100)]
    assert [m.content[0] for m in trim_history(history, 10, 150)] == ["b"]
    assert trim_history(history, 0, 1000) == []


def test_conversation_id_is_preserved_or_generated():
    cid = uuid.uuid4()
    assert run_chat(ChatRequest(message="q", conversation_id=cid))[0].data.conversation_id == cid
    assert isinstance(run_chat(ChatRequest(message="q"))[0].data.conversation_id, uuid.UUID)


def test_sources_only_include_shown_evidence_and_track_citations():
    ctx = {"evidence": [{"source": "rag://docker", "title": "Docker primer", "content": "c1"},
                        {"source": "rag://aws", "content": "c2"}]}
    response, _ = run_chat(ChatRequest(message="Why Docker?", context=ctx),
                           FakeClient("Containers matter [E1]."))
    sources = response.data.sources
    assert [(s.id, s.source, s.cited) for s in sources] == [("E1", "rag://docker", True), ("E2", "rag://aws", False)]


def test_truncated_generation_is_flagged():
    response, _ = run_chat(ChatRequest(message="q"), FakeClient("partial", done_reason="length"))
    assert response.meta.answer_truncated is True


def test_client_errors_propagate():
    with pytest.raises(QwenTimeoutError):
        run_chat(ChatRequest(message="q"), FakeClient(error=QwenTimeoutError()))


def test_empty_answer_rejected():
    with pytest.raises(QwenResponseError):
        run_chat(ChatRequest(message="q"), FakeClient("   "))


def test_recommendations_prefer_roadmap_order():
    ctx = SkillForgeContext.model_validate({
        "roadmap": [{"skill": "Kubernetes", "priority": "MEDIUM", "order": 3},
                    {"skill": "Docker", "priority": "HIGH", "order": 1},
                    {"skill": "AWS", "priority": "HIGH", "order": 2}],
        "priority_skills": ["Something else"],
    })
    assert [(r.skill, r.priority, r.origin) for r in derive_recommendations(ctx)] == [
        ("Docker", "HIGH", "roadmap"), ("AWS", "HIGH", "roadmap"), ("Kubernetes", "MEDIUM", "roadmap")]


def test_recommendations_from_gap_engine_skip_strong_and_use_scores():
    ctx = SkillForgeContext.model_validate({"skill_gaps": [
        {"skill": "Python", "status": "STRONG", "priority_score": 0.99},
        {"skill": "Kubernetes", "status": "MISSING", "priority_level": "MEDIUM", "priority_score": 0.4},
        {"skill": "Docker", "status": "MISSING", "priority_level": "HIGH", "priority_score": 0.8},
    ]})
    assert [r.skill for r in derive_recommendations(ctx)] == ["Docker", "Kubernetes"]


def test_cited_ids_parsing():
    assert cited_ids("See [E1] and [E2, e3]. Also [link]") == {"E1", "E2", "E3", "LINK"}