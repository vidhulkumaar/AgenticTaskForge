"""
Database models for the RAG knowledge base.

TranscriptDocument represents an ingested podcast episode transcript.
TranscriptChunk represents a chunk of a transcript with its embedding vector.
"""
from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Text, Integer, Float, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class TranscriptDocument(Base):
    """Represents an ingested podcast transcript document."""
    __tablename__ = "transcript_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # Stable document identifier derived from source (e.g., filename hash)
    stable_doc_id = Column(String, unique=True, nullable=False, index=True)
    episode_title = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    # Guest/author metadata
    guest = Column(String, nullable=True)
    publication_date = Column(String, nullable=True)
    # Content hash for change detection
    content_hash = Column(String(64), nullable=False, index=True)
    # Ingestion metadata
    ingested_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String, default="ingested", nullable=False)  # ingested, failed, updated
    # Source provenance
    source_path = Column(String, nullable=True)
    source_metadata = Column(JSON, nullable=True)

    chunks = relationship("TranscriptChunk", back_populates="document", cascade="all, delete-orphan")


class TranscriptChunk(Base):
    """Represents a chunk of a transcript document with its embedding."""
    __tablename__ = "transcript_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # Deterministic chunk ID for deduplication
    stable_chunk_id = Column(String, unique=True, nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("transcript_documents.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    # Embedding stored as JSON array (compatible with both pgvector and SQLite for testing)
    # In production with pgvector, this would be a Vector column
    embedding = Column(JSON, nullable=True)
    embedding_model = Column(String, nullable=True)
    # Source position metadata
    start_char_offset = Column(Integer, nullable=True)
    end_char_offset = Column(Integer, nullable=True)
    # Speaker and timestamp metadata from original transcript
    speaker = Column(String, nullable=True)
    timestamp_start = Column(String, nullable=True)
    timestamp_end = Column(String, nullable=True)
    # Token count for the chunk
    token_count = Column(Integer, nullable=True)

    document = relationship("TranscriptDocument", back_populates="chunks")

    __table_args__ = (
        Index('ix_transcript_chunks_document_chunk', 'document_id', 'chunk_index'),
    )
