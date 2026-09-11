"""create rag_documents and rag_chunks tables for post-MVP P3 evidence retrieval layer

Revision ID: 0016_rag_evidence
Revises: 0015_market_demand_snapshots
Create Date: 2026-09-11 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

from app.config import settings

# revision identifiers, used by Alembic.
revision: str = '0016_rag_evidence'
down_revision: Union[str, None] = '0015_market_demand_snapshots'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. RAG Documents Table
    op.create_table(
        'rag_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('source_reference', sa.String(length=512), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('document_metadata', JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index(op.f('ix_rag_documents_source_type'), 'rag_documents', ['source_type'], unique=False)
    op.create_index(op.f('ix_rag_documents_source_reference'), 'rag_documents', ['source_reference'], unique=False)

    # 2. RAG Chunks Table
    op.create_table(
        'rag_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(settings.EMBEDDING_DIMENSION), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=True),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('source_reference', sa.String(length=512), nullable=False),
        sa.Column('chunk_metadata', JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('chunk_index >= 0', name='chk_rag_chunks_chunk_index_non_negative'),
        sa.ForeignKeyConstraint(['document_id'], ['rag_documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'chunk_index', name='uq_rag_chunks_document_chunk_index'),
    )

    op.create_index(op.f('ix_rag_chunks_document_id'), 'rag_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_rag_chunks_skill_id'), 'rag_chunks', ['skill_id'], unique=False)
    op.create_index(op.f('ix_rag_chunks_source_type'), 'rag_chunks', ['source_type'], unique=False)
    op.create_index(op.f('ix_rag_chunks_source_reference'), 'rag_chunks', ['source_reference'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_rag_chunks_source_reference'), table_name='rag_chunks')
    op.drop_index(op.f('ix_rag_chunks_source_type'), table_name='rag_chunks')
    op.drop_index(op.f('ix_rag_chunks_skill_id'), table_name='rag_chunks')
    op.drop_index(op.f('ix_rag_chunks_document_id'), table_name='rag_chunks')
    op.drop_table('rag_chunks')

    op.drop_index(op.f('ix_rag_documents_source_reference'), table_name='rag_documents')
    op.drop_index(op.f('ix_rag_documents_source_type'), table_name='rag_documents')
    op.drop_table('rag_documents')
