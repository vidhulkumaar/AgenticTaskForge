"""
Fake embedding service for unit tests ONLY.

This produces deterministic, controllable vectors so that retrieval tests
can run without a real Ollama server. The class name is deliberately verbose
to make accidental use in production obvious.

DO NOT use this outside of tests/.
"""
from typing import List, Optional
import numpy as np


class FakeEmbeddingForUnitTestsOnly:
    """Deterministic fake embedding service for unit tests.

    Constructor takes an optional query_vector that embed_query() will return.
    embed_documents() returns the same vector for every document.
    """

    def __init__(self, query_vector: Optional[List[float]] = None, dimension: int = 3):
        self._query_vector = query_vector or [1.0] + [0.0] * (dimension - 1)
        self._dimension = dimension

    def embed_query(self, query: str) -> List[float]:
        return list(self._query_vector)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [list(self._query_vector) for _ in texts]

    @property
    def model_id(self) -> str:
        return "fake-embedding-for-unit-tests"

    @property
    def dimension(self) -> int:
        return self._dimension
