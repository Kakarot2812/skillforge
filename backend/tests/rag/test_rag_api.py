import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.db.models import RAG_EMBEDDING_DIMENSIONS
from app.main import app
from app.rag.embeddings import RagEmbeddingClient
from app.rag.ingestion import Ingestor
from app.rag.retriever import Retriever
from app.rag.service import RagService, get_rag_service
from tests.rag.helpers import make_rag_settings, ollama_embed_payload

client = TestClient(app)
INGEST = "/api/v1/rag/ingest"
REINDEX = "/api/v1/rag/reindex"
HEALTH = "/api/v1/rag/health"

DIM = RAG_EMBEDDING_DIMENSIONS


def _vector(dim=DIM):
    return [0.03] * dim


def _ok_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode())
    return httpx.Response(200, json=ollama_embed_payload([_vector() for _ in body["input"]]))


def use_rag(handler, **settings_overrides):
    """Wire a RagService with a mocked embedding transport into the app."""
    settings = make_rag_settings(RAG_EMBEDDING_DIMENSIONS=DIM, **settings_overrides)
    service = RagService(settings)
    service._embedding_client = RagEmbeddingClient(settings, transport=httpx.MockTransport(handler))
    service._retriever = Retriever(service._embedding_client)
    service._ingestor = Ingestor(
        service._embedding_client, chunk_size=settings.RAG_CHUNK_SIZE, chunk_overlap=settings.RAG_CHUNK_OVERLAP
    )
    app.dependency_overrides[get_rag_service] = lambda: service
    return service


@pytest.fixture(autouse=True)
def reset_overrides():
    yield
    app.dependency_overrides.pop(get_rag_service, None)


def test_ingest_manual_document_creates_document_and_delete_removes_it():
    use_rag(_ok_handler)
    slug = f"manual-{uuid.uuid4()}"
    response = client.post(INGEST, json={
        "source_type": "manual", "source_id": slug, "title": "Docker 101",
        "text": "Docker packages applications into portable containers.",
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["source_type"] == "manual"
    assert data[0]["chunks_created"] >= 1
    assert data[0]["changed"] is True

    document_id = data[0]["document_id"]
    delete_resp = client.delete(f"/api/v1/rag/documents/{document_id}")
    assert delete_resp.status_code == 204

    delete_again = client.delete(f"/api/v1/rag/documents/{document_id}")
    assert delete_again.status_code == 404


def test_ingest_manual_reingest_is_idempotent():
    use_rag(_ok_handler)
    slug = f"manual-{uuid.uuid4()}"
    payload = {
        "source_type": "manual", "source_id": slug, "title": "Docker 101",
        "text": "Docker packages applications into portable containers.",
    }
    first = client.post(INGEST, json=payload).json()["data"][0]
    second = client.post(INGEST, json=payload).json()["data"][0]
    try:
        assert first["changed"] is True
        assert second["changed"] is False
        assert second["document_id"] == first["document_id"]
        assert second["version"] == 1
    finally:
        client.delete(f"/api/v1/rag/documents/{first['document_id']}")


@pytest.mark.parametrize("payload", [
    {"source_type": "manual", "source_id": "x"},  # missing title/text
    {"source_type": "manual", "title": "T", "text": "content"},  # missing source_id
    {"source_type": "not_a_real_source"},
    {"source_type": "manual", "source_id": "x", "title": "T", "text": "content", "unexpected": True},
])
def test_ingest_validation_errors(payload):
    use_rag(lambda r: pytest.fail("Ollama must not be called for invalid input"))
    response = client.post(INGEST, json=payload)
    assert response.status_code == 422


def test_reindex_rejects_manual_source_type():
    use_rag(lambda r: pytest.fail("Ollama must not be called"))
    response = client.post(REINDEX, json={"source_type": "manual"})
    assert response.status_code == 422


def test_reindex_unknown_source_type():
    use_rag(lambda r: pytest.fail("Ollama must not be called"))
    response = client.post(REINDEX, json={"source_type": "not_a_real_source"})
    assert response.status_code == 422


def test_delete_nonexistent_document_returns_404():
    use_rag(_ok_handler)
    response = client.delete(f"/api/v1/rag/documents/{uuid.uuid4()}")
    assert response.status_code == 404


def test_ingest_error_mapping_hides_internal_details():
    def failing_handler(request):
        raise httpx.ConnectError("boom at /internal/path", request=request)

    use_rag(failing_handler)
    response = client.post(INGEST, json={
        "source_type": "manual", "source_id": f"manual-{uuid.uuid4()}", "title": "T", "text": "some content",
    })
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "RAG_SERVICE_UNAVAILABLE"
    assert "boom" not in response.text and "/internal/path" not in response.text


def test_health_ok():
    use_rag(lambda r: httpx.Response(200, json={"models": [{"name": "qwen3-embedding:8b"}]}))
    response = client.get(HEALTH)
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok", "embedding_model_available": True}}


def test_health_unavailable():
    def unreachable_handler(request):
        raise httpx.ConnectError("refused", request=request)

    use_rag(unreachable_handler)
    response = client.get(HEALTH)
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "unavailable"


def test_health_disabled():
    use_rag(_ok_handler, RAG_ENABLED=False)
    response = client.get(HEALTH)
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "disabled", "embedding_model_available": False}}


def test_existing_qwen_routes_still_work_with_rag_mounted():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
