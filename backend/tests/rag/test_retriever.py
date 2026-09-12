"""
Retriever tests: real Postgres (repository layer) + a mocked embedding
transport (no live Ollama needed), verifying the full
embed -> vector search + FTS search -> RRF fusion -> top_k orchestration.
"""
import asyncio
import uuid

import httpx
import pytest

from app.db.database import SessionLocal
from app.db.models import RAG_EMBEDDING_DIMENSIONS
from app.rag import repository
from app.rag.chunking import Chunk
from app.rag.retriever import Retriever
from app.rag.schemas import NormalizedDocument, RetrievalFilters
from tests.rag.helpers import make_embedding_client, ollama_embed_payload

DIM = RAG_EMBEDDING_DIMENSIONS


def run(coro):
    return asyncio.run(coro)


def _vector(*hot_indices, dim: int = DIM) -> list:
    vec = [0.0] * dim
    for i in hot_indices:
        vec[i] = 1.0
    return vec


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _doc(**overrides) -> NormalizedDocument:
    values = dict(source_type="manual", source_id=str(uuid.uuid4()), title="Doc", text="ignored")
    values.update(overrides)
    return NormalizedDocument(**values)


def _client_returning(vector):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=ollama_embed_payload([vector]))

    return make_embedding_client(handler, RAG_EMBEDDING_DIMENSIONS=DIM)


def test_retrieve_returns_fused_top_k(db):
    doc, _ = repository.upsert_document(db, _doc(title="Kubernetes Guide"), content_hash="h1")
    db.commit()
    try:
        repository.replace_chunks(
            db, doc.id,
            [
                Chunk(0, "Kubernetes orchestrates containers across a cluster.", "c0"),
                Chunk(1, "Bananas are a good source of potassium.", "c1"),
            ],
            [_vector(0), _vector(1)],
        )
        db.commit()

        client = _client_returning(_vector(0))
        retriever = Retriever(client)
        results = run(
            retriever.retrieve(
                db, "How does Kubernetes orchestrate containers?",
                filters=RetrievalFilters(), top_k=5, candidate_k=20, rrf_k=60,
            )
        )

        matching = [r for r in results if r.document_id == doc.id]
        assert matching
        assert matching[0].content.startswith("Kubernetes")
        assert matching[0].fused_score > 0
    finally:
        repository.delete_document(db, doc.id)
        db.commit()


def test_retrieve_respects_top_k(db):
    doc, _ = repository.upsert_document(db, _doc(title="Many Chunks"), content_hash="h1")
    db.commit()
    try:
        chunks = [Chunk(i, f"Chunk number {i} about Kubernetes networking.", f"c{i}") for i in range(10)]
        embeddings = [_vector(0) for _ in chunks]
        repository.replace_chunks(db, doc.id, chunks, embeddings)
        db.commit()

        client = _client_returning(_vector(0))
        retriever = Retriever(client)
        results = run(
            retriever.retrieve(
                db, "Kubernetes networking", filters=RetrievalFilters(), top_k=3, candidate_k=20, rrf_k=60,
            )
        )
        assert len(results) <= 3
    finally:
        repository.delete_document(db, doc.id)
        db.commit()


def test_retrieve_applies_user_isolation(db):
    from app.db.models import User

    user = User(email=f"retriever-{uuid.uuid4()}@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)

    private_doc, _ = repository.upsert_document(db, _doc(user_id=user.id, title="Private"), content_hash="h1")
    global_doc, _ = repository.upsert_document(db, _doc(user_id=None, title="Public"), content_hash="h2")
    db.commit()
    try:
        repository.replace_chunks(db, private_doc.id, [Chunk(0, "Private Kubernetes notes.", "c1")], [_vector(0)])
        repository.replace_chunks(db, global_doc.id, [Chunk(0, "Public Kubernetes notes.", "c2")], [_vector(0)])
        db.commit()

        client = _client_returning(_vector(0))
        retriever = Retriever(client)
        results = run(
            retriever.retrieve(
                db, "Kubernetes notes", filters=RetrievalFilters(user_id=None), top_k=10, candidate_k=20, rrf_k=60,
            )
        )
        titles = {r.title for r in results}
        assert "Public" in titles
        assert "Private" not in titles
    finally:
        repository.delete_document(db, private_doc.id)
        repository.delete_document(db, global_doc.id)
        db.delete(user)
        db.commit()
