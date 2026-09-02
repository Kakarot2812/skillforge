"""add growth_rate and location indexes for demand intelligence

Revision ID: 0009_demand_intel_indexes
Revises: 0008_demand_hardening
Create Date: 2026-09-01 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0009_demand_intel_indexes'
down_revision: Union[str, None] = '0008_demand_hardening'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        op.f('ix_skill_demand_growth_rate'),
        'skill_demand',
        ['growth_rate'],
        unique=False,
    )
    op.create_index(
        op.f('ix_skill_demand_location'),
        'skill_demand',
        ['location'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_skill_demand_location'), table_name='skill_demand')
    op.drop_index(op.f('ix_skill_demand_growth_rate'), table_name='skill_demand')
