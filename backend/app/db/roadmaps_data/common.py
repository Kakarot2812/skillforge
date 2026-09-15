"""Common helpers and constants for roadmap domain definitions."""
import uuid
from typing import Any, Dict, List, Optional

CANONICAL_ROLE_IDS = {
    "backend-engineer": uuid.UUID("9f8e7d6c-5b4a-3f2e-1d0c-9b8a7f6e5d4c"),
    "full-stack-engineer": uuid.UUID("0a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d"),
    "frontend-engineer": uuid.UUID("1b2c3d4e-5f6a-7b8c-9d0e-1f2a3b4c5d6e"),
    "cloud-devops-engineer": uuid.UUID("2c3d4e5f-6a7b-8c9d-0e1f-2a3b4c5d6e7f"),
    "ai-ml-engineer": uuid.UUID("3d4e5f6a-7b8c-9d0e-1f2a-3b4c5d6e7f8a"),
}

ROADMAP_IDS = {
    "backend-engineer": uuid.UUID("a1000000-0000-4000-8000-000000000001"),
    "full-stack-engineer": uuid.UUID("a1000000-0000-4000-8000-000000000002"),
    "frontend-engineer": uuid.UUID("a1000000-0000-4000-8000-000000000003"),
    "cloud-devops-engineer": uuid.UUID("a1000000-0000-4000-8000-000000000004"),
    "ai-ml-engineer": uuid.UUID("a1000000-0000-4000-8000-000000000005"),
    "android-developer": uuid.UUID("a1000000-0000-4000-8000-000000000006"),
    "data-engineer": uuid.UUID("a1000000-0000-4000-8000-000000000007"),
    "data-scientist": uuid.UUID("a1000000-0000-4000-8000-000000000008"),
    "cybersecurity-engineer": uuid.UUID("a1000000-0000-4000-8000-000000000009"),
    "qa-automation-engineer": uuid.UUID("a1000000-0000-4000-8000-000000000010"),
    "ios-developer": uuid.UUID("a1000000-0000-4000-8000-000000000011"),
    "ui-ux-engineer": uuid.UUID("a1000000-0000-4000-8000-000000000012"),
}


def make_problem(
    problem_id: str,
    title: str,
    difficulty: str,
    order: int,
    objective: str,
    problem_statement: str,
    requirements: List[str],
    concepts_tested: List[str],
    expected_outcome: str,
    optional_hints: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "problem_id": problem_id,
        "title": title,
        "difficulty": difficulty,
        "order": order,
        "objective": objective,
        "problem_statement": problem_statement,
        "requirements": requirements,
        "concepts_tested": concepts_tested,
        "expected_outcome": expected_outcome,
        "optional_hints": optional_hints or [],
    }


def make_skill(
    slug: str,
    name: str,
    difficulty: str,
    description: str,
    key_topics: List[str],
    role_relevance: str,
    prerequisites: List[str],
    resources: List[Dict[str, str]],
    practice_problems: List[Dict[str, Any]],
    canonical_slug: Optional[str] = None,
    practice_project: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "slug": slug,
        "name": name,
        "canonical_slug": canonical_slug,
        "difficulty": difficulty,
        "description": description,
        "key_topics": key_topics,
        "role_relevance": role_relevance,
        "practice_project": practice_project or (practice_problems[2]["title"] if len(practice_problems) >= 3 else ""),
        "prerequisites": prerequisites,
        "resources": resources,
        "practice_problems": practice_problems,
    }
