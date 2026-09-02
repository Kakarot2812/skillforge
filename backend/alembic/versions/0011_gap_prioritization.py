"""add priority_score, priority_level, and scoring_version to skill_gaps

Revision ID: 0011_gap_prioritization
Revises: 0010_skill_gap_records
Create Date: 2026-09-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0011_gap_prioritization'
down_revision: Union[str, None] = '0010_skill_gap_records'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('skill_gaps', sa.Column('priority_score', sa.Float(), nullable=True))
    op.add_column('skill_gaps', sa.Column('priority_level', sa.String(length=32), nullable=True))
    op.add_column('skill_gaps', sa.Column('scoring_version', sa.String(length=16), server_default='v1', nullable=False))

    op.create_index(op.f('ix_skill_gaps_priority_score'), 'skill_gaps', ['priority_score'], unique=False)
    op.create_index(op.f('ix_skill_gaps_priority_level'), 'skill_gaps', ['priority_level'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_skill_gaps_priority_level'), table_name='skill_gaps')
    op.drop_index(op.f('ix_skill_gaps_priority_score'), table_name='skill_gaps')

    op.drop_column('skill_gaps', 'scoring_version')
    op.drop_column('skill_gaps', 'priority_level')
    op.drop_column('skill_gaps', 'priority_score')
