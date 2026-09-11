"""add practice_problems to roadmap_skills, create user_practice_progress table, and update roadmap content

Revision ID: 0013_roadmap_practice_problems
Revises: 0012_skill_roadmaps
Create Date: 2026-09-11 18:00:00.000000

"""
import json
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.db.seed_roadmaps_data import ROADMAPS_SEED_DATA

# revision identifiers, used by Alembic.
revision: str = '0013_roadmap_practice_problems'
down_revision: Union[str, None] = '0012_skill_roadmaps'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add practice_problems column to roadmap_skills
    op.add_column(
        'roadmap_skills',
        sa.Column('practice_problems', JSONB(), server_default='[]', nullable=False)
    )

    # 2. Create user_practice_progress table
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

    # 3. Drop unique constraint temporarily during bulk content migration
    op.drop_constraint('uq_roadmap_skills_stage_order', 'roadmap_skills', type_='unique')

    bind = op.get_bind()

    # Load canonical skill map (slug -> skill_id)
    skill_rows = bind.execute(sa.text("SELECT id, slug FROM skills;")).fetchall()
    canonical_skills = {row[1]: row[0] for row in skill_rows}

    # Fetch existing skill IDs (roadmap_id, slug -> id) to preserve existing progress
    existing_skills_rows = bind.execute(sa.text("SELECT id, roadmap_id, slug FROM roadmap_skills;")).fetchall()
    existing_skill_ids = {(row[1], row[2]): row[0] for row in existing_skills_rows}

    new_skill_keys = set()
    new_stage_ids = set()

    for roadmap_data in ROADMAPS_SEED_DATA:
        roadmap_id = roadmap_data["id"]

        # Upsert roadmap
        bind.execute(
            sa.text(
                "INSERT INTO roadmaps (id, role_id, slug, title, domain, category, description, version, has_market_data, created_at, updated_at) "
                "VALUES (:id, :role_id, :slug, :title, :domain, :category, :description, :version, :has_market_data, now(), now()) "
                "ON CONFLICT (slug) DO UPDATE SET "
                "  title = EXCLUDED.title, "
                "  description = EXCLUDED.description, "
                "  version = EXCLUDED.version, "
                "  has_market_data = EXCLUDED.has_market_data, "
                "  updated_at = now();"
            ),
            {
                "id": roadmap_id,
                "role_id": roadmap_data.get("role_id"),
                "slug": roadmap_data["slug"],
                "title": roadmap_data["title"],
                "domain": roadmap_data["domain"],
                "category": roadmap_data["category"],
                "description": roadmap_data["description"],
                "version": roadmap_data.get("version", "v2.0"),
                "has_market_data": roadmap_data.get("has_market_data", False),
            },
        )

        # Upsert stages
        for stage_data in roadmap_data.get("stages", []):
            stage_order = stage_data["order"]
            stage_res = bind.execute(
                sa.text("SELECT id FROM roadmap_stages WHERE roadmap_id = :roadmap_id AND stage_order = :stage_order;"),
                {"roadmap_id": roadmap_id, "stage_order": stage_order},
            ).fetchone()

            if stage_res:
                actual_stage_id = stage_res[0]
                bind.execute(
                    sa.text(
                        "UPDATE roadmap_stages SET name = :name, description = :description "
                        "WHERE id = :id;"
                    ),
                    {
                        "id": actual_stage_id,
                        "name": stage_data["name"],
                        "description": stage_data.get("description"),
                    },
                )
            else:
                actual_stage_id = uuid.uuid4()
                bind.execute(
                    sa.text(
                        "INSERT INTO roadmap_stages (id, roadmap_id, name, description, stage_order, created_at) "
                        "VALUES (:id, :roadmap_id, :name, :description, :stage_order, now());"
                    ),
                    {
                        "id": actual_stage_id,
                        "roadmap_id": roadmap_id,
                        "name": stage_data["name"],
                        "description": stage_data.get("description"),
                        "stage_order": stage_order,
                    },
                )

            new_stage_ids.add(actual_stage_id)

            # Upsert skills in this stage
            for idx, skill_data in enumerate(stage_data.get("skills", []), start=1):
                canonical_slug = skill_data.get("canonical_slug")
                canonical_id = canonical_skills.get(canonical_slug) if canonical_slug else None
                skill_slug = skill_data["slug"]
                new_skill_keys.add((roadmap_id, skill_slug))

                existing_id = existing_skill_ids.get((roadmap_id, skill_slug))
                if existing_id:
                    roadmap_skill_id = existing_id
                    bind.execute(
                        sa.text(
                            "UPDATE roadmap_skills SET "
                            "  stage_id = :stage_id, "
                            "  canonical_skill_id = :canonical_skill_id, "
                            "  name = :name, "
                            "  description = :description, "
                            "  difficulty = :difficulty, "
                            "  skill_order = :skill_order, "
                            "  key_topics = :key_topics, "
                            "  practice_project = :practice_project, "
                            "  practice_problems = :practice_problems, "
                            "  role_relevance = :role_relevance "
                            "WHERE id = :id;"
                        ),
                        {
                            "id": roadmap_skill_id,
                            "stage_id": actual_stage_id,
                            "canonical_skill_id": canonical_id,
                            "name": skill_data["name"],
                            "description": skill_data["description"],
                            "difficulty": skill_data.get("difficulty", "BEGINNER"),
                            "skill_order": idx,
                            "key_topics": json.dumps(skill_data.get("key_topics", [])),
                            "practice_project": skill_data.get("practice_project"),
                            "practice_problems": json.dumps(skill_data.get("practice_problems", [])),
                            "role_relevance": skill_data.get("role_relevance"),
                        },
                    )
                else:
                    roadmap_skill_id = uuid.uuid4()
                    existing_skill_ids[(roadmap_id, skill_slug)] = roadmap_skill_id
                    bind.execute(
                        sa.text(
                            "INSERT INTO roadmap_skills ("
                            "  id, stage_id, roadmap_id, canonical_skill_id, name, slug, description, "
                            "  difficulty, skill_order, key_topics, practice_project, practice_problems, role_relevance, created_at"
                            ") VALUES ("
                            "  :id, :stage_id, :roadmap_id, :canonical_skill_id, :name, :slug, :description, "
                            "  :difficulty, :skill_order, :key_topics, :practice_project, :practice_problems, :role_relevance, now()"
                            ");"
                        ),
                        {
                            "id": roadmap_skill_id,
                            "stage_id": actual_stage_id,
                            "roadmap_id": roadmap_id,
                            "canonical_skill_id": canonical_id,
                            "name": skill_data["name"],
                            "slug": skill_slug,
                            "description": skill_data["description"],
                            "difficulty": skill_data.get("difficulty", "BEGINNER"),
                            "skill_order": idx,
                            "key_topics": json.dumps(skill_data.get("key_topics", [])),
                            "practice_project": skill_data.get("practice_project"),
                            "practice_problems": json.dumps(skill_data.get("practice_problems", [])),
                            "role_relevance": skill_data.get("role_relevance"),
                        },
                    )

                # Re-seed learning resources
                bind.execute(
                    sa.text("DELETE FROM learning_resources WHERE roadmap_skill_id = :roadmap_skill_id;"),
                    {"roadmap_skill_id": roadmap_skill_id}
                )
                for res in skill_data.get("resources", []):
                    bind.execute(
                        sa.text(
                            "INSERT INTO learning_resources (id, roadmap_skill_id, resource_type, title, url, description, created_at) "
                            "VALUES (:id, :roadmap_skill_id, :resource_type, :title, :url, :description, now());"
                        ),
                        {
                            "id": uuid.uuid4(),
                            "roadmap_skill_id": roadmap_skill_id,
                            "resource_type": res["type"],
                            "title": res["title"],
                            "url": res["url"],
                            "description": res.get("description", ""),
                        },
                    )

        # Re-seed prerequisites for roadmap
        skills_in_roadmap = {
            slug: existing_skill_ids[(roadmap_id, slug)]
            for (r_id, slug) in existing_skill_ids
            if r_id == roadmap_id
        }

        # Clear existing prerequisites for this roadmap's skills
        for s_id in skills_in_roadmap.values():
            bind.execute(
                sa.text("DELETE FROM roadmap_prerequisites WHERE roadmap_skill_id = :skill_id;"),
                {"skill_id": s_id}
            )

        # Insert updated prerequisites
        for stage_data in roadmap_data.get("stages", []):
            for skill_data in stage_data.get("skills", []):
                target_skill_id = skills_in_roadmap.get(skill_data["slug"])
                for prereq_slug in skill_data.get("prerequisites", []):
                    prereq_id = skills_in_roadmap.get(prereq_slug)
                    if target_skill_id and prereq_id:
                        bind.execute(
                            sa.text(
                                "INSERT INTO roadmap_prerequisites (id, roadmap_skill_id, prerequisite_skill_id, created_at) "
                                "VALUES (:id, :roadmap_skill_id, :prerequisite_skill_id, now()) "
                                "ON CONFLICT DO NOTHING;"
                            ),
                            {
                                "id": uuid.uuid4(),
                                "roadmap_skill_id": target_skill_id,
                                "prerequisite_skill_id": prereq_id,
                            },
                        )

    # Clean up obsolete skills that no longer exist in ROADMAPS_SEED_DATA
    for (r_id, slug), s_id in list(existing_skill_ids.items()):
        if (r_id, slug) not in new_skill_keys:
            bind.execute(
                sa.text("DELETE FROM roadmap_skills WHERE id = :id;"),
                {"id": s_id}
            )

    # Clean up obsolete stages that no longer have skills or are orphaned
    bind.execute(
        sa.text("DELETE FROM roadmap_stages WHERE id NOT IN (SELECT DISTINCT stage_id FROM roadmap_skills);")
    )

    # 4. Recreate the unique constraint on (stage_id, skill_order)
    op.create_unique_constraint('uq_roadmap_skills_stage_order', 'roadmap_skills', ['stage_id', 'skill_order'])


def downgrade() -> None:
    # 1. Drop user_practice_progress
    op.drop_index(op.f('ix_user_practice_progress_status'), table_name='user_practice_progress')
    op.drop_index(op.f('ix_user_practice_progress_problem_id'), table_name='user_practice_progress')
    op.drop_index(op.f('ix_user_practice_progress_roadmap_skill_id'), table_name='user_practice_progress')
    op.drop_index(op.f('ix_user_practice_progress_user_id'), table_name='user_practice_progress')
    op.drop_table('user_practice_progress')

    # 2. Drop practice_problems column
    op.drop_column('roadmap_skills', 'practice_problems')
