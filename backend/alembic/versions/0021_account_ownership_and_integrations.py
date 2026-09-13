"""account ownership and integrations

Revision ID: 0021_account_ownership_and_integrations
Revises: 0020_google_oauth_identity
Create Date: 2026-09-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0021_account_ownership_and_integrations'
down_revision: Union[str, None] = '0020_google_oauth_identity'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('connected_github_username', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('active_resume_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_users_active_resume_id'), 'users', ['active_resume_id'], unique=False)
    op.create_foreign_key(
        'fk_users_active_resume_id',
        'users',
        'resumes',
        ['active_resume_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_active_resume_id', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_active_resume_id'), table_name='users')
    op.drop_column('users', 'active_resume_id')
    op.drop_column('users', 'connected_github_username')
