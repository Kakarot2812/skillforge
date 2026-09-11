"""create skill_gaps table

Revision ID: 0010_skill_gap_records
Revises: 0009_demand_intel_indexes
Create Date: 2026-09-02 09:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0010_skill_gap_records'
down_revision: Union[str, None] = '0009_demand_intel_indexes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'skill_gaps',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('skill_id', sa.UUID(), nullable=False),
        sa.Column('location', sa.String(length=64), server_default='India', nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('demand_score', sa.Float(), nullable=False),
        sa.Column('growth_rate', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('claimed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('claim_confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('demonstrated', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('demonstrated_score', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('evidence_level', sa.String(length=32), nullable=True),
        sa.Column('evidence_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('gap_metadata', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("demand_score >= 0.0 AND demand_score <= 1.0", name='chk_skill_gap_demand_score_range'),
        sa.CheckConstraint("status IN ('STRONG', 'PARTIAL', 'MISSING')", name='chk_skill_gap_status'),
        sa.ForeignKeyConstraint(['role_id'], ['job_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', 'skill_id', 'location', name='uq_skill_gaps_user_role_skill_loc'),
    )
    op.create_index(op.f('ix_skill_gaps_user_id'), 'skill_gaps', ['user_id'], unique=False)
    op.create_index(op.f('ix_skill_gaps_role_id'), 'skill_gaps', ['role_id'], unique=False)
    op.create_index(op.f('ix_skill_gaps_skill_id'), 'skill_gaps', ['skill_id'], unique=False)
    op.create_index(op.f('ix_skill_gaps_location'), 'skill_gaps', ['location'], unique=False)
    op.create_index(op.f('ix_skill_gaps_status'), 'skill_gaps', ['status'], unique=False)
    op.create_index(op.f('ix_skill_gaps_demand_score'), 'skill_gaps', ['demand_score'], unique=False)
    op.create_index('ix_skill_gaps_user_role', 'skill_gaps', ['user_id', 'role_id'], unique=False)
    op.create_index(
        'uq_skill_gaps_null_user',
        'skill_gaps',
        ['role_id', 'skill_id', 'location'],
        unique=True,
        postgresql_where=sa.text('user_id IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_skill_gaps_null_user', table_name='skill_gaps')
    op.drop_index('ix_skill_gaps_user_role', table_name='skill_gaps')
    op.drop_index(op.f('ix_skill_gaps_demand_score'), table_name='skill_gaps')
    op.drop_index(op.f('ix_skill_gaps_status'), table_name='skill_gaps')
    op.drop_index(op.f('ix_skill_gaps_location'), table_name='skill_gaps')
    op.drop_index(op.f('ix_skill_gaps_skill_id'), table_name='skill_gaps')
    op.drop_index(op.f('ix_skill_gaps_role_id'), table_name='skill_gaps')
    op.drop_index(op.f('ix_skill_gaps_user_id'), table_name='skill_gaps')
    op.drop_table('skill_gaps')
