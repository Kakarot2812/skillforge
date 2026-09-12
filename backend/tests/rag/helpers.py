"""Shared helpers for RAG embedding tests (mock Ollama responses, isolated settings)."""
import json
from typing import Callable

import httpx

from app.rag.config import RagSettings
from app.rag.embeddings import RagEmbeddingClient


def make_rag_settings(**overrides) -> RagSettings:
    """Settings isolated from any developer .env file."""
    values = {
        "RAG_OLLAMA_BASE_URL": "http://ollama.test:11434",
        "RAG_EMBEDDING_MODEL": "qwen3-embedding:8b",
        "RAG_EMBEDDING_DIMENSIONS": 32,
        "RAG_EMBEDDING_BATCH_SIZE": 4,
    }
    values.update(overrides)
    return RagSettings(_env_file=None, **values)


def ollama_embed_payload(vectors: list, **extra) -> dict:
    body = {"model": "qwen3-embedding:8b", "embeddings": vectors}
    body.update(extra)
    return body


def make_embedding_client(handler: Callable[[httpx.Request], httpx.Response], **overrides) -> RagEmbeddingClient:
    return RagEmbeddingClient(make_rag_settings(**overrides), transport=httpx.MockTransport(handler))


def request_json(request: httpx.Request) -> dict:
    return json.loads(request.content.decode())


def fake_vector(dim: int, seed: float = 0.1) -> list:
    return [round(seed * (i + 1), 4) for i in range(dim)]
