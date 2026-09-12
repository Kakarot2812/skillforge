import asyncio

import httpx
import pytest

from app.rag.exceptions import (
    RagEmbeddingDimensionError,
    RagEmbeddingModelNotFoundError,
    RagEmbeddingResponseError,
    RagEmbeddingTimeoutError,
    RagEmbeddingUnavailableError,
)
from tests.rag.helpers import fake_vector, make_embedding_client, ollama_embed_payload, request_json


def run(coro):
    return asyncio.run(coro)


def test_embed_sends_expected_payload_and_returns_vectors():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request_json(request)
        return httpx.Response(200, json=ollama_embed_payload([fake_vector(32), fake_vector(32, 0.2)]))

    client = make_embedding_client(handler)
    vectors = run(client.embed(["Python and SQL", "Docker containers"]))

    assert captured["url"] == "http://ollama.test:11434/api/embed"
    assert captured["body"]["model"] == "qwen3-embedding:8b"
    assert captured["body"]["input"] == ["Python and SQL", "Docker containers"]
    assert vectors == [fake_vector(32), fake_vector(32, 0.2)]


def test_embed_one_returns_single_vector():
    def handler(request):
        return httpx.Response(200, json=ollama_embed_payload([fake_vector(32)]))

    client = make_embedding_client(handler)
    vector = run(client.embed_one("Python"))
    assert vector == fake_vector(32)


def test_empty_input_returns_empty_list_without_a_request():
    def handler(request):
        raise AssertionError("should not be called for empty input")

    client = make_embedding_client(handler)
    assert run(client.embed([])) == []


def test_blank_text_is_rejected_before_any_request():
    def handler(request):
        raise AssertionError("should not be called for blank text")

    client = make_embedding_client(handler)
    with pytest.raises(ValueError):
        run(client.embed(["   "]))


def test_batches_requests_according_to_batch_size():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = request_json(request)
        calls.append(body["input"])
        return httpx.Response(200, json=ollama_embed_payload([fake_vector(32) for _ in body["input"]]))

    client = make_embedding_client(handler, RAG_EMBEDDING_BATCH_SIZE=2)
    texts = ["a", "b", "c", "d", "e"]
    vectors = run(client.embed(texts))

    assert len(calls) == 3  # 2 + 2 + 1
    assert sum(len(c) for c in calls) == 5
    assert len(vectors) == 5


def test_dimension_mismatch_raises_clear_error():
    def handler(request):
        return httpx.Response(200, json=ollama_embed_payload([fake_vector(4096)]))

    client = make_embedding_client(handler)  # configured for 32 dims
    with pytest.raises(RagEmbeddingDimensionError) as info:
        run(client.embed(["Python"]))
    assert "4096" in info.value.detail
    assert "RAG_EMBEDDING_DIMENSIONS" in info.value.detail


def test_mismatched_embedding_count_raises_response_error():
    def handler(request):
        return httpx.Response(200, json=ollama_embed_payload([fake_vector(32)]))  # only 1, expected 2

    client = make_embedding_client(handler)
    with pytest.raises(RagEmbeddingResponseError):
        run(client.embed(["a", "b"]))


def test_missing_embeddings_key_raises_response_error():
    def handler(request):
        return httpx.Response(200, json={"model": "qwen3-embedding:8b"})

    client = make_embedding_client(handler)
    with pytest.raises(RagEmbeddingResponseError):
        run(client.embed(["a"]))


def test_connect_timeout_maps_to_unavailable():
    def handler(request):
        raise httpx.ConnectTimeout("boom", request=request)

    client = make_embedding_client(handler)
    with pytest.raises(RagEmbeddingUnavailableError):
        run(client.embed(["a"]))


def test_read_timeout_maps_to_timeout_error():
    def handler(request):
        raise httpx.ReadTimeout("boom", request=request)

    client = make_embedding_client(handler)
    with pytest.raises(RagEmbeddingTimeoutError):
        run(client.embed(["a"]))


def test_model_not_found_maps_to_model_not_found_error():
    def handler(request):
        return httpx.Response(404, json={"error": "model 'qwen3-embedding:8b' not found"})

    client = make_embedding_client(handler)
    with pytest.raises(RagEmbeddingModelNotFoundError):
        run(client.embed(["a"]))


def test_server_error_maps_to_unavailable():
    def handler(request):
        return httpx.Response(500, json={"error": "model failed to load"})

    client = make_embedding_client(handler)
    with pytest.raises(RagEmbeddingUnavailableError):
        run(client.embed(["a"]))


def test_check_health_true_when_model_installed():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "qwen3-embedding:8b"}]})

    client = make_embedding_client(handler)
    assert run(client.check_health()) is True


def test_check_health_false_when_model_missing():
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": "llama3:8b"}]})

    client = make_embedding_client(handler)
    assert run(client.check_health()) is False


def test_check_health_false_when_unreachable():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    client = make_embedding_client(handler)
    assert run(client.check_health()) is False
