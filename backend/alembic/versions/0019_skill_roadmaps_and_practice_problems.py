"""create roadmaps, stages, skills, prerequisites, resources, progress, and practice progress tables

Revision ID: 0019_skill_roadmaps_and_practice_problems
Revises: 0018_milestone_verifications
Create Date: 2026-09-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = '0019_skill_roadmaps_and_practice_problems'
down_revision: Union[str, None] = '0018_milestone_verifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create roadmaps table
    op.create_table(
        'roadmaps',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('role_id', UUID(as_uuid=True), sa.ForeignKey('job_roles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('slug', sa.String(length=128), unique=True, nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('domain', sa.String(length=128), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('version', sa.String(length=32), server_default='v1.0', nullable=False),
        sa.Column('last_reviewed', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('has_market_data', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_roadmaps_slug'), 'roadmaps', ['slug'], unique=True)
    op.create_index(op.f('ix_roadmaps_role_id'), 'roadmaps', ['role_id'], unique=False)
    op.create_index(op.f('ix_roadmaps_domain'), 'roadmaps', ['domain'], unique=False)

    # 2. Create roadmap_stages table
    op.create_table(
        'roadmap_stages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('roadmap_id', UUID(as_uuid=True), sa.ForeignKey('roadmaps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stage_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('roadmap_id', 'stage_order', name='uq_roadmap_stages_roadmap_stage_order'),
    )
    op.create_index(op.f('ix_roadmap_stages_roadmap_id'), 'roadmap_stages', ['roadmap_id'], unique=False)

    # 3. Create roadmap_skills table
    op.create_table(
        'roadmap_skills',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('stage_id', UUID(as_uuid=True), sa.ForeignKey('roadmap_stages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('roadmap_id', UUID(as_uuid=True), sa.ForeignKey('roadmaps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('canonical_skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.String(length=32), server_default='BEGINNER', nullable=False),
        sa.Column('skill_order', sa.Integer(), nullable=False),
        sa.Column('key_topics', JSONB(), server_default='[]', nullable=False),
        sa.Column('practice_project', sa.Text(), nullable=True),
        sa.Column('practice_problems', JSONB(), server_default='[]', nullable=False),
        sa.Column('role_relevance', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('stage_id', 'skill_order', name='uq_roadmap_skills_stage_order'),
        sa.CheckConstraint("difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED')", name='chk_roadmap_skill_difficulty'),
    )
    op.create_index(op.f('ix_roadmap_skills_stage_id'), 'roadmap_skills', ['stage_id'], unique=False)
    op.create_index(op.f('ix_roadmap_skills_roadmap_id'), 'roadmap_skills', ['roadmap_id'], unique=False)
    op.create_index(op.f('ix_roadmap_skills_canonical_skill_id'), 'roadmap_skills', ['canonical_skill_id'], unique=False)
    op.create_index(op.f('ix_roadmap_skills_slug'), 'roadmap_skills', ['slug'], unique=False)

    # 4. Create roadmap_prerequisites table
    op.create_table(
        'roadmap_prerequisites',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('roadmap_skill_id', UUID(as_uuid=True), sa.ForeignKey('roadmap_skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('prerequisite_skill_id', UUID(as_uuid=True), sa.ForeignKey('roadmap_skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('roadmap_skill_id', 'prerequisite_skill_id', name='uq_roadmap_prereqs_skill_prereq'),
    )
    op.create_index(op.f('ix_roadmap_prerequisites_roadmap_skill_id'), 'roadmap_prerequisites', ['roadmap_skill_id'], unique=False)
    op.create_index(op.f('ix_roadmap_prerequisites_prerequisite_skill_id'), 'roadmap_prerequisites', ['prerequisite_skill_id'], unique=False)

    # 5. Create learning_resources table
    op.create_table(
        'learning_resources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('roadmap_skill_id', UUID(as_uuid=True), sa.ForeignKey('roadmap_skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resource_type', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=512), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("resource_type IN ('DOCUMENTATION', 'YOUTUBE')", name='chk_learning_resource_type'),
    )
    op.create_index(op.f('ix_learning_resources_roadmap_skill_id'), 'learning_resources', ['roadmap_skill_id'], unique=False)

    # 6. Create user_roadmap_progress table
    op.create_table(
        'user_roadmap_progress',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('roadmap_skill_id', UUID(as_uuid=True), sa.ForeignKey('roadmap_skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='NOT_STARTED', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_id', 'roadmap_skill_id', name='uq_user_roadmap_progress_user_skill'),
        sa.CheckConstraint("status IN ('NOT_STARTED', 'LEARNING', 'DONE', 'SKIPPED')", name='chk_user_roadmap_status'),
    )
    op.create_index(op.f('ix_user_roadmap_progress_user_id'), 'user_roadmap_progress', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_roadmap_progress_roadmap_skill_id'), 'user_roadmap_progress', ['roadmap_skill_id'], unique=False)
    op.create_index(op.f('ix_user_roadmap_progress_status'), 'user_roadmap_progress', ['status'], unique=False)

    # 7. Create user_practice_progress table
    op.create_table(
        'user_practice_progress',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('roadmap_skill_id', UUID(as_uuid=True), sa.ForeignKey('roadmap_skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('problem_id', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='NOT_STARTED', nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED')", name='ck_user_practice_progress_status'),
        sa.UniqueConstraint('user_id', 'roadmap_skill_id', 'problem_id', name='uq_user_practice_progress_user_skill_problem'),
    )
    op.create_index(op.f('ix_user_practice_progress_user_id'), 'user_practice_progress', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_practice_progress_roadmap_skill_id'), 'user_practice_progress', ['roadmap_skill_id'], unique=False)
    op.create_index(op.f('ix_user_practice_progress_problem_id'), 'user_practice_progress', ['problem_id'], unique=False)
    op.create_index(op.f('ix_user_practice_progress_status'), 'user_practice_progress', ['status'], unique=False)


def downgrade() -> None:
    # 1. user_practice_progress
    op.drop_index(op.f('ix_user_practice_progress_status'), table_name='user_practice_progress')
    op.drop_index(op.f('ix_user_practice_progress_problem_id'), table_name='user_practice_progress')
    op.drop_index(op.f('ix_user_practice_progress_roadmap_skill_id'), table_name='user_practice_progress')
    op.drop_index(op.f('ix_user_practice_progress_user_id'), table_name='user_practice_progress')
    op.drop_table('user_practice_progress')

    # 2. user_roadmap_progress
    op.drop_index(op.f('ix_user_roadmap_progress_status'), table_name='user_roadmap_progress')
    op.drop_index(op.f('ix_user_roadmap_progress_roadmap_skill_id'), table_name='user_roadmap_progress')
    op.drop_index(op.f('ix_user_roadmap_progress_user_id'), table_name='user_roadmap_progress')
    op.drop_table('user_roadmap_progress')

    # 3. learning_resources
    op.drop_index(op.f('ix_learning_resources_roadmap_skill_id'), table_name='learning_resources')
    op.drop_table('learning_resources')

    # 4. roadmap_prerequisites
    op.drop_index(op.f('ix_roadmap_prerequisites_prerequisite_skill_id'), table_name='roadmap_prerequisites')
    op.drop_index(op.f('ix_roadmap_prerequisites_roadmap_skill_id'), table_name='roadmap_prerequisites')
    op.drop_table('roadmap_prerequisites')

    # 5. roadmap_skills
    op.drop_index(op.f('ix_roadmap_skills_slug'), table_name='roadmap_skills')
    op.drop_index(op.f('ix_roadmap_skills_canonical_skill_id'), table_name='roadmap_skills')
    op.drop_index(op.f('ix_roadmap_skills_roadmap_id'), table_name='roadmap_skills')
    op.drop_index(op.f('ix_roadmap_skills_stage_id'), table_name='roadmap_skills')
    op.drop_table('roadmap_skills')

    # 6. roadmap_stages
    op.drop_index(op.f('ix_roadmap_stages_roadmap_id'), table_name='roadmap_stages')
    op.drop_table('roadmap_stages')

    # 7. roadmaps
    op.drop_index(op.f('ix_roadmaps_domain'), table_name='roadmaps')
    op.drop_index(op.f('ix_roadmaps_role_id'), table_name='roadmaps')
    op.drop_index(op.f('ix_roadmaps_slug'), table_name='roadmaps')
    op.drop_table('roadmaps')
