"""create github_repositories table

Revision ID: 0004_github_repositories
Revises: 0003_skills_and_aliases
Create Date: 2026-09-01 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = '0004_github_repositories'
down_revision: Union[str, None] = '0003_skills_and_aliases'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'github_repositories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('github_repository_id', sa.BigInteger(), nullable=True),
        sa.Column('repo_name', sa.String(length=128), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('repo_url', sa.String(length=512), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_branch', sa.String(length=64), server_default='main', nullable=True),
        sa.Column('visibility', sa.String(length=32), server_default='public', nullable=True),
        sa.Column('primary_language', sa.String(length=64), nullable=True),
        sa.Column('is_fork', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('stars_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('forks_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_pushed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('repo_metadata', JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('synced_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_id', 'repo_url', name='uq_github_repos_user_repo_url'),
    )
    op.create_index(op.f('ix_github_repositories_user_id'), 'github_repositories', ['user_id'], unique=False)
    op.create_index(op.f('ix_github_repositories_github_repository_id'), 'github_repositories', ['github_repository_id'], unique=False)
    op.create_index(op.f('ix_github_repositories_repo_name'), 'github_repositories', ['repo_name'], unique=False)
    op.create_index(op.f('ix_github_repositories_full_name'), 'github_repositories', ['full_name'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_github_repositories_full_name'), table_name='github_repositories')
    op.drop_index(op.f('ix_github_repositories_repo_name'), table_name='github_repositories')
    op.drop_index(op.f('ix_github_repositories_github_repository_id'), table_name='github_repositories')
    op.drop_index(op.f('ix_github_repositories_user_id'), table_name='github_repositories')
    op.drop_table('github_repositories')
