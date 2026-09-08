"""create job_roles and skill_demand tables and seed canonical roles and demand data

Revision ID: 0007_job_roles_and_skill_demand
Revises: 0006_demonstrated_skills
Create Date: 2026-09-01 21:45:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '0007_job_roles_and_skill_demand'
down_revision: Union[str, None] = '0006_demonstrated_skills'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CANONICAL_ROLES = [
    {
        "id": uuid.UUID("9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c"),
        "title": "Backend Engineer",
        "slug": "backend-engineer",
        "category": "Engineering",
        "description": "Designs, implements, and maintains scalable server-side systems, databases, and APIs.",
    },
    {
        "id": uuid.UUID("0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d"),
        "title": "Full Stack Engineer",
        "slug": "full-stack-engineer",
        "category": "Engineering",
        "description": "Builds complete web applications covering frontend user interfaces and backend services.",
    },
    {
        "id": uuid.UUID("1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e"),
        "title": "Frontend Engineer",
        "slug": "frontend-engineer",
        "category": "Engineering",
        "description": "Develops responsive, accessible, and performant web interfaces and client-side logic.",
    },
    {
        "id": uuid.UUID("2c3d4e5f-6a7b-8c9d-0e1f-2a3b4c5d6e7f"),
        "title": "Cloud/DevOps Engineer",
        "slug": "cloud-devops-engineer",
        "category": "Cloud & Infrastructure",
        "description": "Automates cloud infrastructure, continuous deployment pipelines, and system reliability.",
    },
    {
        "id": uuid.UUID("3d4e5f6a-7b8c-9d0e-1f2a-3b4c5d6e7f8a"),
        "title": "AI/ML Engineer",
        "slug": "ai-ml-engineer",
        "category": "Data & AI",
        "description": "Designs and deploys machine learning models, data pipelines, and vector database systems.",
    },
]

# (role_slug, skill_slug, demand_score, growth_rate, sample_size)
CANONICAL_DEMAND = [
    # Backend Engineer
    ("backend-engineer", "java", 0.72, 0.04, 14200),
    ("backend-engineer", "python", 0.68, 0.08, 14200),
    ("backend-engineer", "postgresql", 0.65, 0.09, 14200),
    ("backend-engineer", "spring-boot", 0.64, 0.05, 14200),
    ("backend-engineer", "sql", 0.61, 0.03, 14200),
    ("backend-engineer", "fastapi", 0.55, 0.15, 14200),
    ("backend-engineer", "docker", 0.51, 0.12, 14200),
    ("backend-engineer", "aws", 0.47, 0.09, 14200),
    ("backend-engineer", "redis", 0.44, 0.07, 14200),
    ("backend-engineer", "kubernetes", 0.35, 0.14, 14200),
    ("backend-engineer", "git", 0.78, 0.02, 14200),
    ("backend-engineer", "rest-apis", 0.75, 0.04, 14200),
    ("backend-engineer", "pytest", 0.42, 0.06, 14200),

    # Full Stack Engineer
    ("full-stack-engineer", "javascript", 0.74, 0.02, 11800),
    ("full-stack-engineer", "typescript", 0.70, 0.11, 11800),
    ("full-stack-engineer", "react", 0.68, 0.07, 11800),
    ("full-stack-engineer", "nodejs", 0.64, 0.05, 11800),
    ("full-stack-engineer", "postgresql", 0.60, 0.08, 11800),
    ("full-stack-engineer", "nextjs", 0.58, 0.18, 11800),
    ("full-stack-engineer", "html", 0.80, 0.01, 11800),
    ("full-stack-engineer", "css", 0.75, 0.01, 11800),
    ("full-stack-engineer", "docker", 0.45, 0.10, 11800),
    ("full-stack-engineer", "rest-apis", 0.72, 0.05, 11800),
    ("full-stack-engineer", "git", 0.75, 0.02, 11800),

    # Frontend Engineer
    ("frontend-engineer", "html", 0.85, 0.01, 9500),
    ("frontend-engineer", "javascript", 0.82, 0.02, 9500),
    ("frontend-engineer", "css", 0.82, 0.01, 9500),
    ("frontend-engineer", "react", 0.76, 0.08, 9500),
    ("frontend-engineer", "typescript", 0.74, 0.14, 9500),
    ("frontend-engineer", "nextjs", 0.65, 0.20, 9500),
    ("frontend-engineer", "tailwindcss", 0.60, 0.16, 9500),
    ("frontend-engineer", "git", 0.72, 0.03, 9500),
    ("frontend-engineer", "rest-apis", 0.65, 0.05, 9500),

    # Cloud/DevOps Engineer
    ("cloud-devops-engineer", "git", 0.85, 0.02, 8200),
    ("cloud-devops-engineer", "docker", 0.82, 0.10, 8200),
    ("cloud-devops-engineer", "aws", 0.80, 0.11, 8200),
    ("cloud-devops-engineer", "kubernetes", 0.78, 0.15, 8200),
    ("cloud-devops-engineer", "github-actions", 0.68, 0.14, 8200),
    ("cloud-devops-engineer", "docker-compose", 0.62, 0.08, 8200),
    ("cloud-devops-engineer", "python", 0.58, 0.07, 8200),
    ("cloud-devops-engineer", "go", 0.52, 0.12, 8200),

    # AI/ML Engineer
    ("ai-ml-engineer", "python", 0.90, 0.09, 7400),
    ("ai-ml-engineer", "pytorch", 0.75, 0.18, 7400),
    ("ai-ml-engineer", "git", 0.74, 0.03, 7400),
    ("ai-ml-engineer", "pandas", 0.72, 0.08, 7400),
    ("ai-ml-engineer", "sql", 0.65, 0.04, 7400),
    ("ai-ml-engineer", "pgvector", 0.62, 0.25, 7400),
    ("ai-ml-engineer", "docker", 0.55, 0.11, 7400),
    ("ai-ml-engineer", "fastapi", 0.52, 0.14, 7400),
]


def upgrade() -> None:
    # 1. Create job_roles table
    op.create_table(
        'job_roles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('title', sa.String(length=128), unique=True, nullable=False),
        sa.Column('slug', sa.String(length=128), unique=True, nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_job_roles_title'), 'job_roles', ['title'], unique=True)
    op.create_index(op.f('ix_job_roles_slug'), 'job_roles', ['slug'], unique=True)
    op.create_index(op.f('ix_job_roles_category'), 'job_roles', ['category'], unique=False)

    # 2. Create skill_demand table
    op.create_table(
        'skill_demand',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('role_id', UUID(as_uuid=True), sa.ForeignKey('job_roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('location', sa.String(length=64), server_default='India', nullable=False),
        sa.Column('sample_size', sa.Integer(), server_default='10000', nullable=False),
        sa.Column('demand_score', sa.Float(), nullable=False),
        sa.Column('growth_rate', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('data_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('role_id', 'skill_id', 'location', name='uq_skill_demand_role_skill_loc'),
        sa.CheckConstraint('demand_score >= 0.0 AND demand_score <= 1.0', name='chk_demand_score_range'),
    )
    op.create_index(op.f('ix_skill_demand_role_id'), 'skill_demand', ['role_id'], unique=False)
    op.create_index(op.f('ix_skill_demand_skill_id'), 'skill_demand', ['skill_id'], unique=False)
    op.create_index(op.f('ix_skill_demand_demand_score'), 'skill_demand', ['demand_score'], unique=False)
    op.create_index(op.f('ix_skill_demand_role_skill'), 'skill_demand', ['role_id', 'skill_id'], unique=False)

    # 3. Seed canonical roles
    conn = op.get_bind()
    role_id_map = {}
    for r in CANONICAL_ROLES:
        conn.execute(
            sa.text(
                "INSERT INTO job_roles (id, title, slug, category, description, created_at, updated_at) "
                "VALUES (:id, :title, :slug, :category, :description, now(), now()) "
                "ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title, category = EXCLUDED.category, description = EXCLUDED.description "
                "RETURNING id;"
            ),
            r,
        )
        role_id_map[r["slug"]] = r["id"]

    # 4. Fetch canonical skill IDs from skills table
    skill_rows = conn.execute(sa.text("SELECT id, slug FROM skills;")).fetchall()
    skill_slug_map = {row[1]: row[0] for row in skill_rows}

    # 5. Seed deterministic industry skill demand
    for role_slug, skill_slug, demand_score, growth_rate, sample_size in CANONICAL_DEMAND:
        r_id = role_id_map.get(role_slug)
        s_id = skill_slug_map.get(skill_slug)
        if not r_id or not s_id:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO skill_demand (id, role_id, skill_id, location, sample_size, demand_score, growth_rate, data_updated_at, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :role_id, :skill_id, 'India', :sample_size, :demand_score, :growth_rate, now(), now(), now()) "
                "ON CONFLICT (role_id, skill_id, location) DO UPDATE SET "
                "demand_score = EXCLUDED.demand_score, "
                "growth_rate = EXCLUDED.growth_rate, "
                "sample_size = EXCLUDED.sample_size, "
                "updated_at = now();"
            ),
            {
                "role_id": r_id,
                "skill_id": s_id,
                "sample_size": sample_size,
                "demand_score": demand_score,
                "growth_rate": growth_rate,
            },
        )


def downgrade() -> None:
    op.drop_index(op.f('ix_skill_demand_role_skill'), table_name='skill_demand')
    op.drop_index(op.f('ix_skill_demand_demand_score'), table_name='skill_demand')
    op.drop_index(op.f('ix_skill_demand_skill_id'), table_name='skill_demand')
    op.drop_index(op.f('ix_skill_demand_role_id'), table_name='skill_demand')
    op.drop_table('skill_demand')

    op.drop_index(op.f('ix_job_roles_category'), table_name='job_roles')
    op.drop_index(op.f('ix_job_roles_slug'), table_name='job_roles')
    op.drop_index(op.f('ix_job_roles_title'), table_name='job_roles')
    op.drop_table('job_roles')
