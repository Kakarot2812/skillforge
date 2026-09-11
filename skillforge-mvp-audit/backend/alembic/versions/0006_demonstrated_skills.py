"""create demonstrated_skills table

Revision ID: 0006_demonstrated_skills
Revises: 0005_project_evidence
Create Date: 2026-09-01 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = '0006_demonstrated_skills'
down_revision: Union[str, None] = '0005_project_evidence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'demonstrated_skills',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('evidence_level', sa.String(length=32), nullable=False),
        sa.Column('evidence_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('repository_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('skill_metadata', JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_id', 'skill_id', name='uq_demonstrated_skills_user_skill'),
    )
    op.create_index(op.f('ix_demonstrated_skills_user_id'), 'demonstrated_skills', ['user_id'], unique=False)
    op.create_index(op.f('ix_demonstrated_skills_skill_id'), 'demonstrated_skills', ['skill_id'], unique=False)
    op.create_index(op.f('ix_demonstrated_skills_confidence_score'), 'demonstrated_skills', ['confidence_score'], unique=False)
    op.create_index(op.f('ix_demonstrated_skills_user_skill'), 'demonstrated_skills', ['user_id', 'skill_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_demonstrated_skills_user_skill'), table_name='demonstrated_skills')
    op.drop_index(op.f('ix_demonstrated_skills_confidence_score'), table_name='demonstrated_skills')
    op.drop_index(op.f('ix_demonstrated_skills_skill_id'), table_name='demonstrated_skills')
    op.drop_index(op.f('ix_demonstrated_skills_user_id'), table_name='demonstrated_skills')
    op.drop_table('demonstrated_skills')
