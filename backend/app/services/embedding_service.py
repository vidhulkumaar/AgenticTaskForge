"""
Embedding service for generating document and query embeddings via Ollama.

Uses the nomic-embed-text model through Ollama's /api/embeddings endpoint.
Applies search_document: and search_query: prefixes per the nomic specification.
"""
import logging
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingError(Exception):
    """Raised when embedding generation fails for a recoverable reason (bad input, etc.)."""
    pass


class EmbeddingUnavailableError(EmbeddingError):
    """Raised when the embedding infrastructure is unreachable (Ollama down, model missing, timeout).

    Mapped to HTTP 503 by the global exception handler.
    """
    pass


class OllamaEmbeddingService:
    """
    Generates embeddings using Ollama's nomic-embed-text model.

    Applies the required prefixes:
        - Documents: "search_document: <text>"
        - Queries:   "search_query: <text>"

    Validates that returned vectors are non-empty, finite, and the expected dimension.
    """

    def __init__(self, ollama_base_url: str, model: str = "nomic-embed-text",
                 dimension: int = 768, timeout: int = 60):
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.model = model
        self.expected_dimension = dimension
        self.timeout = timeout

    def _validate_vector(self, vec: List[float], index: int = 0) -> List[float]:
        """Validate that a vector is non-empty, the correct dimension, and contains finite values."""
        if not vec:
            raise EmbeddingError(f"Ollama returned empty embedding at index {index}")

        if len(vec) != self.expected_dimension:
            raise EmbeddingError(
                f"Embedding at index {index} has dimension {len(vec)}, "
                f"expected {self.expected_dimension}"
            )

        arr = np.array(vec, dtype=np.float32)
        if not np.all(np.isfinite(arr)):
            raise EmbeddingError(f"Embedding at index {index} contains non-finite values")

        # Normalize
        norm = np.linalg.norm(arr)
        if norm > 0:
            arr = arr / norm
        return arr.tolist()

    async def _call_ollama(self, prompt: str) -> List[float]:
        """Make an asynchronous call to Ollama's embedding endpoint."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.model, "prompt": prompt},
                )
                resp.raise_for_status()
        except httpx.ConnectError as e:
            raise EmbeddingUnavailableError(
                f"Cannot connect to Ollama at {self.ollama_base_url}: {e}"
            )
        except httpx.TimeoutException as e:
            raise EmbeddingUnavailableError(
                f"Ollama embedding request timed out after {self.timeout}s: {e}"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise EmbeddingUnavailableError(
                    f"Embedding model '{self.model}' not found in Ollama. "
                    f"Run: ollama pull {self.model}"
                )
            raise EmbeddingUnavailableError(f"Ollama embedding HTTP error: {e}")
        except httpx.RequestError as e:
            raise EmbeddingUnavailableError(f"Ollama embedding request failed: {e}")

        data = resp.json()
        emb = data.get("embedding")
        if not emb:
            raise EmbeddingUnavailableError(
                f"Ollama returned no embedding field. Response keys: {list(data.keys())}"
            )
        return emb

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of document texts.

        Applies the "search_document: " prefix per nomic specification.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of normalized embedding vectors (each a list of floats).

        Raises:
            EmbeddingError: If input validation fails.
            EmbeddingUnavailableError: If Ollama is unreachable.
        """
        if not texts:
            return []

        # Validate inputs
        for i, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise EmbeddingError(f"Invalid text at index {i}: must be a non-empty string")

        results = []
        for i, text in enumerate(texts):
            prompt = f"search_document: {text.strip()}"
            raw = await self._call_ollama(prompt)
            validated = self._validate_vector(raw, index=i)
            results.append(validated)

        return results

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate an embedding for a single query text.

        Applies the "search_query: " prefix per nomic specification.

        Args:
            query: The query text to embed.

        Returns:
            Normalized embedding vector as a list of floats.

        Raises:
            EmbeddingError: If input validation fails.
            EmbeddingUnavailableError: If Ollama is unreachable.
        """
        if not isinstance(query, str) or not query.strip():
            raise EmbeddingError("Query must be a non-empty string")

        prompt = f"search_query: {query.strip()}"
        raw = await self._call_ollama(prompt)
        return self._validate_vector(raw)

    @property
    def model_id(self) -> str:
        """Return the embedding model identifier."""
        return self.model

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self.expected_dimension


def get_embedding_service() -> OllamaEmbeddingService:
    """Factory function to create an OllamaEmbeddingService from application settings."""
    from app.core.config import settings
    return OllamaEmbeddingService(
        ollama_base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_EMBEDDING_MODEL,
        dimension=settings.EMBEDDING_DIMENSION,
        timeout=settings.EMBEDDING_TIMEOUT,
    )
