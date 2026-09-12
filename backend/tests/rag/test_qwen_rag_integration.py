"""
Integration between RAG and the existing Qwen chat endpoint: verifies RAG
evidence is merged into SkillForgeContext.evidence and Qwen's existing
citation behavior ([E1], sources[], grounded flag) is preserved unchanged.

Uses a lightweight fake RagService (retrieval mechanics themselves are
already covered by tests/rag/test_retriever.py, test_rag_service.py) so
this file focuses purely on the orchestration/merge logic in
app/api/v1/qwen_api.py.
"""
from typing import List, Optional
from uuid import UUID

import httpx
from fastapi.testclient import TestClient

from app.api.v1.qwen_api import get_qwen_service
from app.main import app
from app.qwen_ai.context import EvidenceItem
from app.qwen_ai.qwen_service import QwenService
from app.rag.service import get_rag_service
from tests.qwen_ai.helpers import make_client, make_settings, ollama_chat_payload

client = TestClient(app)
CHAT = "/api/v1/qwen/chat"


class FakeRagService:
    def __init__(self, evidence: List[EvidenceItem]):
        self._evidence = evidence
        self.calls = []

    async def retrieve_evidence(self, db, query, *, user_id: Optional[UUID] = None, source_types=None):
        self.calls.append({"query": query, "user_id": user_id, "source_types": source_types})
        return self._evidence


def use_ollama(handler):
    service = QwenService(make_client(handler), make_settings())
    app.dependency_overrides[get_qwen_service] = lambda: service


def use_rag(fake: FakeRagService):
    app.dependency_overrides[get_rag_service] = lambda: fake


def teardown_function(_):
    app.dependency_overrides.pop(get_qwen_service, None)
    app.dependency_overrides.pop(get_rag_service, None)


def test_rag_evidence_is_merged_into_context_and_cited():
    fake = FakeRagService([
        EvidenceItem(source="rag://doc1", title="Docker Basics", content="Docker packages apps into containers.",
                     evidence_type="manual"),
    ])
    use_rag(fake)

    def handler(request):
        return httpx.Response(200, json=ollama_chat_payload("Learn Docker first [E1]."))

    use_ollama(handler)
    response = client.post(CHAT, json={"message": "What should I learn next?"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["grounded"] is True
    assert body["data"]["sources"] == [{
        "id": "E1", "source": "rag://doc1", "title": "Docker Basics",
        "evidence_type": "manual", "cited": True,
    }]
    assert "evidence" in body["meta"]["context_sections"]
    assert fake.calls[0]["query"] == "What should I learn next?"


def test_rag_evidence_merges_alongside_caller_supplied_evidence_within_cap():
    fake = FakeRagService([EvidenceItem(source="rag://extra", title="Extra", content="Extra evidence.")])
    use_rag(fake)

    def handler(request):
        return httpx.Response(200, json=ollama_chat_payload("See [E1] and [E2]."))

    use_ollama(handler)
    caller_evidence = [{"source": "caller://one", "title": "Caller Evidence", "content": "Caller supplied fact."}]
    response = client.post(CHAT, json={
        "message": "Explain my gap",
        "context": {"target_role": "Backend Engineer", "evidence": caller_evidence},
    })

    assert response.status_code == 200
    sources = response.json()["data"]["sources"]
    assert [s["source"] for s in sources] == ["caller://one", "rag://extra"]
    assert [s["id"] for s in sources] == ["E1", "E2"]


def test_rag_evidence_respected_when_no_context_supplied_at_all():
    fake = FakeRagService([EvidenceItem(source="rag://only", title="Only Evidence", content="Some fact.")])
    use_rag(fake)

    def handler(request):
        return httpx.Response(200, json=ollama_chat_payload("Answer [E1]."))

    use_ollama(handler)
    response = client.post(CHAT, json={"message": "Tell me something"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["grounded"] is True
    assert body["data"]["sources"][0]["source"] == "rag://only"


def test_no_rag_evidence_leaves_ungrounded_chat_unchanged():
    use_rag(FakeRagService([]))

    def handler(request):
        return httpx.Response(200, json=ollama_chat_payload("General advice."))

    use_ollama(handler)
    response = client.post(CHAT, json={"message": "Tell me something"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["grounded"] is False
    assert body["data"]["sources"] == []


def test_x_user_id_header_is_forwarded_to_rag_retrieval():
    fake = FakeRagService([])
    use_rag(fake)
    use_ollama(lambda r: httpx.Response(200, json=ollama_chat_payload("ok")))

    user_id = "11111111-1111-1111-1111-111111111111"
    response = client.post(CHAT, json={"message": "hi"}, headers={"X-User-Id": user_id})

    assert response.status_code == 200
    assert str(fake.calls[0]["user_id"]) == user_id


def test_invalid_x_user_id_header_returns_422_before_calling_rag():
    fake = FakeRagService([])
    use_rag(fake)
    use_ollama(lambda r: httpx.Response(200, json=ollama_chat_payload("ok")))

    response = client.post(CHAT, json={"message": "hi"}, headers={"X-User-Id": "not-a-uuid"})

    assert response.status_code == 422
    assert fake.calls == []
