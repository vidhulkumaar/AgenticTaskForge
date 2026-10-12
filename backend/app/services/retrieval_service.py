"""
Retrieval service for searching the knowledge base.

Performs vector similarity search against transcript chunks,
returning ranked results with source metadata. Independent of the model provider.
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.models.knowledge_base import TranscriptDocument, TranscriptChunk
from app.services.embedding_service import OllamaEmbeddingService, EmbeddingError, EmbeddingUnavailableError, get_embedding_service

logger = logging.getLogger(__name__)


class RetrievalError(Exception):
    """Raised when retrieval fails."""
    pass


@dataclass
class RetrievalResult:
    """A single retrieval result with source metadata."""
    chunk_id: str
    document_id: str
    episode_title: Optional[str]
    source_url: Optional[str]
    content: str
    similarity_score: float
    chunk_index: int
    speaker: Optional[str] = None
    timestamp_start: Optional[str] = None
    guest: Optional[str] = None
    publication_date: Optional[str] = None


class RetrievalService:
    """
    Handles vector similarity search against the transcript knowledge base.
    
    Uses the same embedding model for queries as was used for documents,
    preventing incompatible embeddings from being silently mixed.
    """

    def __init__(self, embedding_service=None,
                 top_k: int = 5, similarity_threshold: float = 0.3):
        self._embedding_service = embedding_service
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    @property
    def embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service

    async def search(
        self,
        db: AsyncSession,
        query: str,
        conversation_context: Optional[str] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[RetrievalResult]:
        """
        Search the knowledge base for relevant transcript passages.
        
        Args:
            db: Database session.
            query: The user's question.
            conversation_context: Optional context from the conversation for better retrieval.
            top_k: Override default top_k.
            similarity_threshold: Override default threshold.
            
        Returns:
            List of RetrievalResult objects sorted by relevance (highest first).
            
        Raises:
            RetrievalError: If retrieval infrastructure fails.
        """
        if not query or not query.strip():
            return []

        top_k = top_k or self.top_k
        similarity_threshold = similarity_threshold or self.similarity_threshold

        # Combine query with conversation context for better retrieval
        search_query = query.strip()
        if conversation_context:
            # Append context to query to give the embedding model context about the current topic
            # We truncate the context to avoid shifting the embedding too far from the new question
            # ~200 chars of recent context is usually enough for pronoun resolution or topic continuity
            context_excerpt = conversation_context[-200:]
            search_query = f"{context_excerpt}\n\nQuery: {query.strip()}"

        # Generate query embedding
        try:
            query_embedding = await self.embedding_service.embed_query(search_query)
        except EmbeddingUnavailableError:
            raise  # Let 503 handler catch this
        except EmbeddingError as e:
            raise RetrievalError(f"Failed to generate query embedding: {str(e)}")

        # Perform vector search
        try:
            return await self._cosine_similarity_search(
                db, query_embedding, top_k, similarity_threshold
            )
        except RetrievalError:
            raise
        except Exception as e:
            raise RetrievalError(f"Vector search failed: {str(e)}")

    async def _cosine_similarity_search(
        self,
        db: AsyncSession,
        query_embedding: List[float],
        top_k: int,
        similarity_threshold: float,
    ) -> List[RetrievalResult]:
        """
        Perform cosine similarity search using in-application computation.
        
        This works with both SQLite (testing) and PostgreSQL.
        For production with pgvector, this should use SQL-level vector operations.
        """
        # Fetch all chunks with their embeddings and document data
        stmt = (
            select(TranscriptChunk, TranscriptDocument)
            .join(TranscriptDocument, TranscriptChunk.document_id == TranscriptDocument.id)
            .where(TranscriptChunk.embedding.isnot(None))
            .where(TranscriptDocument.status == "ingested")
        )
        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            return []

        # Compute cosine similarities
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return []
        query_vec = query_vec / query_norm

        scored_results: List[RetrievalResult] = []
        for chunk, doc in rows:
            if not chunk.embedding:
                continue
            
            chunk_vec = np.array(chunk.embedding, dtype=np.float32)
            chunk_norm = np.linalg.norm(chunk_vec)
            if chunk_norm == 0:
                continue
            chunk_vec = chunk_vec / chunk_norm

            similarity = float(np.dot(query_vec, chunk_vec))
            
            if similarity >= similarity_threshold:
                scored_results.append(RetrievalResult(
                    chunk_id=str(chunk.stable_chunk_id),
                    document_id=str(doc.stable_doc_id),
                    episode_title=doc.episode_title,
                    source_url=doc.source_url,
                    content=chunk.content,
                    similarity_score=similarity,
                    chunk_index=chunk.chunk_index,
                    speaker=chunk.speaker,
                    timestamp_start=chunk.timestamp_start,
                    guest=doc.guest,
                    publication_date=doc.publication_date,
                ))

        # Sort by similarity (highest first), tiebreak by chunk_index (deterministic)
        scored_results.sort(key=lambda r: (-r.similarity_score, r.chunk_index))
        return scored_results[:top_k]

    async def check_knowledge_base_status(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Check the status of the knowledge base.
        
        Returns:
            Dictionary with document count, chunk count, and embedding status.
        """
        try:
            doc_count = await db.execute(
                select(TranscriptDocument).where(TranscriptDocument.status == "ingested")
            )
            docs = doc_count.scalars().all()

            chunk_count = await db.execute(
                select(TranscriptChunk).where(TranscriptChunk.embedding.isnot(None))
            )
            chunks = chunk_count.scalars().all()

            return {
                "documents_ingested": len(docs),
                "chunks_with_embeddings": len(chunks),
                "status": "ready" if len(chunks) > 0 else "empty",
            }
        except Exception as e:
            return {
                "documents_ingested": 0,
                "chunks_with_embeddings": 0,
                "status": "error",
                "error": str(e),
            }


def get_retrieval_service() -> RetrievalService:
    """Factory function to create a RetrievalService from application settings."""
    from app.core.config import settings
    return RetrievalService(
        top_k=settings.RETRIEVAL_TOP_K,
        similarity_threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD
    )
