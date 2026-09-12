import asyncio
import uuid

import httpx
import pytest

from app.db.database import SessionLocal
from app.db.models import RAG_EMBEDDING_DIMENSIONS
from app.rag import repository
from app.rag.config import RagSettings
from app.rag.exceptions import RagDisabledError
from app.rag.schemas import NormalizedDocument
from app.rag.service import RagService, get_rag_service
from tests.rag.helpers import make_rag_settings, ollama_embed_payload

DIM = RAG_EMBEDDING_DIMENSIONS


def run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _settings(**overrides):
    return make_rag_settings(RAG_EMBEDDING_DIMENSIONS=DIM, RAG_CHUNK_SIZE=500, RAG_CHUNK_OVERLAP=50, **overrides)


def _vector(dim=DIM):
    return [0.02] * dim


def _service_with_handler(handler, **settings_overrides) -> RagService:
    settings = _settings(**settings_overrides)
    svc = RagService(settings)
    # Swap in a mocked transport for the embedding client + retriever/ingestor built on it.
    from app.rag.embeddings import RagEmbeddingClient
    from app.rag.ingestion import Ingestor
    from app.rag.retriever import Retriever

    svc._embedding_client = RagEmbeddingClient(settings, transport=httpx.MockTransport(handler))
    svc._retriever = Retriever(svc._embedding_client)
    svc._ingestor = Ingestor(svc._embedding_client, chunk_size=settings.RAG_CHUNK_SIZE, chunk_overlap=settings.RAG_CHUNK_OVERLAP)
    return svc


def _ok_embed_handler(request: httpx.Request) -> httpx.Response:
    import json
    body = json.loads(request.content.decode())
    return httpx.Response(200, json=ollama_embed_payload([_vector() for _ in body["input"]]))


def test_retrieve_evidence_returns_evidence_items(db):
    svc = _service_with_handler(_ok_embed_handler)
    doc = NormalizedDocument(
        source_type="manual", source_id=str(uuid.uuid4()), title="Docker Guide",
        text="Docker packages applications into portable containers.",
    )
    result = run(svc.ingest_document(db, doc))
    try:
        items = run(svc.retrieve_evidence(db, "How does Docker work?"))
        assert any("Docker" in item.content for item in items)
        assert all(item.evidence_type == "manual" for item in items if item.title == "Docker Guide")
    finally:
        repository.delete_document(db, result.document_id)
        db.commit()


def test_retrieve_evidence_disabled_returns_empty_list_not_error(db):
    svc = _service_with_handler(_ok_embed_handler, RAG_ENABLED=False)
    items = run(svc.retrieve_evidence(db, "anything"))
    assert items == []


def test_retrieve_evidence_or_raise_raises_when_disabled(db):
    svc = _service_with_handler(_ok_embed_handler, RAG_ENABLED=False)
    with pytest.raises(RagDisabledError):
        run(svc.retrieve_evidence_or_raise(db, "anything"))


def test_retrieve_evidence_fails_open_when_embedding_unavailable(db):
    def failing_handler(request):
        return httpx.Response(500, json={"error": "model failed to load"})

    svc = _service_with_handler(failing_handler)
    items = run(svc.retrieve_evidence(db, "anything"))
    assert items == []  # never raises to the caller


def test_ingest_source_unknown_type_raises_value_error(db):
    svc = _service_with_handler(_ok_embed_handler)
    with pytest.raises(ValueError):
        run(svc.ingest_source(db, "not_a_real_source"))


def test_delete_document_and_delete_by_source(db):
    svc = _service_with_handler(_ok_embed_handler)
    doc = NormalizedDocument(source_type="manual", source_id="svc-delete-test", title="X", text="Some content here.")
    result = run(svc.ingest_document(db, doc))

    assert svc.delete_by_source(db, "manual", "svc-delete-test") is True
    assert svc.delete_by_source(db, "manual", "svc-delete-test") is False


def test_get_rag_service_falls_back_to_disabled_on_bad_config(monkeypatch):
    from app.rag.config import get_rag_settings

    get_rag_service.cache_clear()
    get_rag_settings.cache_clear()
    monkeypatch.setenv("RAG_TOP_K", "0")  # invalid: must be >= 1
    monkeypatch.setattr(
        RagSettings, "model_config", {**RagSettings.model_config, "env_file": None}
    )
    try:
        svc = get_rag_service()
        assert svc.enabled is False
    finally:
        get_rag_service.cache_clear()
        get_rag_settings.cache_clear()
