"""create milestone_verifications table

Revision ID: 0018_milestone_verifications
Revises: 0017_roadmap_and_resources
Create Date: 2026-09-11 11:30:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = '0018_milestone_verifications'
down_revision: Union[str, None] = '0017_roadmap_and_resources'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'milestone_verifications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('milestone_id', UUID(as_uuid=True), sa.ForeignKey('roadmap_milestones.id', ondelete='CASCADE'), nullable=False),
        sa.Column('roadmap_id', UUID(as_uuid=True), sa.ForeignKey('candidate_roadmaps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('repository_id', UUID(as_uuid=True), sa.ForeignKey('github_repositories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('commit_sha', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('details', JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('VERIFIED', 'PARTIAL', 'UNVERIFIED', 'FAILED')", name='chk_milestone_verifications_status'),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name='chk_milestone_verifications_confidence'),
    )
    op.create_index(op.f('ix_milestone_verifications_milestone_id'), 'milestone_verifications', ['milestone_id'], unique=False)
    op.create_index(op.f('ix_milestone_verifications_roadmap_id'), 'milestone_verifications', ['roadmap_id'], unique=False)
    op.create_index(op.f('ix_milestone_verifications_user_id'), 'milestone_verifications', ['user_id'], unique=False)
    op.create_index(op.f('ix_milestone_verifications_repository_id'), 'milestone_verifications', ['repository_id'], unique=False)
    op.create_index(op.f('ix_milestone_verifications_status'), 'milestone_verifications', ['status'], unique=False)
    op.create_index(op.f('ix_milestone_verifications_created_at'), 'milestone_verifications', ['created_at'], unique=False)
    op.create_index('ix_milestone_verifications_milestone_created', 'milestone_verifications', ['milestone_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_milestone_verifications_milestone_created', table_name='milestone_verifications')
    op.drop_index(op.f('ix_milestone_verifications_created_at'), table_name='milestone_verifications')
    op.drop_index(op.f('ix_milestone_verifications_status'), table_name='milestone_verifications')
    op.drop_index(op.f('ix_milestone_verifications_repository_id'), table_name='milestone_verifications')
    op.drop_index(op.f('ix_milestone_verifications_user_id'), table_name='milestone_verifications')
    op.drop_index(op.f('ix_milestone_verifications_roadmap_id'), table_name='milestone_verifications')
    op.drop_index(op.f('ix_milestone_verifications_milestone_id'), table_name='milestone_verifications')
    op.drop_table('milestone_verifications')
