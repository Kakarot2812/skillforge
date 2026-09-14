"""
Authoritative Project Provenance Registry & Cryptographic Fingerprinting.
Checkpoint C7-E.

Invariant:
A live ApprovedProject row is authoritative iff:
SHA256(CanonicalJSON(project fields + canonical skill/role identifiers)) in CANONICAL_SEED_PROJECT_HASHES

Strictly rejects all fixture rows, uncurated projects, and modified copies.
Never relies on project UUID, timestamps, title-alone matching, or LLM judgment.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple


# The exact 8 canonical seed practical project specifications from migration 0017:
# alembic/versions/0017_roadmap_and_resources.py
CANONICAL_SEED_PROJECT_SPECS: Tuple[Dict[str, Any], ...] = (
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
)


def compute_canonical_project_fingerprint(
    skill_slug: str,
    role_slug: Optional[str],
    title: str,
    description: str,
    difficulty: str,
    deliverables: Sequence[str],
    verification_criteria: Sequence[str],
    estimated_hours: Optional[int],
) -> str:
    """
    Computes deterministic SHA-256 canonical fingerprint over normalized project fields.
    Strictly excludes database UUIDs, primary keys, and timestamps.
    """
    norm_skill_slug = (skill_slug or "").strip().lower()
    norm_role_slug = (role_slug or "").strip().lower() if role_slug else None
    norm_title = (title or "").strip()
    norm_description = (description or "").strip()
    norm_difficulty = (difficulty or "").strip().upper()
    norm_deliverables = sorted([str(d).strip() for d in deliverables]) if deliverables else []
    norm_criteria = sorted([str(c).strip() for c in verification_criteria]) if verification_criteria else []
    norm_hours = int(estimated_hours) if estimated_hours is not None else None

    payload = {
        "deliverables": norm_deliverables,
        "description": norm_description,
        "difficulty": norm_difficulty,
        "estimated_hours": norm_hours,
        "role_slug": norm_role_slug,
        "skill_slug": norm_skill_slug,
        "title": norm_title,
        "verification_criteria": norm_criteria,
    }

    canonical_json = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )

    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


# Exactly 8 immutable SHA-256 hashes generated from the authoritative specs
CANONICAL_SEED_PROJECT_HASHES = frozenset(
    compute_canonical_project_fingerprint(
        skill_slug=spec["skill_slug"],
        role_slug=spec["role_slug"],
        title=spec["title"],
        description=spec["description"],
        difficulty=spec["difficulty"],
        deliverables=spec["deliverables"],
        verification_criteria=spec["verification_criteria"],
        estimated_hours=spec["estimated_hours"],
    )
    for spec in CANONICAL_SEED_PROJECT_SPECS
)


def is_canonical_project(
    project: Any,
    skill: Optional[Any] = None,
    role: Optional[Any] = None,
) -> bool:
    """
    Evaluates whether a database ApprovedProject instance is an authoritative curated project.
    Resolves skill and role slugs, computes the canonical fingerprint, and checks membership
    in CANONICAL_SEED_PROJECT_HASHES.
    """
    if not project:
        return False

    # Resolve skill slug
    resolved_skill = skill or getattr(project, "skill", None)
    skill_slug = getattr(resolved_skill, "slug", "") if resolved_skill else ""

    # Resolve role slug
    resolved_role = role or getattr(project, "role", None)
    role_slug = getattr(resolved_role, "slug", None) if resolved_role else None

    deliverables = getattr(project, "deliverables", None) or []
    if isinstance(deliverables, str):
        try:
            deliverables = json.loads(deliverables)
        except Exception:
            deliverables = []

    criteria = getattr(project, "verification_criteria", None) or []
    if isinstance(criteria, str):
        try:
            criteria = json.loads(criteria)
        except Exception:
            criteria = []

    fingerprint = compute_canonical_project_fingerprint(
        skill_slug=skill_slug,
        role_slug=role_slug,
        title=getattr(project, "title", ""),
        description=getattr(project, "description", ""),
        difficulty=getattr(project, "difficulty", ""),
        deliverables=deliverables,
        verification_criteria=criteria,
        estimated_hours=getattr(project, "estimated_hours", None),
    )

    return fingerprint in CANONICAL_SEED_PROJECT_HASHES
