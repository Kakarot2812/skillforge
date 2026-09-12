"""
Low-level async client for a local embedding model served by Ollama.

Structurally parallel to ``app.qwen_ai.qwen_client.QwenClient`` (same
transport-injection testability, same connect/total timeout split, same
"never raise raw httpx errors" philosophy) but talks to a different
endpoint (``/api/embed``) with batch support, and validates the returned
vector width against configuration rather than parsing a chat message.

Deliberately contains no SkillForge or RAG business logic (no chunking, no
persistence) so it stays a small, independently testable unit.
Ollama API reference: https://github.com/ollama/ollama/blob/main/docs/api.md
"""
import logging
from typing import Any, Dict, List, Optional, Sequence

import httpx

from app.rag.config import RagSettings
from app.rag.exceptions import (
    RagEmbeddingDimensionError,
    RagEmbeddingModelNotFoundError,
    RagEmbeddingResponseError,
    RagEmbeddingTimeoutError,
    RagEmbeddingUnavailableError,
)

logger = logging.getLogger(__name__)


def _normalise_tag(name: str) -> str:
    """Ollama treats an untagged model name as ':latest'."""
    return name if ":" in name else f"{name}:latest"


class RagEmbeddingClient:
    """Async HTTP client for a local Ollama embedding model."""

    def __init__(self, settings: RagSettings, transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self._settings = settings
        # ``transport`` is injectable so tests can use httpx.MockTransport.
        self._transport = transport

    @property
    def model(self) -> str:
        return self._settings.RAG_EMBEDDING_MODEL

    @property
    def dimensions(self) -> int:
        return self._settings.RAG_EMBEDDING_DIMENSIONS

    def _http(self, total_timeout: float) -> httpx.AsyncClient:
        timeout = httpx.Timeout(total_timeout, connect=self._settings.RAG_EMBEDDING_CONNECT_TIMEOUT)
        return httpx.AsyncClient(
            base_url=self._settings.RAG_OLLAMA_BASE_URL,
            timeout=timeout,
            transport=self._transport,
        )

    async def embed(self, texts: Sequence[str]) -> List[List[float]]:
        """Embed a batch of texts, preserving input order.

        Splits into batches of ``RAG_EMBEDDING_BATCH_SIZE`` and issues one
        Ollama request per batch (Ollama's ``/api/embed`` accepts a list
        ``input`` and returns embeddings in the same order).
        """
        if not texts:
            return []
        if any(not t or not t.strip() for t in texts):
            raise ValueError("All texts passed to embed() must be non-empty.")

        results: List[List[float]] = []
        batch_size = self._settings.RAG_EMBEDDING_BATCH_SIZE
        for start in range(0, len(texts), batch_size):
            batch = list(texts[start : start + batch_size])
            results.extend(await self._embed_batch(batch))
        return results

    async def embed_one(self, text: str) -> List[float]:
        """Convenience wrapper for embedding a single query string."""
        return (await self.embed([text]))[0]

    async def _embed_batch(self, batch: List[str]) -> List[List[float]]:
        payload: Dict[str, Any] = {"model": self._settings.RAG_EMBEDDING_MODEL, "input": batch}
        data = await self._request_json(
            "POST", "/api/embed", json=payload, timeout=self._settings.RAG_EMBEDDING_TIMEOUT
        )
        return self._parse_embed(data, expected_count=len(batch))

    async def check_health(self) -> bool:
        """True if Ollama is reachable and the configured embedding model is pulled.

        Uses /api/tags, which lists local models without loading one into
        memory. Never raises; returns False for any unreachable/misconfigured
        state so callers can treat RAG as best-effort.
        """
        try:
            data = await self._request_json(
                "GET", "/api/tags", timeout=self._settings.RAG_EMBEDDING_CONNECT_TIMEOUT * 2
            )
        except Exception as exc:  # noqa: BLE001 - health checks must never raise
            logger.info("RAG embedding health check failed: %s", exc)
            return False

        wanted = _normalise_tag(self._settings.RAG_EMBEDDING_MODEL)
        installed = set()
        for entry in data.get("models") or []:
            if isinstance(entry, dict):
                for key in ("name", "model"):
                    if isinstance(entry.get(key), str):
                        installed.add(_normalise_tag(entry[key]))
        return wanted in installed

    async def _request_json(self, method: str, path: str, *, timeout: float, json: Any = None) -> Dict[str, Any]:
        try:
            async with self._http(timeout) as http:
                response = await http.request(method, path, json=json)
        except httpx.ConnectTimeout as exc:
            raise RagEmbeddingUnavailableError(detail=f"Connect timeout to Ollama: {exc!r}") from exc
        except httpx.TimeoutException as exc:
            raise RagEmbeddingTimeoutError(detail=f"Ollama embedding request timed out: {exc!r}") from exc
        except httpx.TransportError as exc:
            raise RagEmbeddingUnavailableError(detail=f"Cannot reach Ollama: {exc!r}") from exc

        if response.status_code >= 400:
            self._raise_for_status(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise RagEmbeddingResponseError(detail="Ollama returned non-JSON body") from exc
        if not isinstance(data, dict):
            raise RagEmbeddingResponseError(detail=f"Ollama returned JSON of type {type(data).__name__}")
        return data

    def _raise_for_status(self, response: httpx.Response) -> None:
        error_text = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                error_text = str(body.get("error", ""))
        except ValueError:
            error_text = response.text[:200]
        detail = f"Ollama HTTP {response.status_code}: {error_text}"

        if response.status_code == 404 and "not found" in error_text.lower():
            raise RagEmbeddingModelNotFoundError(detail=detail)
        if response.status_code >= 500:
            raise RagEmbeddingUnavailableError(detail=detail)
        raise RagEmbeddingResponseError(detail=detail)

    def _parse_embed(self, data: Dict[str, Any], *, expected_count: int) -> List[List[float]]:
        if data.get("error"):
            raise RagEmbeddingResponseError(detail=f"Ollama error payload: {data.get('error')}")

        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings:
            raise RagEmbeddingResponseError(detail="Ollama response is missing 'embeddings'")
        if len(embeddings) != expected_count:
            raise RagEmbeddingResponseError(
                detail=f"Expected {expected_count} embeddings, got {len(embeddings)}"
            )

        expected_dim = self._settings.RAG_EMBEDDING_DIMENSIONS
        vectors: List[List[float]] = []
        for vec in embeddings:
            if not isinstance(vec, list) or not all(isinstance(x, (int, float)) for x in vec):
                raise RagEmbeddingResponseError(detail="Ollama returned a non-numeric embedding vector")
            if len(vec) != expected_dim:
                raise RagEmbeddingDimensionError(
                    detail=(
                        f"Embedding model '{self._settings.RAG_EMBEDDING_MODEL}' returned a "
                        f"{len(vec)}-dimensional vector but RAG_EMBEDDING_DIMENSIONS="
                        f"{expected_dim}. Update RAG_EMBEDDING_DIMENSIONS (and re-run the "
                        f"rag_chunks migration + full re-ingest) to match the real model output."
                    )
                )
            vectors.append([float(x) for x in vec])
        return vectors
