"""
Embedding provider interface and local/mock implementations for SkillForge AI.
Post-MVP Phase 2, Checkpoint P3.

Core architectural boundaries:
- "The LLM never decides what is true."
- Pure vector representation: zero business logic, zero skill classification.
- Embeddings are generated locally with sentence-transformers/all-MiniLM-L6-v2 (384-dim).
- Zero cloud/external API calls.
- Enforces strict dimension consistency between provider, configuration, and database.
- Controllable MockEmbeddingProvider for deterministic retrieval ranking tests.
"""

from abc import ABC, abstractmethod
import logging
import math
from typing import Dict, List, Optional

from app.config import settings
from app.rag.exceptions import RAGDimensionMismatchError, RAGEmbeddingError

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """
    Abstract interface for embedding generation.
    Decouples retrieval and storage from specific embedding library implementations.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Authoritative vector dimension produced by this provider."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generates an embedding vector for a single query or text snippet."""
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a batch of text documents."""
        pass

    def validate_dimension_consistency(self, expected_dim: Optional[int] = None) -> None:
        """
        Validates that the provider dimension agrees with the authoritative configuration.
        Raises RAGDimensionMismatchError if they differ.
        """
        target = expected_dim if expected_dim is not None else settings.EMBEDDING_DIMENSION
        if self.dimension != target:
            raise RAGDimensionMismatchError(
                expected=target,
                actual=self.dimension,
                model_name=getattr(self, "model_name", self.__class__.__name__),
            )


class LocalSentenceTransformerProvider(EmbeddingProvider):
    """
    Local sentence-transformers embedding provider.
    Runs locally on CPU / Apple Silicon MPS with all-MiniLM-L6-v2 (384 dimensions).
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        expected_dim: Optional[int] = None,
    ):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._expected_dim = expected_dim if expected_dim is not None else settings.EMBEDDING_DIMENSION

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        except Exception as exc:
            raise RAGEmbeddingError(
                f"Failed to load local embedding model '{self.model_name}': {str(exc)}"
            ) from exc

        # Determine and validate actual model dimension
        if hasattr(self._model, "get_embedding_dimension"):
            actual_dim = self._model.get_embedding_dimension()
        else:
            actual_dim = self._model.get_sentence_embedding_dimension()
        if actual_dim is None:
            raise RAGEmbeddingError(f"Could not determine embedding dimension for '{self.model_name}'.")

        self._dimension = int(actual_dim)
        self.validate_dimension_consistency(self._expected_dim)

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise RAGEmbeddingError("Cannot generate embedding for empty text.")
        try:
            vec = self._model.encode(
                text.strip(),
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [float(x) for x in vec]
        except Exception as exc:
            raise RAGEmbeddingError(f"Embedding inference error for text: {str(exc)}") from exc

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        for idx, t in enumerate(texts):
            if not t or not t.strip():
                raise RAGEmbeddingError(f"Cannot embed document list with empty text at index {idx}.")

        try:
            cleaned = [t.strip() for t in texts]
            embeddings = self._model.encode(
                cleaned,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [[float(x) for x in vec] for vec in embeddings]
        except Exception as exc:
            raise RAGEmbeddingError(f"Batch embedding inference error: {str(exc)}") from exc


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Controllable deterministic mock embedding provider for tests.
    Does NOT use random hashing to fake semantic similarity; provides explicit
    predictable vector mappings so unit tests can prove deterministic ranking,
    tie-breaking, metadata filtering, and dimension checking offline.
    """

    def __init__(
        self,
        dimension: int = settings.EMBEDDING_DIMENSION,
        explicit_mappings: Optional[Dict[str, List[float]]] = None,
    ):
        self._dimension = dimension
        self._mappings: Dict[str, List[float]] = {}
        if explicit_mappings:
            for k, v in explicit_mappings.items():
                self.register_mapping(k, v)

    @property
    def dimension(self) -> int:
        return self._dimension

    def register_mapping(self, text_key: str, vector: List[float]) -> None:
        """Registers a deterministic vector for a specific phrase or text snippet."""
        if len(vector) != self._dimension:
            # Pad or truncate or raise
            if len(vector) > self._dimension:
                vector = vector[: self._dimension]
            else:
                vector = vector + [0.0] * (self._dimension - len(vector))
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        self._mappings[text_key.strip().lower()] = vector

    def _generate_default_vector(self, text: str) -> List[float]:
        """Produces a deterministic pseudo-vector derived from characters for unmapped text."""
        vec = [0.0] * self._dimension
        for i, char in enumerate(text):
            idx = (ord(char) * 17 + i * 31) % self._dimension
            vec[idx] += 1.0
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0
        return vec

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise RAGEmbeddingError("Cannot generate mock embedding for empty text.")
        clean = text.strip().lower()
        if clean in self._mappings:
            return list(self._mappings[clean])
        # Check partial/substring matches in explicit mappings
        for key, vec in self._mappings.items():
            if key in clean or clean in key:
                return list(vec)
        return self._generate_default_vector(clean)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]
