"""create roadmap and resources tables and seed canonical dependencies and resources

Revision ID: 0017_roadmap_and_resources
Revises: 0016_rag_evidence
Create Date: 2026-09-11 10:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = '0017_roadmap_and_resources'
down_revision: Union[str, None] = '0016_rag_evidence'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Seed skill dependency pairs (prerequisite_slug -> skill_slug, dependency_type, description)
SEED_DEPENDENCIES = [
    # Python ecosystem
    ("python", "fastapi", "HARD", "Python language fundamentals are required before building FastAPI applications."),
    ("python", "pytest", "HARD", "Python fundamentals are required for writing Pytest test suites."),
    ("python", "pandas", "HARD", "Python fundamentals are required for data analysis with Pandas."),
    ("pandas", "pytorch", "HARD", "Data preparation with Pandas is foundational for PyTorch ML workflows."),
    ("python", "pytorch", "HARD", "Python is the primary interface for PyTorch models."),
    ("rest-apis", "fastapi", "RECOMMENDED", "Understanding RESTful architecture accelerates FastAPI API design."),
    
    # JavaScript / TypeScript / Web ecosystem
    ("html", "css", "HARD", "HTML structure is required before applying CSS styling."),
    ("html", "react", "HARD", "HTML document semantics are foundational to JSX in React."),
    ("css", "react", "HARD", "CSS knowledge is required to style React web components."),
    ("javascript", "react", "HARD", "JavaScript syntax and asynchronous concepts are required for React."),
    ("javascript", "typescript", "HARD", "JavaScript proficiency is the foundation for TypeScript's type system."),
    ("javascript", "nodejs", "HARD", "JavaScript runtime concepts are required for Node.js backend development."),
    ("react", "nextjs", "HARD", "React component architecture is the core foundation for Next.js."),
    ("typescript", "nextjs", "RECOMMENDED", "TypeScript typing provides type-safe server components in Next.js."),
    ("css", "tailwindcss", "HARD", "Understanding CSS cascade and layout models is required for Tailwind CSS utilities."),
    
    # Systems & Java
    ("java", "spring-boot", "HARD", "Object-oriented Java fundamentals are required for Spring Boot microservices."),
    
    # Databases
    ("sql", "postgresql", "HARD", "Standard SQL declarative queries are foundational for PostgreSQL."),
    ("postgresql", "pgvector", "HARD", "PostgreSQL relational knowledge is required to use the pgvector extension."),
    
    # DevOps & Infrastructure
    ("git", "github-actions", "HARD", "Git version control and commit hooks are foundational for GitHub Actions automation."),
    ("docker", "docker-compose", "HARD", "Container fundamentals are required before multi-container Docker Compose."),
    ("docker", "kubernetes", "HARD", "Container packaging is the prerequisite unit for Kubernetes orchestration."),
    ("docker-compose", "kubernetes", "RECOMMENDED", "Local multi-container orchestration prepares for Kubernetes pod architecture."),
]

# Seed approved resources for canonical skills
SEED_RESOURCES = [
    # Python
    ("python", "Official Python Tutorial", "https://docs.python.org/3/tutorial/", "OFFICIAL_DOCS", "Python Software Foundation", "BEGINNER", 240),
    ("python", "Real Python: Python Basics", "https://realpython.com/", "TUTORIAL", "Real Python", "BEGINNER", 180),
    # FastAPI
    ("fastapi", "FastAPI Official Tutorial - User Guide", "https://fastapi.tiangolo.com/tutorial/", "OFFICIAL_DOCS", "FastAPI Docs", "INTERMEDIATE", 180),
    ("fastapi", "Building High-Performance APIs with FastAPI", "https://fastapi.tiangolo.com/advanced/", "GUIDE", "FastAPI Docs", "ADVANCED", 240),
    # React
    ("react", "React Quick Start: Thinking in React", "https://react.dev/learn", "OFFICIAL_DOCS", "React Core Team", "BEGINNER", 180),
    ("react", "Managing State in React Applications", "https://react.dev/learn/managing-state", "GUIDE", "React Core Team", "INTERMEDIATE", 240),
    # Next.js
    ("nextjs", "Next.js App Router Documentation", "https://nextjs.org/docs", "OFFICIAL_DOCS", "Vercel", "INTERMEDIATE", 240),
    ("nextjs", "Full Stack Next.js Foundations", "https://nextjs.org/learn", "TUTORIAL", "Vercel", "BEGINNER", 180),
    # TypeScript
    ("typescript", "TypeScript for JavaScript Programmers", "https://www.typescriptlang.org/docs/handbook/typescript-in-5-minutes.html", "OFFICIAL_DOCS", "Microsoft", "INTERMEDIATE", 120),
    # JavaScript
    ("javascript", "MDN JavaScript First Steps", "https://developer.mozilla.org/en-US/docs/Learn/JavaScript/First_steps", "OFFICIAL_DOCS", "Mozilla", "BEGINNER", 180),
    # HTML
    ("html", "MDN Introduction to HTML", "https://developer.mozilla.org/en-US/docs/Learn/HTML/Introduction_to_HTML", "OFFICIAL_DOCS", "Mozilla", "BEGINNER", 120),
    # CSS
    ("css", "MDN CSS First Steps & Layout", "https://developer.mozilla.org/en-US/docs/Learn/CSS/First_steps", "OFFICIAL_DOCS", "Mozilla", "BEGINNER", 180),
    # Tailwind CSS
    ("tailwindcss", "Tailwind CSS Installation & Core Concepts", "https://tailwindcss.com/docs/utility-first", "OFFICIAL_DOCS", "Tailwind Labs", "BEGINNER", 90),
    # Docker
    ("docker", "Docker Getting Started Guide", "https://docs.docker.com/get-started/", "OFFICIAL_DOCS", "Docker Inc.", "BEGINNER", 180),
    ("docker", "Dockerfile Best Practices", "https://docs.docker.com/develop/develop-images/dockerfile_best-practices/", "GUIDE", "Docker Inc.", "INTERMEDIATE", 120),
    # Docker Compose
    ("docker-compose", "Docker Compose Specification & Overview", "https://docs.docker.com/compose/", "OFFICIAL_DOCS", "Docker Inc.", "INTERMEDIATE", 120),
    # Kubernetes
    ("kubernetes", "Kubernetes Basics Interactive Tutorial", "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "OFFICIAL_DOCS", "Cloud Native Computing Foundation", "INTERMEDIATE", 240),
    # PostgreSQL
    ("postgresql", "PostgreSQL Official Tutorial", "https://www.postgresql.org/docs/current/tutorial.html", "OFFICIAL_DOCS", "PostgreSQL Global Development Group", "BEGINNER", 240),
    ("postgresql", "PostgreSQL Indexing and Query Performance", "https://www.postgresql.org/docs/current/performance-tips.html", "GUIDE", "PostgreSQL Global Development Group", "ADVANCED", 180),
    # pgvector
    ("pgvector", "pgvector Documentation & Vector Similarity Operations", "https://github.com/pgvector/pgvector", "OFFICIAL_DOCS", "pgvector Community", "INTERMEDIATE", 120),
    # Redis
    ("redis", "Redis Quick Start & Data Structures", "https://redis.io/docs/getting-started/", "OFFICIAL_DOCS", "Redis Ltd.", "BEGINNER", 120),
    # MongoDB
    ("mongodb", "MongoDB Manual: Introduction & CRUD", "https://www.mongodb.com/docs/manual/introduction/", "OFFICIAL_DOCS", "MongoDB Inc.", "BEGINNER", 180),
    # SQL
    ("sql", "W3Schools SQL Tutorial & Reference", "https://www.w3schools.com/sql/", "TUTORIAL", "W3Schools", "BEGINNER", 150),
    # Git
    ("git", "Pro Git Book - Version Control Fundamentals", "https://git-scm.com/book/en/v2", "BOOK", "Scott Chacon & Ben Straub", "BEGINNER", 240),
    # GitHub Actions
    ("github-actions", "GitHub Actions Quickstart & Workflow Syntax", "https://docs.github.com/en/actions/quickstart", "OFFICIAL_DOCS", "GitHub", "BEGINNER", 120),
    # Pytest
    ("pytest", "Pytest Official Getting Started Guide", "https://docs.pytest.org/en/stable/getting-started.html", "OFFICIAL_DOCS", "Pytest Community", "BEGINNER", 120),
    # REST APIs
    ("rest-apis", "RESTful API Architectural Guidelines", "https://restfulapi.net/", "GUIDE", "REST API Tutorial", "BEGINNER", 120),
    # PyTorch
    ("pytorch", "PyTorch Deep Learning with PyTorch: A 60 Minute Blitz", "https://pytorch.org/tutorials/beginner/deep_learning_60min_blitz.html", "OFFICIAL_DOCS", "PyTorch Foundation", "INTERMEDIATE", 180),
    # Pandas
    ("pandas", "Pandas Getting Started Tutorials", "https://pandas.pydata.org/docs/getting_started/index.html", "OFFICIAL_DOCS", "Pandas Development Team", "BEGINNER", 180),
    # Node.js
    ("nodejs", "Node.js Introduction & Event Loop", "https://nodejs.org/en/learn/getting-started/introduction-to-nodejs", "OFFICIAL_DOCS", "OpenJS Foundation", "BEGINNER", 150),
    # Java
    ("java", "Oracle Java Tutorials: Learn Java Basics", "https://dev.java/learn/", "OFFICIAL_DOCS", "Oracle", "BEGINNER", 300),
    # Spring Boot
    ("spring-boot", "Building an Application with Spring Boot", "https://spring.io/guides/gs/spring-boot/", "TUTORIAL", "VMware Tanzu", "INTERMEDIATE", 180),
    # Go
    ("go", "Go Tutorial: Get Started with Go", "https://go.dev/doc/tutorial/getting-started", "OFFICIAL_DOCS", "Google Go Team", "BEGINNER", 150),
    # AWS
    ("aws", "AWS Cloud Practitioner & Getting Started", "https://aws.amazon.com/getting-started/", "OFFICIAL_DOCS", "Amazon Web Services", "BEGINNER", 240),
    # C++
    ("cpp", "cppreference.com Core Language Reference", "https://en.cppreference.com/w/", "OFFICIAL_DOCS", "cppreference Community", "INTERMEDIATE", 240),
    # C#
    ("csharp", "Microsoft Learn C# Guide", "https://learn.microsoft.com/en-us/dotnet/csharp/", "OFFICIAL_DOCS", "Microsoft", "BEGINNER", 240),
]

# Seed approved practical projects
SEED_PROJECTS = [
    {
        "skill_slug": "fastapi",
        "role_slug": "backend-engineer",
        "title": "Production REST API with Dependency Injection and Pydantic",
        "description": "Develop a production-grade FastAPI service implementing CRUD operations, connection-pooled PostgreSQL storage, and structured JSON schemas.",
        "difficulty": "INTERMEDIATE",
        "deliverables": ["main.py", "requirements.txt", "Dockerfile", "tests/test_api.py"],
        "verification_criteria": ["fastapi_dependency_injection", "pydantic_v2_models", "status_code_testing"],
        "estimated_hours": 12,
    },
    {
        "skill_slug": "docker",
        "role_slug": "backend-engineer",
        "title": "Multi-Stage Docker Containerization",
        "description": "Containerize a web service using multi-stage builds to minimize image size and run under an unprivileged user.",
        "difficulty": "BEGINNER",
        "deliverables": ["Dockerfile", ".dockerignore"],
        "verification_criteria": ["multi_stage_build", "non_root_user", "explicit_workdir"],
        "estimated_hours": 6,
    },
    {
        "skill_slug": "docker-compose",
        "role_slug": "backend-engineer",
        "title": "Multi-Service Orchestration with PostgreSQL and Redis",
        "description": "Compose an API service, PostgreSQL database with persistent volume, and Redis cache with health checks and network isolation.",
        "difficulty": "INTERMEDIATE",
        "deliverables": ["docker-compose.yml", ".env.example"],
        "verification_criteria": ["named_volumes", "service_healthchecks", "isolated_networks"],
        "estimated_hours": 8,
    },
    {
        "skill_slug": "postgresql",
        "role_slug": "backend-engineer",
        "title": "Relational Schema Design & Alembic Migrations",
        "description": "Design an indexed PostgreSQL schema with foreign keys, check constraints, and an automated Alembic migration chain.",
        "difficulty": "INTERMEDIATE",
        "deliverables": ["models.py", "alembic/versions/0001_initial.py", "alembic.ini"],
        "verification_criteria": ["foreign_key_constraints", "composite_indexes", "reversible_migrations"],
        "estimated_hours": 10,
    },
    {
        "skill_slug": "github-actions",
        "role_slug": "cloud-devops-engineer",
        "title": "Automated CI Pipeline with Pytest and Linting",
        "description": "Build a GitHub Actions workflow that runs automated unit tests with coverage, Ruff linting, and Docker build checks on pull requests.",
        "difficulty": "BEGINNER",
        "deliverables": [".github/workflows/ci.yml"],
        "verification_criteria": ["pr_branch_trigger", "python_test_step", "coverage_reporting"],
        "estimated_hours": 6,
    },
    {
        "skill_slug": "react",
        "role_slug": "frontend-engineer",
        "title": "Evidence Dashboard Component with State Management",
        "description": "Build an accessible, responsive dashboard UI consuming REST API endpoints with optimistic state updates and error boundary fallbacks.",
        "difficulty": "BEGINNER",
        "deliverables": ["package.json", "src/App.tsx", "src/components/Dashboard.tsx"],
        "verification_criteria": ["typed_props", "error_boundary", "accessible_aria_roles"],
        "estimated_hours": 10,
    },
    {
        "skill_slug": "nextjs",
        "role_slug": "full-stack-engineer",
        "title": "Full-Stack Server Component Web Application",
        "description": "Build an end-to-end web application using Next.js App Router, Server Actions, and Tailwind CSS.",
        "difficulty": "INTERMEDIATE",
        "deliverables": ["package.json", "app/page.tsx", "app/layout.tsx", "tailwind.config.js"],
        "verification_criteria": ["app_router_layout", "server_actions", "responsive_grid"],
        "estimated_hours": 14,
    },
    {
        "skill_slug": "pytorch",
        "role_slug": "ai-ml-engineer",
        "title": "Vector Embedding & Similarity Classification Pipeline",
        "description": "Train or fine-tune a neural embedding pipeline, export embeddings, and evaluate cosine similarity metrics.",
        "difficulty": "INTERMEDIATE",
        "deliverables": ["model.py", "dataset.py", "evaluate.py", "requirements.txt"],
        "verification_criteria": ["torch_nn_module", "batch_evaluation", "cosine_similarity_metric"],
        "estimated_hours": 16,
    },
]


def upgrade() -> None:
    # 1. Skill Dependencies Table
    op.create_table(
        'skill_dependencies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('prerequisite_skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dependency_type', sa.String(length=32), nullable=False, server_default='HARD'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('skill_id', 'prerequisite_skill_id', name='uq_skill_dependencies_skill_prereq'),
        sa.CheckConstraint('skill_id != prerequisite_skill_id', name='chk_skill_dependencies_no_self_loop'),
        sa.CheckConstraint("dependency_type IN ('HARD', 'RECOMMENDED')", name='chk_skill_dependencies_type'),
    )
    op.create_index(op.f('ix_skill_dependencies_skill_id'), 'skill_dependencies', ['skill_id'], unique=False)
    op.create_index(op.f('ix_skill_dependencies_prereq_id'), 'skill_dependencies', ['prerequisite_skill_id'], unique=False)

    # 2. Approved Resources Table
    op.create_table(
        'approved_resources',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=1024), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=False),
        sa.Column('provider', sa.String(length=128), nullable=False),
        sa.Column('difficulty', sa.String(length=32), nullable=False),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True),
        sa.Column('is_approved', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('approval_source', sa.String(length=64), nullable=False, server_default='CURATED_SEED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_approved_resources_skill_id'), 'approved_resources', ['skill_id'], unique=False)
    op.create_index(op.f('ix_approved_resources_resource_type'), 'approved_resources', ['resource_type'], unique=False)

    # 3. Approved Projects Table
    op.create_table(
        'approved_projects',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', UUID(as_uuid=True), sa.ForeignKey('job_roles.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('difficulty', sa.String(length=32), nullable=False),
        sa.Column('deliverables', JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('verification_criteria', JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('estimated_hours', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_approved_projects_skill_id'), 'approved_projects', ['skill_id'], unique=False)
    op.create_index(op.f('ix_approved_projects_role_id'), 'approved_projects', ['role_id'], unique=False)

    # 4. Candidate Roadmaps Table (persisted for authenticated users only)
    op.create_table(
        'candidate_roadmaps',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', UUID(as_uuid=True), sa.ForeignKey('job_roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_role_title', sa.String(length=128), nullable=False),
        sa.Column('location', sa.String(length=64), nullable=False, server_default='India'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('roadmap_version', sa.String(length=16), nullable=False, server_default='v1'),
        sa.Column('summary_metadata', JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('ACTIVE', 'COMPLETED', 'ARCHIVED')", name='chk_candidate_roadmaps_status'),
    )
    op.create_index(op.f('ix_candidate_roadmaps_user_id'), 'candidate_roadmaps', ['user_id'], unique=False)
    op.create_index(op.f('ix_candidate_roadmaps_role_id'), 'candidate_roadmaps', ['role_id'], unique=False)
    op.create_index('ix_candidate_roadmaps_user_role', 'candidate_roadmaps', ['user_id', 'role_id'], unique=False)

    # 5. Roadmap Milestones Table
    op.create_table(
        'roadmap_milestones',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('roadmap_id', UUID(as_uuid=True), sa.ForeignKey('candidate_roadmaps.id', ondelete='CASCADE'), nullable=False),
        sa.Column('skill_id', UUID(as_uuid=True), sa.ForeignKey('skills.id', ondelete='CASCADE'), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='NOT_STARTED'),
        sa.Column('gap_status', sa.String(length=32), nullable=False),
        sa.Column('priority_score', sa.Float(), nullable=True),
        sa.Column('priority_level', sa.String(length=32), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('project_id', UUID(as_uuid=True), sa.ForeignKey('approved_projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('milestone_metadata', JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('roadmap_id', 'order_index', name='uq_roadmap_milestones_order'),
        sa.UniqueConstraint('roadmap_id', 'skill_id', name='uq_roadmap_milestones_skill'),
        sa.CheckConstraint("status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'VERIFIED')", name='chk_roadmap_milestones_status'),
        sa.CheckConstraint('order_index >= 1', name='chk_roadmap_milestones_order_positive'),
    )
    op.create_index(op.f('ix_roadmap_milestones_roadmap_id'), 'roadmap_milestones', ['roadmap_id'], unique=False)
    op.create_index(op.f('ix_roadmap_milestones_skill_id'), 'roadmap_milestones', ['skill_id'], unique=False)

    # 6. Seed Data Execution
    bind = op.get_bind()

    # Load canonical skills into a slug -> id mapping
    skill_rows = bind.execute(sa.text("SELECT id, slug FROM skills")).fetchall()
    skill_slug_map = {row[1]: row[0] for row in skill_rows}

    # Load canonical job roles into a slug -> id mapping
    role_rows = bind.execute(sa.text("SELECT id, slug FROM job_roles")).fetchall()
    role_slug_map = {row[1]: row[0] for row in role_rows}

    # Seed skill dependencies
    for prereq_slug, skill_slug, dep_type, desc in SEED_DEPENDENCIES:
        p_id = skill_slug_map.get(prereq_slug)
        s_id = skill_slug_map.get(skill_slug)
        if p_id and s_id:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO skill_dependencies (id, skill_id, prerequisite_skill_id, dependency_type, description, created_at)
                    VALUES (:id, :skill_id, :prereq_id, :dep_type, :desc, now())
                    ON CONFLICT (skill_id, prerequisite_skill_id) DO NOTHING
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "skill_id": s_id,
                    "prereq_id": p_id,
                    "dep_type": dep_type,
                    "desc": desc,
                }
            )

    # Seed approved resources
    for skill_slug, title, url, r_type, provider, diff, est_min in SEED_RESOURCES:
        s_id = skill_slug_map.get(skill_slug)
        if s_id:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO approved_resources (id, skill_id, title, url, resource_type, provider, difficulty, estimated_minutes, is_approved, approval_source, created_at, updated_at)
                    VALUES (:id, :skill_id, :title, :url, :resource_type, :provider, :difficulty, :estimated_minutes, true, 'CURATED_SEED', now(), now())
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "skill_id": s_id,
                    "title": title,
                    "url": url,
                    "resource_type": r_type,
                    "provider": provider,
                    "difficulty": diff,
                    "estimated_minutes": est_min,
                }
            )

    # Seed approved projects
    import json
    for proj in SEED_PROJECTS:
        s_id = skill_slug_map.get(proj["skill_slug"])
        r_id = role_slug_map.get(proj["role_slug"])
        if s_id:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO approved_projects (id, skill_id, role_id, title, description, difficulty, deliverables, verification_criteria, estimated_hours, created_at, updated_at)
                    VALUES (:id, :skill_id, :role_id, :title, :description, :difficulty, :deliverables, :verification_criteria, :estimated_hours, now(), now())
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "skill_id": s_id,
                    "role_id": r_id,
                    "title": proj["title"],
                    "description": proj["description"],
                    "difficulty": proj["difficulty"],
                    "deliverables": json.dumps(proj["deliverables"]),
                    "verification_criteria": json.dumps(proj["verification_criteria"]),
                    "estimated_hours": proj["estimated_hours"],
                }
            )


def downgrade() -> None:
    op.drop_table('roadmap_milestones')
    op.drop_table('candidate_roadmaps')
    op.drop_table('approved_projects')
    op.drop_table('approved_resources')
    op.drop_table('skill_dependencies')
