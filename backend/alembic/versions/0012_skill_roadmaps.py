"""create roadmaps, stages, skills, prerequisites, resources, and progress tables and seed catalog

Revision ID: 0012_skill_roadmaps
Revises: 0011_gap_prioritization
Create Date: 2026-09-03 12:00:00.000000

"""
import json
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.seed_roadmaps_data import ROADMAPS_SEED_DATA

# revision identifiers, used by Alembic.
revision: str = '0012_skill_roadmaps'
down_revision: Union[str, None] = '0011_gap_prioritization'
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

    # 7. Seed canonical and curated roadmaps
    bind = op.get_bind()

    # Load canonical skill map (slug -> skill_id)
    skill_rows = bind.execute(sa.text("SELECT id, slug FROM skills;")).fetchall()
    canonical_skills = {row[1]: row[0] for row in skill_rows}

    for roadmap_data in ROADMAPS_SEED_DATA:
        roadmap_id = roadmap_data["id"]
        bind.execute(
            sa.text(
                "INSERT INTO roadmaps (id, role_id, slug, title, domain, category, description, version, has_market_data, created_at, updated_at) "
                "VALUES (:id, :role_id, :slug, :title, :domain, :category, :description, :version, :has_market_data, now(), now()) "
                "ON CONFLICT (slug) DO NOTHING;"
            ),
            {
                "id": roadmap_id,
                "role_id": roadmap_data.get("role_id"),
                "slug": roadmap_data["slug"],
                "title": roadmap_data["title"],
                "domain": roadmap_data["domain"],
                "category": roadmap_data["category"],
                "description": roadmap_data["description"],
                "version": roadmap_data.get("version", "v1.0"),
                "has_market_data": roadmap_data.get("has_market_data", False),
            },
        )

        skill_slug_to_id = {}
        pending_prereqs = []

        for stage_data in roadmap_data.get("stages", []):
            stage_id = uuid.uuid4()
            bind.execute(
                sa.text(
                    "INSERT INTO roadmap_stages (id, roadmap_id, name, description, stage_order, created_at) "
                    "VALUES (:id, :roadmap_id, :name, :description, :stage_order, now()) "
                    "ON CONFLICT (roadmap_id, stage_order) DO NOTHING;"
                ),
                {
                    "id": stage_id,
                    "roadmap_id": roadmap_id,
                    "name": stage_data["name"],
                    "description": stage_data.get("description"),
                    "stage_order": stage_data["order"],
                },
            )

            # Retrieve actual stage id if conflicted
            stage_res = bind.execute(
                sa.text("SELECT id FROM roadmap_stages WHERE roadmap_id = :roadmap_id AND stage_order = :stage_order;"),
                {"roadmap_id": roadmap_id, "stage_order": stage_data["order"]},
            ).fetchone()
            actual_stage_id = stage_res[0] if stage_res else stage_id

            for idx, skill_data in enumerate(stage_data.get("skills", []), start=1):
                roadmap_skill_id = uuid.uuid4()
                canonical_slug = skill_data.get("canonical_slug")
                canonical_id = canonical_skills.get(canonical_slug) if canonical_slug else None

                bind.execute(
                    sa.text(
                        "INSERT INTO roadmap_skills (id, stage_id, roadmap_id, canonical_skill_id, name, slug, description, difficulty, skill_order, key_topics, practice_project, role_relevance, created_at) "
                        "VALUES (:id, :stage_id, :roadmap_id, :canonical_skill_id, :name, :slug, :description, :difficulty, :skill_order, :key_topics, :practice_project, :role_relevance, now()) "
                        "ON CONFLICT (stage_id, skill_order) DO NOTHING;"
                    ),
                    {
                        "id": roadmap_skill_id,
                        "stage_id": actual_stage_id,
                        "roadmap_id": roadmap_id,
                        "canonical_skill_id": canonical_id,
                        "name": skill_data["name"],
                        "slug": skill_data["slug"],
                        "description": skill_data["description"],
                        "difficulty": skill_data.get("difficulty", "BEGINNER"),
                        "skill_order": idx,
                        "key_topics": json.dumps(skill_data.get("key_topics", [])),
                        "practice_project": skill_data.get("practice_project"),
                        "role_relevance": skill_data.get("role_relevance"),
                    },
                )

                # Retrieve actual skill id
                skill_res = bind.execute(
                    sa.text("SELECT id FROM roadmap_skills WHERE stage_id = :stage_id AND skill_order = :skill_order;"),
                    {"stage_id": actual_stage_id, "skill_order": idx},
                ).fetchone()
                actual_skill_id = skill_res[0] if skill_res else roadmap_skill_id
                skill_slug_to_id[skill_data["slug"]] = actual_skill_id

                if skill_data.get("prerequisites"):
                    for prereq_slug in skill_data["prerequisites"]:
                        pending_prereqs.append((actual_skill_id, prereq_slug))

                for res_data in skill_data.get("resources", []):
                    bind.execute(
                        sa.text(
                            "INSERT INTO learning_resources (id, roadmap_skill_id, resource_type, title, url, description, created_at) "
                            "VALUES (:id, :roadmap_skill_id, :resource_type, :title, :url, :description, now());"
                        ),
                        {
                            "id": uuid.uuid4(),
                            "roadmap_skill_id": actual_skill_id,
                            "resource_type": res_data["type"],
                            "title": res_data["title"],
                            "url": res_data["url"],
                            "description": res_data["description"],
                        },
                    )

        # Wire prerequisites
        for skill_id, prereq_slug in pending_prereqs:
            prereq_skill_id = skill_slug_to_id.get(prereq_slug)
            if prereq_skill_id and prereq_skill_id != skill_id:
                bind.execute(
                    sa.text(
                        "INSERT INTO roadmap_prerequisites (id, roadmap_skill_id, prerequisite_skill_id, created_at) "
                        "VALUES (:id, :roadmap_skill_id, :prerequisite_skill_id, now()) "
                        "ON CONFLICT (roadmap_skill_id, prerequisite_skill_id) DO NOTHING;"
                    ),
                    {
                        "id": uuid.uuid4(),
                        "roadmap_skill_id": skill_id,
                        "prerequisite_skill_id": prereq_skill_id,
                    },
                )


def downgrade() -> None:
    op.drop_table('user_roadmap_progress')
    op.drop_table('learning_resources')
    op.drop_table('roadmap_prerequisites')
    op.drop_table('roadmap_skills')
    op.drop_table('roadmap_stages')
    op.drop_table('roadmaps')
