"""Add knowledge base tables

Revision ID: bbb123cd45e6
Revises: aaa459ad5da5
Create Date: 2026-10-09 20:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bbb123cd45e6'
down_revision: Union[str, Sequence[str], None] = 'aaa459ad5da5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We will use JSON to store embeddings to support both SQLite and Postgres in the current setup.
    # In a full Postgres setup with pgvector, we would use:
    # op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    # And sa.Column('embedding', vector(384))
    
    op.create_table('transcript_documents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('stable_doc_id', sa.String(), nullable=False),
    sa.Column('episode_title', sa.String(), nullable=True),
    sa.Column('source_url', sa.String(), nullable=True),
    sa.Column('guest', sa.String(), nullable=True),
    sa.Column('publication_date', sa.String(), nullable=True),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('source_path', sa.String(), nullable=True),
    sa.Column('source_metadata', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('stable_doc_id')
    )
    op.create_index(op.f('ix_transcript_documents_content_hash'), 'transcript_documents', ['content_hash'], unique=False)
    op.create_index(op.f('ix_transcript_documents_id'), 'transcript_documents', ['id'], unique=False)
    op.create_index(op.f('ix_transcript_documents_stable_doc_id'), 'transcript_documents', ['stable_doc_id'], unique=False)

    op.create_table('transcript_chunks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('stable_chunk_id', sa.String(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('embedding', sa.JSON(), nullable=True),
    sa.Column('embedding_model', sa.String(), nullable=True),
    sa.Column('start_char_offset', sa.Integer(), nullable=True),
    sa.Column('end_char_offset', sa.Integer(), nullable=True),
    sa.Column('speaker', sa.String(), nullable=True),
    sa.Column('timestamp_start', sa.String(), nullable=True),
    sa.Column('timestamp_end', sa.String(), nullable=True),
    sa.Column('token_count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['document_id'], ['transcript_documents.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('stable_chunk_id')
    )
    op.create_index(op.f('ix_transcript_chunks_document_id'), 'transcript_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_transcript_chunks_id'), 'transcript_chunks', ['id'], unique=False)
    op.create_index(op.f('ix_transcript_chunks_stable_chunk_id'), 'transcript_chunks', ['stable_chunk_id'], unique=False)
    op.create_index('ix_transcript_chunks_document_chunk', 'transcript_chunks', ['document_id', 'chunk_index'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_transcript_chunks_document_chunk', table_name='transcript_chunks')
    op.drop_index(op.f('ix_transcript_chunks_stable_chunk_id'), table_name='transcript_chunks')
    op.drop_index(op.f('ix_transcript_chunks_id'), table_name='transcript_chunks')
    op.drop_index(op.f('ix_transcript_chunks_document_id'), table_name='transcript_chunks')
    op.drop_table('transcript_chunks')
    op.drop_index(op.f('ix_transcript_documents_stable_doc_id'), table_name='transcript_documents')
    op.drop_index(op.f('ix_transcript_documents_id'), table_name='transcript_documents')
    op.drop_index(op.f('ix_transcript_documents_content_hash'), table_name='transcript_documents')
    op.drop_table('transcript_documents')
