"""
Repository tests against a real local Postgres (matches tests/test_db.py's
convention: no mocking of the database layer). Requires the project's
docker-compose Postgres to be running.
"""
import uuid

import pytest

from app.db.database import SessionLocal
from app.db.models import RAG_EMBEDDING_DIMENSIONS, RagChunk, RagDocument, User
from app.rag import repository
from app.rag.chunking import Chunk
from app.rag.schemas import NormalizedDocument, RetrievalFilters

DIM = RAG_EMBEDDING_DIMENSIONS


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


@pytest.fixture()
def user(db):
    record = User(email=f"rag-test-{uuid.uuid4()}@example.com", full_name="RAG Tester")
    db.add(record)
    db.commit()
    db.refresh(record)
    yield record
    db.delete(record)
    db.commit()


def _doc(source_type="manual", source_id=None, user_id=None, title="Doc", text="ignored") -> NormalizedDocument:
    return NormalizedDocument(
        source_type=source_type,
        source_id=source_id or str(uuid.uuid4()),
        title=title,
        text=text,
        user_id=user_id,
    )


def test_upsert_document_creates_new_document_as_changed(db):
    doc = _doc()
    record, changed = repository.upsert_document(db, doc, content_hash="hash-a")
    db.commit()
    try:
        assert changed is True
        assert record.version == 1
        assert record.content_hash == "hash-a"
    finally:
        repository.delete_document(db, record.id)
        db.commit()


def test_upsert_document_same_hash_is_idempotent_noop(db):
    doc = _doc()
    record, _ = repository.upsert_document(db, doc, content_hash="hash-a")
    db.commit()
    try:
        record2, changed = repository.upsert_document(db, doc, content_hash="hash-a")
        db.commit()
        assert changed is False
        assert record2.id == record.id
        assert record2.version == 1
    finally:
        repository.delete_document(db, record.id)
        db.commit()


def test_upsert_document_changed_hash_bumps_version(db):
    doc = _doc()
    record, _ = repository.upsert_document(db, doc, content_hash="hash-a")
    db.commit()
    try:
        record2, changed = repository.upsert_document(db, doc, content_hash="hash-b")
        db.commit()
        assert changed is True
        assert record2.id == record.id
        assert record2.version == 2
        assert record2.content_hash == "hash-b"
    finally:
        repository.delete_document(db, record.id)
        db.commit()


def test_replace_chunks_creates_expected_rows(db):
    doc = _doc()
    record, _ = repository.upsert_document(db, doc, content_hash="hash-a")
    db.commit()
    try:
        chunks = [
            Chunk(index=0, content="Python is great", content_hash="c0"),
            Chunk(index=1, content="SQL is also great", content_hash="c1"),
        ]
        embeddings = [_vector(0), _vector(1)]
        created = repository.replace_chunks(db, record.id, chunks, embeddings)
        db.commit()
        assert created == 2
        rows = db.query(RagChunk).filter(RagChunk.document_id == record.id).order_by(RagChunk.chunk_index).all()
        assert [r.content for r in rows] == ["Python is great", "SQL is also great"]
    finally:
        repository.delete_document(db, record.id)
        db.commit()


def test_replace_chunks_removes_stale_chunks(db):
    doc = _doc()
    record, _ = repository.upsert_document(db, doc, content_hash="hash-a")
    db.commit()
    try:
        repository.replace_chunks(
            db, record.id,
            [Chunk(index=0, content="old chunk one", content_hash="c0"),
             Chunk(index=1, content="old chunk two", content_hash="c1")],
            [_vector(0), _vector(1)],
        )
        db.commit()
        repository.replace_chunks(
            db, record.id,
            [Chunk(index=0, content="new chunk only", content_hash="c2")],
            [_vector(2)],
        )
        db.commit()
        rows = db.query(RagChunk).filter(RagChunk.document_id == record.id).all()
        assert len(rows) == 1
        assert rows[0].content == "new chunk only"
    finally:
        repository.delete_document(db, record.id)
        db.commit()


def test_delete_document_cascades_chunks(db):
    doc = _doc()
    record, _ = repository.upsert_document(db, doc, content_hash="hash-a")
    db.commit()
    repository.replace_chunks(db, record.id, [Chunk(index=0, content="x", content_hash="c0")], [_vector(0)])
    db.commit()

    deleted = repository.delete_document(db, record.id)
    db.commit()
    assert deleted is True
    assert db.query(RagDocument).filter(RagDocument.id == record.id).first() is None
    assert db.query(RagChunk).filter(RagChunk.document_id == record.id).count() == 0


def test_delete_by_source(db):
    doc = _doc(source_type="manual", source_id="unique-slug-1")
    record, _ = repository.upsert_document(db, doc, content_hash="hash-a")
    db.commit()
    assert repository.delete_by_source(db, "manual", "unique-slug-1") is True
    assert repository.delete_by_source(db, "manual", "unique-slug-1") is False


