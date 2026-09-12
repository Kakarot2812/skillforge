"""create rag_documents and rag_chunks tables for the RAG evidence layer

Revision ID: 0012_rag_documents_and_chunks
Revises: 0011_gap_prioritization
Create Date: 2026-09-12 00:00:00.000000

RAG_EMBEDDING_DIMENSIONS is fixed at 1024 here (see app/rag/config.py):
comfortably under pgvector's ~2000-dim HNSW indexing ceiling for the plain
`vector` type (confirmed against the installed pgvector 0.8.6 extension).
Changing the embedding dimension in production requires a new migration
that alters this column and a full re-ingest of all documents.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '0012_rag_documents_and_chunks'
down_revision: Union[str, None] = '0011_gap_prioritization'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSIONS = 1024


def upgrade() -> None:
    op.create_table(
        'rag_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('source_id', sa.String(length=128), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('document_metadata', JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False,
        ),
        sa.UniqueConstraint('source_type', 'source_id', name='uq_rag_documents_source'),
    )
    op.create_index(op.f('ix_rag_documents_user_id'), 'rag_documents', ['user_id'], unique=False)
    op.create_index(op.f('ix_rag_documents_source_type'), 'rag_documents', ['source_type'], unique=False)

    op.create_table(
        'rag_chunks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('rag_documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('embedding', Vector(EMBEDDING_DIMENSIONS), nullable=True),
        sa.Column('chunk_metadata', JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False,
        ),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_rag_chunks_document_index'),
    )
    op.create_index(op.f('ix_rag_chunks_document_id'), 'rag_chunks', ['document_id'], unique=False)

    # Generated, persisted full-text search column (Postgres 12+ generated columns).
    op.execute(
        "ALTER TABLE rag_chunks ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"
    )
    op.execute(
        "CREATE INDEX ix_rag_chunks_search_vector ON rag_chunks USING gin (search_vector)"
    )
    op.execute(
        "CREATE INDEX ix_rag_chunks_embedding_hnsw ON rag_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_rag_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_rag_chunks_search_vector")
    op.drop_index(op.f('ix_rag_chunks_document_id'), table_name='rag_chunks')
    op.drop_table('rag_chunks')

    op.drop_index(op.f('ix_rag_documents_source_type'), table_name='rag_documents')
    op.drop_index(op.f('ix_rag_documents_user_id'), table_name='rag_documents')
    op.drop_table('rag_documents')
