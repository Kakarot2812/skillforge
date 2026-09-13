"""create user_profiles table

Revision ID: 0020_user_profiles
Revises: 0019_conversations_and_messages
Create Date: 2026-09-13 20:15:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '0020_user_profiles'
down_revision: Union[str, None] = '0019_conversations_and_messages'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_profiles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('education', sa.String(length=255), nullable=True),
        sa.Column('college', sa.String(length=255), nullable=True),
        sa.Column('degree', sa.String(length=255), nullable=True),
        sa.Column('branch', sa.String(length=255), nullable=True),
        sa.Column('semester', sa.Integer(), nullable=True),
        sa.Column('target_role', sa.String(length=255), nullable=True),
        sa.Column('experience_level', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_user_profiles_user_id'),
    )


def downgrade() -> None:
    op.drop_table('user_profiles')
