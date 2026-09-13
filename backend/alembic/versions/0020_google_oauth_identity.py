"""add google_sub to users

Revision ID: 0020_google_oauth_identity
Revises: 0019_auth_users_and_sessions
Create Date: 2026-09-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0020_google_oauth_identity'
down_revision: Union[str, None] = '0019_auth_users_and_sessions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('google_sub', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_google_sub'), 'users', ['google_sub'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_google_sub'), table_name='users')
    op.drop_column('users', 'google_sub')
