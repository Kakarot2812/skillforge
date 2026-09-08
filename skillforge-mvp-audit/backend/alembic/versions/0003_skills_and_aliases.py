"""create skill_aliases and user_claimed_skills tables and seed canonical taxonomy

Revision ID: 0003_create_skill_aliases_and_claimed_skills
Revises: 0002_create_resumes_table
Create Date: 2026-09-01 15:30:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = '0003_skills_and_aliases'
down_revision: Union[str, None] = '0002_create_resumes_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Canonical taxonomy seed data from docs/data/SKILL_TAXONOMY.md
SEED_SKILLS = [
    {"name": "Python", "slug": "python", "category": "Languages", "description": "Interpreted high-level dynamic language."},
    {"name": "TypeScript", "slug": "typescript", "category": "Languages", "description": "Strongly typed superset of JavaScript."},
    {"name": "JavaScript", "slug": "javascript", "category": "Languages", "description": "High-level scripting language for the web."},
    {"name": "Java", "slug": "java", "category": "Languages", "description": "Object-oriented class-based language."},
    {"name": "Go", "slug": "go", "category": "Languages", "description": "Statically typed concurrent programming language."},
    {"name": "SQL", "slug": "sql", "category": "Languages", "description": "Standard declarative database query language."},
    {"name": "C++", "slug": "cpp", "category": "Languages", "description": "General-purpose systems programming language."},
    {"name": "C#", "slug": "csharp", "category": "Languages", "description": "Modern, object-oriented language for .NET."},
    {"name": "React", "slug": "react", "category": "Frontend", "description": "Component-based declarative UI library."},
    {"name": "Next.js", "slug": "nextjs", "category": "Frontend", "description": "Full-stack React framework with SSR and App Router."},
    {"name": "Tailwind CSS", "slug": "tailwindcss", "category": "Frontend", "description": "Utility-first CSS framework."},
    {"name": "HTML", "slug": "html", "category": "Frontend", "description": "Standard markup language for documents designed to be displayed in a web browser."},
    {"name": "CSS", "slug": "css", "category": "Frontend", "description": "Style sheet language used for describing the presentation of a document."},
    {"name": "FastAPI", "slug": "fastapi", "category": "Backend", "description": "High-performance Python web framework."},
    {"name": "Node.js", "slug": "nodejs", "category": "Backend", "description": "JavaScript runtime environment."},
    {"name": "Spring Boot", "slug": "spring-boot", "category": "Backend", "description": "Java-based framework for microservices."},
    {"name": "PostgreSQL", "slug": "postgresql", "category": "Databases", "description": "Advanced open-source relational database."},
    {"name": "MongoDB", "slug": "mongodb", "category": "Databases", "description": "Document-oriented NoSQL database."},
    {"name": "Redis", "slug": "redis", "category": "Databases", "description": "In-memory data structure store and cache."},
    {"name": "pgvector", "slug": "pgvector", "category": "Databases", "description": "Vector similarity search extension for PostgreSQL."},
    {"name": "Docker", "slug": "docker", "category": "DevOps & Cloud", "description": "Platform for containerizing applications."},
    {"name": "Kubernetes", "slug": "kubernetes", "category": "DevOps & Cloud", "description": "Container orchestration and management system."},
    {"name": "AWS", "slug": "aws", "category": "DevOps & Cloud", "description": "Amazon Web Services cloud computing platform."},
    {"name": "GitHub Actions", "slug": "github-actions", "category": "DevOps & Cloud", "description": "Continuous integration and delivery platform."},
    {"name": "Git", "slug": "git", "category": "Systems", "description": "Distributed version control system."},
    {"name": "REST APIs", "slug": "rest-apis", "category": "Systems", "description": "Representational State Transfer web services."},
    {"name": "Pytest", "slug": "pytest", "category": "Systems", "description": "Python testing framework."},
    {"name": "Docker Compose", "slug": "docker-compose", "category": "DevOps & Cloud", "description": "Tool for defining and running multi-container Docker applications."},
    {"name": "PyTorch", "slug": "pytorch", "category": "AI & ML", "description": "Machine learning framework for deep neural networks."},
    {"name": "Pandas", "slug": "pandas", "category": "AI & ML", "description": "Data analysis and manipulation library for Python."},
]

SEED_ALIASES = {
    "Python": ["py", "python3", "cpython"],
    "TypeScript": ["ts", "type-script"],
    "JavaScript": ["js", "es6", "ecmascript"],
    "Java": ["jdk", "java8", "java17", "jvm"],
    "Go": ["golang", "go-lang"],
    "SQL": ["structured-query-language", "ansi-sql"],
    "C++": ["c-plus-plus", "cplusplus"],
    "C#": ["c-sharp", "csharp", "dotnet"],
    "React": ["reactjs", "react.js", "react-dom", "react js"],
    "Next.js": ["nextjs", "next.js", "next13", "next14", "next js"],
    "Tailwind CSS": ["tailwind", "tailwind-css", "tailwindcss"],
    "HTML": ["html5"],
    "CSS": ["css3"],
    "FastAPI": ["fast-api", "fastapi-framework"],
    "Node.js": ["node", "node.js", "nodejs"],
    "Spring Boot": ["springboot", "spring-framework", "spring"],
    "PostgreSQL": ["postgres", "psql", "pg", "postgre sql", "postgresql database"],
    "MongoDB": ["mongo", "documentdb"],
    "Redis": ["redis-cache", "key-value-store"],
    "pgvector": ["vector-extension", "postgres-vector"],
    "Docker": ["dockerfile", "containers"],
    "Kubernetes": ["k8s", "kube", "kubectl"],
    "AWS": ["amazon-web-services", "aws-cloud", "amazon aws"],
    "GitHub Actions": ["gh-actions", "github-ci"],
    "Git": ["git-scm", "version-control"],
    "REST APIs": ["restful", "rest-api", "http-api", "rest"],
    "Pytest": ["py-test", "pytest-runner"],
    "Docker Compose": ["compose", "docker-compose-yml"],
    "PyTorch": ["torch", "torchvision"],
    "Pandas": ["pandas-dataframe", "pd"],
}


def upgrade() -> None:
    # 1. Create skill_aliases table
    op.create_table(
        'skill_aliases',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('alias', sa.String(length=128), nullable=False),
        sa.Column('normalized_alias', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(op.f('ix_skill_aliases_skill_id'), 'skill_aliases', ['skill_id'], unique=False)
    op.create_index(op.f('ix_skill_aliases_normalized_alias'), 'skill_aliases', ['normalized_alias'], unique=False)

    # 2. Create user_claimed_skills table
    op.create_table(
        'user_claimed_skills',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        sa.Column('skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('resume_id', UUID(as_uuid=True), sa.ForeignKey('resumes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source', sa.String(length=32), server_default='resume', nullable=False),
        sa.Column('raw_mention', sa.String(length=128), nullable=True),
        sa.Column('confidence_score', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_id', 'skill_id', name='uq_user_claimed_skills_user_skill'),
    )
    op.create_index(op.f('ix_user_claimed_skills_user_id'), 'user_claimed_skills', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_claimed_skills_skill_id'), 'user_claimed_skills', ['skill_id'], unique=False)
    op.create_index(op.f('ix_user_claimed_skills_resume_id'), 'user_claimed_skills', ['resume_id'], unique=False)

    # 3. Seed canonical skills and aliases
    bind = op.get_bind()
    for skill_data in SEED_SKILLS:
        skill_id = uuid.uuid4()
        bind.execute(
            sa.text(
                "INSERT INTO skills (id, name, slug, category, description, created_at) "
                "VALUES (:id, :name, :slug, :category, :description, now()) "
                "ON CONFLICT (slug) DO NOTHING;"
            ),
            {"id": skill_id, "name": skill_data["name"], "slug": skill_data["slug"], "category": skill_data["category"], "description": skill_data["description"]}
        )

        # Retrieve actual skill_id in case it existed
        res = bind.execute(sa.text("SELECT id FROM skills WHERE slug = :slug;"), {"slug": skill_data["slug"]}).fetchone()
        if res:
            actual_id = res[0]
            aliases = SEED_ALIASES.get(skill_data["name"], [])
            for alias in aliases:
                norm_alias = alias.lower().replace(" ", "").replace("-", "").replace(".", "")
                bind.execute(
                    sa.text(
                        "INSERT INTO skill_aliases (id, skill_id, alias, normalized_alias, created_at) "
                        "VALUES (:id, :skill_id, :alias, :norm_alias, now());"
                    ),
                    {"id": uuid.uuid4(), "skill_id": actual_id, "alias": alias, "norm_alias": norm_alias}
                )


def downgrade() -> None:
    op.drop_table('user_claimed_skills')
    op.drop_table('skill_aliases')
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM skills;"))
