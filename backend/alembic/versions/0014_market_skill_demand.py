"""create market_skill_demand table for post-MVP P1-E deterministic demand aggregation

Revision ID: 0014_market_skill_demand
Revises: 0013_market_job_skills
Create Date: 2026-09-10 22:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0014_market_skill_demand'
down_revision: Union[str, None] = '0013_market_job_skills'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'market_skill_demand',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=64), server_default='adzuna', nullable=False),
        sa.Column('job_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False),
        sa.Column('demand_share', sa.Float(), nullable=False),
        sa.Column('demand_score', sa.Float(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('demand_score >= 0.0 AND demand_score <= 1.0', name='chk_market_skill_demand_score_range'),
        sa.CheckConstraint('demand_share >= 0.0 AND demand_share <= 1.0', name='chk_market_skill_demand_share_range'),
        sa.CheckConstraint('job_count >= 0', name='chk_market_skill_demand_job_count_non_negative'),
        sa.CheckConstraint('sample_size >= 0', name='chk_market_skill_demand_sample_size_non_negative'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source', 'skill_id', name='uq_market_skill_demand_source_skill'),
    )

    op.create_index(op.f('ix_market_skill_demand_skill_id'), 'market_skill_demand', ['skill_id'], unique=False)
    op.create_index(op.f('ix_market_skill_demand_source'), 'market_skill_demand', ['source'], unique=False)
    op.create_index(op.f('ix_market_skill_demand_demand_score'), 'market_skill_demand', ['demand_score'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_market_skill_demand_demand_score'), table_name='market_skill_demand')
    op.drop_index(op.f('ix_market_skill_demand_source'), table_name='market_skill_demand')
    op.drop_index(op.f('ix_market_skill_demand_skill_id'), table_name='market_skill_demand')
    op.drop_table('market_skill_demand')
