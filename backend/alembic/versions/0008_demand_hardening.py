"""add positive sample_size check constraint to skill_demand

Revision ID: 0008_demand_hardening
Revises: 0007_job_roles_and_skill_demand
Create Date: 2026-09-01 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008_demand_hardening'
down_revision: Union[str, None] = '0007_job_roles_and_skill_demand'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        'chk_sample_size_positive',
        'skill_demand',
        'sample_size > 0',
    )


def downgrade() -> None:
    op.drop_constraint(
        'chk_sample_size_positive',
        'skill_demand',
        type_='check',
    )
