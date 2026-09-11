"""create market_job_skills table for post-MVP P1-D deterministic skill extraction

Revision ID: 0013_market_job_skills
Revises: 0012_market_jobs
Create Date: 2026-09-10 22:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0013_market_job_skills'
down_revision: Union[str, None] = '0012_market_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'market_job_skills',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('market_job_id', sa.UUID(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=False),
        sa.Column('matched_alias', sa.String(length=128), nullable=False),
        sa.Column('source_field', sa.String(length=32), nullable=False),
        sa.Column('evidence_text', sa.Text(), nullable=True),
        sa.Column('extraction_method', sa.String(length=64), server_default='deterministic_taxonomy_match', nullable=False),
        sa.Column('confidence_score', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('extracted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['market_job_id'], ['market_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('market_job_id', 'skill_id', name='uq_market_job_skills_job_skill')
    )

    op.create_index(op.f('ix_market_job_skills_market_job_id'), 'market_job_skills', ['market_job_id'], unique=False)
    op.create_index(op.f('ix_market_job_skills_skill_id'), 'market_job_skills', ['skill_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_market_job_skills_skill_id'), table_name='market_job_skills')
    op.drop_index(op.f('ix_market_job_skills_market_job_id'), table_name='market_job_skills')
    op.drop_table('market_job_skills')
