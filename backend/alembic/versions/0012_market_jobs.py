"""create market_jobs table for post-MVP P1-C market persistence

Revision ID: 0012_market_jobs
Revises: 0011_gap_prioritization
Create Date: 2026-09-10 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0012_market_jobs'
down_revision: Union[str, None] = '0011_gap_prioritization'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'market_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('external_job_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('category', sa.String(length=128), nullable=True),
        sa.Column('contract_type', sa.String(length=64), nullable=True),
        sa.Column('contract_time', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('redirect_url', sa.String(length=1024), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'external_job_id', name='uq_market_jobs_source_external_job_id')
    )

    op.create_index(op.f('ix_market_jobs_source'), 'market_jobs', ['source'], unique=False)
    op.create_index(op.f('ix_market_jobs_ingested_at'), 'market_jobs', ['ingested_at'], unique=False)
    op.create_index(op.f('ix_market_jobs_created_at'), 'market_jobs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_market_jobs_created_at'), table_name='market_jobs')
    op.drop_index(op.f('ix_market_jobs_ingested_at'), table_name='market_jobs')
    op.drop_index(op.f('ix_market_jobs_source'), table_name='market_jobs')
    op.drop_table('market_jobs')
