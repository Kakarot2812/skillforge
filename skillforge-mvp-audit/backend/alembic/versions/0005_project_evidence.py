"""create project_evidence table

Revision ID: 0005_project_evidence
Revises: 0004_github_repositories
Create Date: 2026-09-01 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = '0005_project_evidence'
down_revision: Union[str, None] = '0004_github_repositories'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'project_evidence',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('repo_id', UUID(as_uuid=True), sa.ForeignKey('github_repositories.id', ondelete='CASCADE'), nullable=True),
        sa.Column('skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('evidence_type', sa.String(length=64), nullable=False),
        sa.Column('file_path', sa.String(length=255), nullable=True),
        sa.Column('artifact_name', sa.String(length=128), nullable=True),
        sa.Column('evidence_description', sa.Text(), nullable=True),
        sa.Column('matched_content', sa.Text(), nullable=True),
        sa.Column('evidence_metadata', JSONB, server_default='{}', nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('repo_id', 'skill_id', 'evidence_type', 'file_path', name='uq_project_evidence_repo_skill_type_path'),
    )
    op.create_index(op.f('ix_project_evidence_user_id'), 'project_evidence', ['user_id'], unique=False)
    op.create_index(op.f('ix_project_evidence_repo_id'), 'project_evidence', ['repo_id'], unique=False)
    op.create_index(op.f('ix_project_evidence_skill_id'), 'project_evidence', ['skill_id'], unique=False)
    op.create_index(op.f('ix_project_evidence_evidence_type'), 'project_evidence', ['evidence_type'], unique=False)
    op.create_index(op.f('ix_project_evidence_user_skill'), 'project_evidence', ['user_id', 'skill_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_project_evidence_user_skill'), table_name='project_evidence')
    op.drop_index(op.f('ix_project_evidence_evidence_type'), table_name='project_evidence')
    op.drop_index(op.f('ix_project_evidence_skill_id'), table_name='project_evidence')
    op.drop_index(op.f('ix_project_evidence_repo_id'), table_name='project_evidence')
    op.drop_index(op.f('ix_project_evidence_user_id'), table_name='project_evidence')
    op.drop_table('project_evidence')