def test_vector_search_orders_by_similarity(db):
    doc = _doc()
    record, _ = repository.upsert_document(db, doc, content_hash="hash-a")
    db.commit()
    try:
        repository.replace_chunks(
            db, record.id,
            [
                Chunk(index=0, content="near match", content_hash="c0"),
                Chunk(index=1, content="far match", content_hash="c1"),
            ],
            [_vector(0), _vector(1)],
        )
        db.commit()

        results = repository.vector_search(db, _vector(0), RetrievalFilters(), limit=10)
        contents = [r.content for r in results if r.document_id == record.id]
        assert contents[0] == "near match"
    finally:
        repository.delete_document(db, record.id)
        db.commit()


def test_fts_search_matches_keyword(db):
    doc = _doc()
    record, _ = repository.upsert_document(db, doc, content_hash="hash-a")
    db.commit()
    try:
        repository.replace_chunks(
            db, record.id,
            [
                Chunk(index=0, content="Kubernetes orchestrates containers across a cluster.", content_hash="c0"),
                Chunk(index=1, content="Bananas are a good source of potassium.", content_hash="c1"),
            ],
            [_vector(0), _vector(1)],
        )
        db.commit()

        results = repository.fts_search(db, "Kubernetes", RetrievalFilters(), limit=10)
        matching = [r for r in results if r.document_id == record.id]
        assert matching
        assert "Kubernetes" in matching[0].content
    finally:
        repository.delete_document(db, record.id)
        db.commit()


def test_isolation_user_sees_own_and_global_but_not_other_users(db, user):
    other = User(email=f"rag-other-{uuid.uuid4()}@example.com")
    db.add(other)
    db.commit()
    db.refresh(other)

    own_doc, _ = repository.upsert_document(db, _doc(user_id=user.id, title="Mine"), content_hash="h1")
    other_doc, _ = repository.upsert_document(db, _doc(user_id=other.id, title="TheirsPrivate"), content_hash="h2")
    global_doc, _ = repository.upsert_document(db, _doc(user_id=None, title="Shared"), content_hash="h3")
    db.commit()

    try:
        repository.replace_chunks(db, own_doc.id, [Chunk(0, "mine content", "c1")], [_vector(0)])
        repository.replace_chunks(db, other_doc.id, [Chunk(0, "their private content", "c2")], [_vector(0)])
        repository.replace_chunks(db, global_doc.id, [Chunk(0, "shared content", "c3")], [_vector(0)])
        db.commit()

        results = repository.vector_search(db, _vector(0), RetrievalFilters(user_id=user.id), limit=50)
        titles = {r.title for r in results}
        assert "Mine" in titles
        assert "Shared" in titles
        assert "TheirsPrivate" not in titles
    finally:
        repository.delete_document(db, own_doc.id)
        repository.delete_document(db, other_doc.id)
        repository.delete_document(db, global_doc.id)
        db.delete(other)
        db.commit()


def test_isolation_anonymous_caller_only_sees_global_documents(db, user):
    private_doc, _ = repository.upsert_document(db, _doc(user_id=user.id, title="Private"), content_hash="h1")
    global_doc, _ = repository.upsert_document(db, _doc(user_id=None, title="Public"), content_hash="h2")
    db.commit()
    try:
        repository.replace_chunks(db, private_doc.id, [Chunk(0, "private content", "c1")], [_vector(0)])
        repository.replace_chunks(db, global_doc.id, [Chunk(0, "public content", "c2")], [_vector(0)])
        db.commit()

        results = repository.vector_search(db, _vector(0), RetrievalFilters(user_id=None), limit=50)
        titles = {r.title for r in results}
        assert "Public" in titles
        assert "Private" not in titles
    finally:
        repository.delete_document(db, private_doc.id)
        repository.delete_document(db, global_doc.id)
        db.commit()


def test_source_type_filter(db):
    a, _ = repository.upsert_document(db, _doc(source_type="resume", title="Resume Doc"), content_hash="h1")
    b, _ = repository.upsert_document(db, _doc(source_type="manual", title="Manual Doc"), content_hash="h2")
    db.commit()
    try:
        repository.replace_chunks(db, a.id, [Chunk(0, "resume content", "c1")], [_vector(0)])
        repository.replace_chunks(db, b.id, [Chunk(0, "manual content", "c2")], [_vector(0)])
        db.commit()

        results = repository.vector_search(
            db, _vector(0), RetrievalFilters(source_types=["resume"]), limit=50
        )
        titles = {r.title for r in results}
        assert "Resume Doc" in titles
        assert "Manual Doc" not in titles
    finally:
        repository.delete_document(db, a.id)
        repository.delete_document(db, b.id)
        db.commit()
