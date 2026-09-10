"""create market_skill_demand_snapshots and market_skill_demand_growth tables for post-MVP P1-F historical growth

Revision ID: 0015_market_skill_demand_snapshots
Revises: 0014_market_skill_demand
Create Date: 2026-09-10 23:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0015_market_demand_snapshots'
down_revision: Union[str, None] = '0014_market_skill_demand'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Historical Snapshots Table
    op.create_table(
        'market_skill_demand_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=64), server_default='adzuna', nullable=False),
        sa.Column('job_count', sa.Integer(), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False),
        sa.Column('demand_share', sa.Float(), nullable=False),
        sa.Column('demand_score', sa.Float(), nullable=False),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('demand_score >= 0.0 AND demand_score <= 1.0', name='chk_market_skill_demand_snapshots_score_range'),
        sa.CheckConstraint('demand_share >= 0.0 AND demand_share <= 1.0', name='chk_market_skill_demand_snapshots_share_range'),
        sa.CheckConstraint('job_count >= 0', name='chk_market_skill_demand_snapshots_job_count_non_negative'),
        sa.CheckConstraint('sample_size >= 0', name='chk_market_skill_demand_snapshots_sample_size_non_negative'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'skill_id', 'snapshot_at', name='uq_market_skill_demand_snapshots_source_skill_time'),
    )

    op.create_index(op.f('ix_market_skill_demand_snapshots_skill_id'), 'market_skill_demand_snapshots', ['skill_id'], unique=False)
    op.create_index(op.f('ix_market_skill_demand_snapshots_source'), 'market_skill_demand_snapshots', ['source'], unique=False)
    op.create_index(op.f('ix_market_skill_demand_snapshots_snapshot_at'), 'market_skill_demand_snapshots', ['snapshot_at'], unique=False)
    op.create_index('ix_market_skill_demand_snapshots_source_time', 'market_skill_demand_snapshots', ['source', 'snapshot_at'], unique=False)

    # 2. Latest Materialized Growth Table
    op.create_table(
        'market_skill_demand_growth',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=64), server_default='adzuna', nullable=False),
        sa.Column('previous_snapshot_id', sa.UUID(), nullable=True),
        sa.Column('current_snapshot_id', sa.UUID(), nullable=False),
        sa.Column('previous_demand_score', sa.Float(), nullable=False),
        sa.Column('current_demand_score', sa.Float(), nullable=False),
        sa.Column('growth_rate', sa.Float(), nullable=False),
        sa.Column('growth_class', sa.String(length=16), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['previous_snapshot_id'], ['market_skill_demand_snapshots.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['current_snapshot_id'], ['market_skill_demand_snapshots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'skill_id', name='uq_market_skill_demand_growth_source_skill'),
    )

    op.create_index(op.f('ix_market_skill_demand_growth_skill_id'), 'market_skill_demand_growth', ['skill_id'], unique=False)
    op.create_index(op.f('ix_market_skill_demand_growth_source'), 'market_skill_demand_growth', ['source'], unique=False)
    op.create_index(op.f('ix_market_skill_demand_growth_growth_class'), 'market_skill_demand_growth', ['growth_class'], unique=False)


def downgrade() -> None:
    # Drop growth table
    op.drop_index(op.f('ix_market_skill_demand_growth_growth_class'), table_name='market_skill_demand_growth')
    op.drop_index(op.f('ix_market_skill_demand_growth_source'), table_name='market_skill_demand_growth')
    op.drop_index(op.f('ix_market_skill_demand_growth_skill_id'), table_name='market_skill_demand_growth')
    op.drop_table('market_skill_demand_growth')

    # Drop snapshots table
    op.drop_index('ix_market_skill_demand_snapshots_source_time', table_name='market_skill_demand_snapshots')
    op.drop_index(op.f('ix_market_skill_demand_snapshots_snapshot_at'), table_name='market_skill_demand_snapshots')
    op.drop_index(op.f('ix_market_skill_demand_snapshots_source'), table_name='market_skill_demand_snapshots')
    op.drop_index(op.f('ix_market_skill_demand_snapshots_skill_id'), table_name='market_skill_demand_snapshots')
    op.drop_table('market_skill_demand_snapshots')
