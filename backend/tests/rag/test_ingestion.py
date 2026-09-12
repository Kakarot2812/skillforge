"""
Ingestion pipeline tests: real Postgres + a mocked embedding transport.
Covers idempotent re-ingestion, changed-content re-ingestion, and empty
content handling.
"""
import asyncio
import uuid

import httpx
import pytest

from app.db.database import SessionLocal
from app.db.models import RAG_EMBEDDING_DIMENSIONS, RagChunk
from app.rag import repository
from app.rag.exceptions import RagDocumentError
from app.rag.ingestion import Ingestor
from app.rag.schemas import NormalizedDocument
from tests.rag.helpers import make_embedding_client, ollama_embed_payload

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


def _vector(dim=DIM):
    return [0.01] * dim


def _client_counting(calls: list):
    def handler(request: httpx.Request) -> httpx.Response:
        import json
        body = json.loads(request.content.decode())
        calls.append(body["input"])
        return httpx.Response(200, json=ollama_embed_payload([_vector() for _ in body["input"]]))

    return make_embedding_client(handler, RAG_EMBEDDING_DIMENSIONS=DIM)


def _doc(text, **overrides) -> NormalizedDocument:
    values = dict(source_type="manual", source_id=str(uuid.uuid4()), title="Doc", text=text)
    values.update(overrides)
    return NormalizedDocument(**values)


def test_ingest_new_document_creates_chunks(db):
    calls = []
    client = _client_counting(calls)
    ingestor = Ingestor(client, chunk_size=200, chunk_overlap=20)

    doc = _doc("Docker packages applications into portable containers for deployment.")
    try:
        result = run(ingestor.ingest_document(db, doc))
        assert result.changed is True
        assert result.chunks_created >= 1
        assert result.version == 1
        assert len(calls) == 1  # one embedding batch call
    finally:
        repository.delete_document(db, result.document_id)
        db.commit()


def test_reingesting_identical_content_is_a_noop(db):
    calls = []
    client = _client_counting(calls)
    ingestor = Ingestor(client, chunk_size=200, chunk_overlap=20)

    doc = _doc("Kubernetes orchestrates containers across a cluster of machines.", source_id="stable-id-1")
    try:
        first = run(ingestor.ingest_document(db, doc))
        assert first.changed is True
        calls_after_first = len(calls)

        second = run(ingestor.ingest_document(db, doc))
        assert second.changed is False
        assert second.document_id == first.document_id
        assert second.version == 1
        assert second.chunks_reused == first.chunks_created
        # No new embedding calls were made for the unchanged re-ingest.
        assert len(calls) == calls_after_first
    finally:
        repository.delete_document(db, first.document_id)
        db.commit()


def test_reingesting_changed_content_bumps_version_and_replaces_chunks(db):
    calls = []
    client = _client_counting(calls)
    ingestor = Ingestor(client, chunk_size=200, chunk_overlap=20)

    doc_v1 = _doc("Original content about Python.", source_id="stable-id-2")
    try:
        first = run(ingestor.ingest_document(db, doc_v1))
        assert first.version == 1

        doc_v2 = _doc("Updated content about Go instead of Python.", source_id="stable-id-2")
        second = run(ingestor.ingest_document(db, doc_v2))
        assert second.changed is True
        assert second.document_id == first.document_id
        assert second.version == 2

        rows = db.query(RagChunk).filter(RagChunk.document_id == first.document_id).all()
        assert all("Go instead" in r.content or "Updated" in r.content for r in rows)
    finally:
        repository.delete_document(db, first.document_id)
        db.commit()


def test_empty_content_raises_document_error(db):
    client = _client_counting([])
    ingestor = Ingestor(client, chunk_size=200, chunk_overlap=20)
    doc = _doc("   ")
    with pytest.raises(RagDocumentError):
        run(ingestor.ingest_document(db, doc))


def test_failed_embedding_rolls_back_without_creating_orphan_document(db):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "model failed to load"})

    client = make_embedding_client(handler, RAG_EMBEDDING_DIMENSIONS=DIM)
    ingestor = Ingestor(client, chunk_size=200, chunk_overlap=20)

    doc = _doc("Some content that will fail to embed.", source_id="rollback-test-id")
    with pytest.raises(Exception):
        run(ingestor.ingest_document(db, doc))

    db.rollback()
    assert repository.get_document_by_source(db, "manual", "rollback-test-id") is None
