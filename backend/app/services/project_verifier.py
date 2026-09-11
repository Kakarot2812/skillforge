"""
Pure Deterministic Project Verifier for SkillForge AI.
Post-MVP Checkpoint P5-A.

Enforces:
- 100% deterministic, reproducible evaluation without LLM or AI inference.
- Zero network I/O, zero database access, zero subprocess or code execution.
- Safe path normalization, path traversal rejection, and ambiguous match handling.
- Full deterministic implementation for all 24 criteria seeded in migration 0017.
- Explicit status handling for unknown/unsupported and manual-review criteria.
- Bounded file content inspection (max 512 KB per file).
"""

import ast
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union
import yaml

from app.schemas.verification import (
    CriteriaCheckDetail,
    CriterionDetail,
    CriterionEvaluationStatus,
    DeliverableCheckDetail,
    DeliverableMatchItem,
    DeliverableMatchStatus,
    ProjectVerificationResult,
)

MAX_FILE_SIZE_BYTES = 512 * 1024  # 512 KB per file
MAX_SNIPPET_LENGTH = 256


# ---------------------------------------------------------------------------
# Path Normalization and Safety Helpers
# ---------------------------------------------------------------------------

def is_safe_repo_path(path: str) -> bool:
    """
    Validates repository file paths against directory traversal,
    null bytes, control characters, and absolute filesystem paths.
    """
    if not path or not isinstance(path, str):
        return False
    if "\0" in path or "\r" in path or "\n" in path:
        return False
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("/"):
        return False
    parts = normalized.split("/")
    if any(p in ("..", ".") for p in parts):
        return False
    return bool(normalized)


def normalize_repo_path(path: str) -> Optional[str]:
    """
    Normalizes a repository path by converting backslashes to forward slashes,
    stripping leading './' or '/', and rejecting unsafe paths.
    """
    if not is_safe_repo_path(path):
        return None
    normalized = path.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.lstrip("/")
    return normalized if normalized else None


def extract_tree_paths(tree_entries: Sequence[Union[str, Mapping[str, Any]]]) -> List[str]:
    """
    Extracts, normalizes, and filters safe repository paths from a list of strings or tree dicts.
    Returns deterministically sorted unique paths.
    """
    clean_paths: Set[str] = set()
    for entry in tree_entries:
        raw_path = ""
        if isinstance(entry, str):
            raw_path = entry
        elif isinstance(entry, Mapping) and "path" in entry:
            raw_path = str(entry["path"])
        norm = normalize_repo_path(raw_path)
        if norm:
            clean_paths.add(norm)
    return sorted(list(clean_paths))


# ---------------------------------------------------------------------------
# Pure Deliverable Verification Engine
# ---------------------------------------------------------------------------

def check_deliverables(
    tree_entries: Sequence[Union[str, Mapping[str, Any]]],
    required_deliverables: Sequence[str],
) -> DeliverableCheckDetail:
    """
    Evaluates required project deliverables against repository tree entries.

    Deliverable matching rules (Locked Correction 3):
    1. Normalize repository paths safely.
    2. Try exact normalized path match first (case-insensitive).
    3. If the required deliverable is only a filename with no directory:
       search basename matches across the tree.
    4. If exactly one basename match exists: accept it.
    5. If zero matches exist: mark missing.
    6. If multiple basename matches exist: mark ambiguous.
       Ambiguous matches do NOT automatically pass.
    7. If the required deliverable CONTAINS "/" and exact matching failed:
       DO NOT perform suffix matching. Mark MISSING.
    """
    normalized_tree = extract_tree_paths(tree_entries)
    # Map lowercase normalized tree path -> original tree path
    tree_lower_map: Dict[str, str] = {p.lower(): p for p in normalized_tree}

    # Group tree entries by lowercase basename: basename.lower() -> list of original paths
    basename_map: Dict[str, List[str]] = {}
    for path in normalized_tree:
        base = path.split("/")[-1].lower()
        basename_map.setdefault(base, []).append(path)

    matches: List[DeliverableMatchItem] = []
    passed_items: List[str] = []
    missing_items: List[str] = []
    ambiguous_items: List[str] = []

    for req in required_deliverables:
        norm_req = normalize_repo_path(req)
        if not norm_req:
            # Unsafe or invalid deliverable path
            item = DeliverableMatchItem(
                deliverable=req,
                status=DeliverableMatchStatus.MISSING,
                matched_path=None,
                candidate_paths=(),
                detail=f"Deliverable '{req}' is an invalid or unsafe repository path.",
            )
            matches.append(item)
            missing_items.append(req)
            continue

        req_lower = norm_req.lower()

        # Rule 2: Try exact normalized path match first
        if req_lower in tree_lower_map:
            actual_path = tree_lower_map[req_lower]
            item = DeliverableMatchItem(
                deliverable=req,
                status=DeliverableMatchStatus.PASSED,
                matched_path=actual_path,
                candidate_paths=(actual_path,),
                detail=f"Exact path match found at '{actual_path}'.",
            )
            matches.append(item)
            passed_items.append(req)
            continue

        # Rule 3: Deliverable is only a filename with no directory
        if "/" not in norm_req:
            candidates = basename_map.get(req_lower, [])
            if len(candidates) == 1:
                # Rule 4: Exactly one basename match exists -> accept it
                actual_path = candidates[0]
                item = DeliverableMatchItem(
                    deliverable=req,
                    status=DeliverableMatchStatus.PASSED,
                    matched_path=actual_path,
                    candidate_paths=(actual_path,),
                    detail=f"Unique basename match found at '{actual_path}'.",
                )
                matches.append(item)
                passed_items.append(req)
            elif len(candidates) > 1:
                # Rule 6: Multiple basename matches exist -> mark ambiguous (does NOT pass)
                sorted_candidates = tuple(sorted(candidates))
                item = DeliverableMatchItem(
                    deliverable=req,
                    status=DeliverableMatchStatus.AMBIGUOUS,
                    matched_path=None,
                    candidate_paths=sorted_candidates,
                    detail=(
                        f"Ambiguous deliverable: {len(sorted_candidates)} candidate files found "
                        f"({', '.join(sorted_candidates)}). Exact path disambiguation required."
                    ),
                )
                matches.append(item)
                ambiguous_items.append(req)
            else:
                # Rule 5: Zero matches exist -> mark missing
                item = DeliverableMatchItem(
                    deliverable=req,
                    status=DeliverableMatchStatus.MISSING,
                    matched_path=None,
                    candidate_paths=(),
                    detail=f"Required deliverable '{req}' was not found in repository tree.",
                )
                matches.append(item)
                missing_items.append(req)
            continue

        # Rule 4: Deliverable contains a directory (e.g. 'tests/test_api.py') and exact matching failed.
        # Suffix/contains/proximity matching is strictly prohibited. Mark MISSING.
        item = DeliverableMatchItem(
            deliverable=req,
            status=DeliverableMatchStatus.MISSING,
            matched_path=None,
            candidate_paths=(),
            detail=f"Required deliverable '{req}' was not found at exact repository path.",
        )
        matches.append(item)
        missing_items.append(req)

    total_req = len(required_deliverables)
    passed_cnt = len(passed_items)
    missing_cnt = len(missing_items)
    ambiguous_cnt = len(ambiguous_items)

    if total_req == 0:
        score = 1.0
    else:
        score = min(1.0, max(0.0, round(passed_cnt / total_req, 2)))

    return DeliverableCheckDetail(
        total_required=total_req,
        passed_count=passed_cnt,
        missing_count=missing_cnt,
        ambiguous_count=ambiguous_cnt,
        deliverables_score=score,
        required_deliverables=tuple(required_deliverables),
        passed_deliverables=tuple(passed_items),
        missing_deliverables=tuple(missing_items),
        ambiguous_deliverables=tuple(ambiguous_items),
        matches=tuple(matches),
    )


# ---------------------------------------------------------------------------
# Deterministic Criteria Rule Handlers (24 Seeded P4 Criteria)
# ---------------------------------------------------------------------------

def _clean_content(content: Optional[str]) -> str:
    """Enforces the 512 KB safe buffer limit and string normalization."""
    if not content or not isinstance(content, str):
        return ""
    return content[:MAX_FILE_SIZE_BYTES]


def _filter_files_by_ext(files: Mapping[str, str], extensions: Tuple[str, ...]) -> List[Tuple[str, str]]:
    """Filters candidate files by normalized file extensions."""
    results = []
    for path, content in sorted(files.items()):
        norm = normalize_repo_path(path)
        if not norm:
            continue
        lower_p = norm.lower()
        if any(lower_p.endswith(ext) for ext in extensions):
            results.append((norm, _clean_content(content)))
    return results


# Group 1: FastAPI
def _verify_fastapi_dependency_injection(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    py_files = _filter_files_by_ext(files, (".py",))
    for path, content in py_files:
        # Check AST for import of Depends or usage of Depends(...)
        try:
            tree_ast = ast.parse(content)
            has_import = False
            for node in ast.walk(tree_ast):
                if isinstance(node, ast.ImportFrom):
                    if node.module == "fastapi":
                        if any(alias.name == "Depends" for alias in node.names):
                            has_import = True
                            break
            if has_import:
                snippet = next((l.strip() for l in content.splitlines() if "Depends" in l), "from fastapi import Depends")
                return (
                    CriterionEvaluationStatus.PASSED,
                    path,
                    snippet[:MAX_SNIPPET_LENGTH],
                    "FastAPI Depends() dependency injection import detected via AST.",
                )
        except (SyntaxError, ValueError):
            pass

        # Fallback regex inspection
        match = re.search(r"(?:from\s+fastapi\s+import\s+[^\n]*\bDepends\b|\bDepends\s*\(|fastapi\.Depends\s*\()", content)
        if match:
            line = next((l.strip() for l in content.splitlines() if "Depends" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "FastAPI Depends() dependency injection usage detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No FastAPI Depends() dependency injection found in Python files.",
    )


def _verify_pydantic_v2_models(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    py_files = _filter_files_by_ext(files, (".py",))
    for path, content in py_files:
        has_base_model = bool(
            re.search(r"class\s+\w+\s*\([^)]*BaseModel[^)]*\):", content)
            or re.search(r"from\s+pydantic\s+import\s+[^\n]*BaseModel", content)
        )
        has_v2_feature = bool(
            re.search(
                r"\bmodel_config\s*=\s*ConfigDict\b|\bConfigDict\(|\bfield_validator\b|from\s+pydantic\s+import\s+[^\n]*ConfigDict",
                content,
            )
        )
        if has_base_model and has_v2_feature:
            line = next((l.strip() for l in content.splitlines() if "ConfigDict" in l or "BaseModel" in l), "model_config = ConfigDict(...)")
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Pydantic v2 BaseModel with ConfigDict or v2 validator detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No Pydantic v2 model definitions (BaseModel with ConfigDict) detected.",
    )


def _verify_status_code_testing(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    test_files = [
        (p, c) for p, c in _filter_files_by_ext(files, (".py",))
        if "test" in p.lower()
    ]
    for path, content in test_files:
        match = re.search(
            r"(?:assert\s+[^\n]*status_code\b|status_code\s*==\s*\d{3}|\bstatus\.HTTP_\d{3}_[A-Z_]+|response\.status_code)",
            content,
        )
        if match:
            line = next((l.strip() for l in content.splitlines() if "status_code" in l or "status.HTTP" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "HTTP status code assertion detected in test file.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No HTTP status code assertions found in test files.",
    )


# Group 2: Docker
def _find_dockerfiles(files: Mapping[str, str]) -> List[Tuple[str, str]]:
    results = []
    for path, content in sorted(files.items()):
        norm = normalize_repo_path(path)
        if not norm:
            continue
        name = norm.split("/")[-1].lower()
        if name == "dockerfile" or name.endswith(".dockerfile"):
            results.append((norm, _clean_content(content)))
    return results


def _verify_multi_stage_build(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    dfs = _find_dockerfiles(files)
    if not dfs:
        return (CriterionEvaluationStatus.FAILED, None, None, "No Dockerfile found in supplied repository files.")

    for path, content in dfs:
        from_matches = re.findall(r"^\s*FROM\s+([^\s#]+)", content, flags=re.MULTILINE | re.IGNORECASE)
        if len(from_matches) >= 2:
            snippet = f"FROM {from_matches[0]} ... FROM {from_matches[1]}"
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                snippet[:MAX_SNIPPET_LENGTH],
                f"Multi-stage build with {len(from_matches)} stages detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        dfs[0][0],
        None,
        "Dockerfile contains only 1 build stage; multi-stage build requires at least 2 FROM instructions.",
    )


def _verify_non_root_user(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    dfs = _find_dockerfiles(files)
    if not dfs:
        return (CriterionEvaluationStatus.FAILED, None, None, "No Dockerfile found in supplied repository files.")

    for path, content in dfs:
        user_matches = re.findall(r"^\s*USER\s+([^\s#]+)", content, flags=re.MULTILINE | re.IGNORECASE)
        for user in user_matches:
            clean_u = user.strip().lower()
            if clean_u not in ("root", "0", "0:0", "root:root"):
                return (
                    CriterionEvaluationStatus.PASSED,
                    path,
                    f"USER {user}",
                    f"Non-root USER instruction ('{user}') detected in Dockerfile.",
                )

    return (
        CriterionEvaluationStatus.FAILED,
        dfs[0][0],
        None,
        "No non-root USER instruction found in Dockerfile.",
    )


def _verify_explicit_workdir(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    dfs = _find_dockerfiles(files)
    if not dfs:
        return (CriterionEvaluationStatus.FAILED, None, None, "No Dockerfile found in supplied repository files.")

    for path, content in dfs:
        match = re.search(r"^\s*WORKDIR\s+([^\s#]+)", content, flags=re.MULTILINE | re.IGNORECASE)
        if match:
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                match.group(0).strip(),
                f"Explicit WORKDIR instruction ('{match.group(1).strip()}') detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        dfs[0][0],
        None,
        "No WORKDIR instruction found in Dockerfile.",
    )


# Group 3: Docker Compose
def _find_compose_files(files: Mapping[str, str]) -> List[Tuple[str, str]]:
    results = []
    for path, content in sorted(files.items()):
        norm = normalize_repo_path(path)
        if not norm:
            continue
        name = norm.split("/")[-1].lower()
        if "docker-compose" in name or name in ("compose.yml", "compose.yaml"):
            results.append((norm, _clean_content(content)))
    return results


def _verify_named_volumes(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    compose_files = _find_compose_files(files)
    if not compose_files:
        return (CriterionEvaluationStatus.FAILED, None, None, "No Docker Compose file found in repository files.")

    for path, content in compose_files:
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                top_vols = data.get("volumes")
                has_top = bool(top_vols and (isinstance(top_vols, dict) or isinstance(top_vols, list)))
                services = data.get("services", {})
                has_service_mount = False
                if isinstance(services, dict):
                    for s in services.values():
                        if isinstance(s, dict) and s.get("volumes"):
                            has_service_mount = True
                            break
                if has_top and has_service_mount:
                    return (
                        CriterionEvaluationStatus.PASSED,
                        path,
                        "volumes: defined and referenced in services",
                        "Named volume definitions and service volume mounts detected in Compose configuration.",
                    )
        except Exception:
            pass

        # Regex fallback
        has_top_regex = bool(re.search(r"^volumes:\s*\n(?:\s+[a-zA-Z0-9_\-]+:|\s+-\s+)", content, re.MULTILINE))
        has_mount_regex = bool(re.search(r"^\s+volumes:\s*\n\s+-\s+[a-zA-Z0-9_\-]+:", content, re.MULTILINE))
        if has_top_regex and has_mount_regex:
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                "volumes: ... - volume_name:/...",
                "Named volume definitions and service mounts detected in Compose configuration.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        compose_files[0][0],
        None,
        "No named volume configuration detected in Docker Compose file.",
    )


def _verify_service_healthchecks(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    compose_files = _find_compose_files(files)
    if not compose_files:
        return (CriterionEvaluationStatus.FAILED, None, None, "No Docker Compose file found in repository files.")

    for path, content in compose_files:
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and isinstance(data.get("services"), dict):
                for s_name, s_cfg in data["services"].items():
                    if isinstance(s_cfg, dict) and "healthcheck" in s_cfg:
                        return (
                            CriterionEvaluationStatus.PASSED,
                            path,
                            f"services.{s_name}.healthcheck",
                            f"Service healthcheck configuration detected under service '{s_name}'.",
                        )
        except Exception:
            pass

        match = re.search(r"^\s*healthcheck\s*:", content, re.MULTILINE)
        if match:
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                match.group(0).strip(),
                "Service healthcheck configuration detected in Docker Compose.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        compose_files[0][0],
        None,
        "No service healthchecks found in Docker Compose configuration.",
    )


def _verify_isolated_networks(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    compose_files = _find_compose_files(files)
    if not compose_files:
        return (CriterionEvaluationStatus.FAILED, None, None, "No Docker Compose file found in repository files.")

    for path, content in compose_files:
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                top_nets = data.get("networks")
                if top_nets and (isinstance(top_nets, dict) or isinstance(top_nets, list)):
                    return (
                        CriterionEvaluationStatus.PASSED,
                        path,
                        "networks: custom isolated network defined",
                        "Custom isolated network definitions detected in Compose configuration.",
                    )
        except Exception:
            pass

        match = re.search(r"^networks:\s*\n(?:\s+[a-zA-Z0-9_\-]+:|\s+-\s+)", content, re.MULTILINE)
        if match:
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                match.group(0).strip(),
                "Isolated network definitions detected in Docker Compose.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        compose_files[0][0],
        None,
        "No isolated network configuration found in Docker Compose.",
    )


# Group 4: PostgreSQL
def _verify_foreign_key_constraints(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    model_files = _filter_files_by_ext(files, (".py", ".sql"))
    for path, content in model_files:
        match = re.search(r"(?:\bForeignKey\s*\(\s*['\"][a-zA-Z0-9_\.]+['\"]|\bFOREIGN\s+KEY\b)", content)
        if match:
            line = next((l.strip() for l in content.splitlines() if "ForeignKey" in l or "FOREIGN KEY" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Relational foreign key constraint detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No relational foreign key constraints detected in model or SQL files.",
    )


def _verify_composite_indexes(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    model_files = _filter_files_by_ext(files, (".py", ".sql"))
    for path, content in model_files:
        match = re.search(
            r"(?:Index\s*\([^\)]*,\s*[^\)]*,[^\)]*\)|create_index\s*\([^\)]*,\s*\[[^\]]+,[^\]]+\]|CREATE\s+INDEX[^\(]*\([^\)]+,[^\)]+\)|UniqueConstraint\s*\([^\)]*,\s*['\"][^'\"]+['\"]\s*,\s*['\"][^'\"]+['\"])",
            content,
        )
        if match:
            line = next((l.strip() for l in content.splitlines() if "Index" in l or "UniqueConstraint" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Composite multi-column index or unique constraint detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No composite multi-column index definitions detected.",
    )


def _verify_reversible_migrations(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    migration_files = [
        (p, c) for p, c in _filter_files_by_ext(files, (".py",))
        if "alembic" in p.lower() or "migration" in p.lower() or "versions" in p.lower()
    ]
    if not migration_files:
        # Check any Python file defining downgrade()
        migration_files = _filter_files_by_ext(files, (".py",))

    for path, content in migration_files:
        downgrade_match = re.search(
            r"def\s+downgrade\s*\([^)]*\)\s*(?:->\s*None)?\s*:\s*\n((?:\s+[^\n]+\n)+)",
            content,
        )
        if downgrade_match:
            body = downgrade_match.group(1).strip()
            # Non-trivial downgrade has executable statements beyond pass or comments
            non_trivial = any(
                line.strip() and not line.strip().startswith(("#", "pass", "raise"))
                for line in body.splitlines()
            )
            if non_trivial:
                snippet = next(
                    (l.strip() for l in body.splitlines() if not l.strip().startswith("#")),
                    "def downgrade(): ...",
                )
                return (
                    CriterionEvaluationStatus.PASSED,
                    path,
                    snippet[:MAX_SNIPPET_LENGTH],
                    "Reversible migration with non-trivial downgrade() logic detected.",
                )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No reversible migrations with executable downgrade() logic detected.",
    )


# Group 5: GitHub Actions
def _find_workflow_files(files: Mapping[str, str]) -> List[Tuple[str, str]]:
    results = []
    for path, content in sorted(files.items()):
        norm = normalize_repo_path(path)
        if not norm:
            continue
        lower_p = norm.lower()
        if ".github/workflows/" in lower_p and (lower_p.endswith(".yml") or lower_p.endswith(".yaml")):
            results.append((norm, _clean_content(content)))
    return results


def _verify_pr_branch_trigger(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    workflows = _find_workflow_files(files)
    if not workflows:
        return (CriterionEvaluationStatus.FAILED, None, None, "No GitHub Actions workflow files found.")

    for path, content in workflows:
        match = re.search(r"(?:on:\s*\n[^\n]*\bpull_request\b|\bpull_request:\s*(?:branches|\n|\[|\{))", content)
        if match:
            line = next((l.strip() for l in content.splitlines() if "pull_request" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Pull request branch trigger detected in CI workflow.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        workflows[0][0],
        None,
        "No pull_request trigger found in GitHub Actions workflows.",
    )


def _verify_python_test_step(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    workflows = _find_workflow_files(files)
    if not workflows:
        return (CriterionEvaluationStatus.FAILED, None, None, "No GitHub Actions workflow files found.")

    for path, content in workflows:
        match = re.search(r"run:\s*[^\n]*(?:pytest\b|python\s+-m\s+(?:unittest|pytest))", content)
        if match:
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                match.group(0).strip()[:MAX_SNIPPET_LENGTH],
                "Automated Python test execution step (pytest/unittest) detected in CI workflow.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        workflows[0][0],
        None,
        "No automated test execution step (pytest/unittest) found in CI workflows.",
    )


def _verify_coverage_reporting(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    target_files = _find_workflow_files(files) + _filter_files_by_ext(
        files, ("pyproject.toml", "setup.cfg", ".coveragerc", "requirements.txt")
    )
    for path, content in target_files:
        match = re.search(r"(?:\bpytest-cov\b|\bcoverage\s+run\b|\bcoverage\s+report\b|\bcodecov\b|\bcoveralls\b|codecov/codecov-action)", content)
        if match:
            line = next((l.strip() for l in content.splitlines() if "coverage" in l or "codecov" in l or "pytest-cov" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Automated test coverage reporting configuration detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No test coverage reporting tool (pytest-cov/coverage/codecov) detected.",
    )


# Group 6: React
def _verify_typed_props(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    ts_files = _filter_files_by_ext(files, (".tsx", ".ts"))
    for path, content in ts_files:
        match = re.search(
            r"(?:interface\s+\w*Props\b|type\s+\w*Props\s*=|:\s*React\.FC<|:\s*FC<|\(\s*\{\s*[^}]+\s*\}\s*:\s*(?:\w*Props|\{[^}]+\}))",
            content,
        )
        if match:
            line = next((l.strip() for l in content.splitlines() if "Props" in l or "FC<" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Typed React component props interface/type definition detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No typed React component props definitions found in TypeScript files.",
    )


def _verify_error_boundary(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    react_files = _filter_files_by_ext(files, (".tsx", ".jsx", ".ts", ".js"))
    for path, content in react_files:
        match = re.search(
            r"(?:\bcomponentDidCatch\b|\bgetDerivedStateFromError\b|\bclass\s+\w*ErrorBoundary\b|<ErrorBoundary\b|from\s+['\"]react-error-boundary['\"])",
            content,
        )
        if match:
            line = next((l.strip() for l in content.splitlines() if "ErrorBoundary" in l or "componentDidCatch" in l or "getDerivedStateFromError" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "React Error Boundary implementation or usage detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No React Error Boundary implementation or fallback detected.",
    )


def _verify_accessible_aria_roles(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    react_files = _filter_files_by_ext(files, (".tsx", ".jsx", ".html"))
    for path, content in react_files:
        match = re.search(r"(?:\baria-[a-z]+=|role=['\"][a-z]+['\"])", content)
        if match:
            line = next((l.strip() for l in content.splitlines() if "aria-" in l or "role=" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Accessible ARIA attributes or semantic roles detected in component.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No accessible ARIA attributes or semantic roles found in UI components.",
    )


# Group 7: Next.js
def _verify_app_router_layout(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    for path in tree:
        lower_p = path.lower()
        if re.search(r"^app/(?:.*/)?layout\.(?:tsx|jsx|js)$", lower_p):
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                path,
                "Next.js App Router layout file detected in repository tree.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No Next.js App Router layout file (app/layout.tsx|jsx) found in repository tree.",
    )


def _verify_server_actions(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    js_files = _filter_files_by_ext(files, (".ts", ".tsx", ".js", ".jsx"))
    for path, content in js_files:
        match = re.search(r"['\"]use server['\"]", content)
        if match:
            line = next((l.strip() for l in content.splitlines() if "use server" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Next.js Server Actions ('use server') directive detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No Server Actions ('use server') directive detected in JavaScript/TypeScript files.",
    )


def _verify_responsive_grid(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    ui_files = _filter_files_by_ext(files, (".tsx", ".jsx", ".css", ".module.css", ".html"))
    for path, content in ui_files:
        match = re.search(
            r"(?:grid\s+.*(?:sm|md|lg|xl):grid-cols-|grid-cols-\d+\s+.*(?:sm|md|lg|xl):|@media[^{]+\{[^}]*display:\s*grid|\bgrid\b[^\n]*\b(?:sm|md|lg|xl):)",
            content,
        )
        if match:
            line = next((l.strip() for l in content.splitlines() if "grid" in l and any(bp in l for bp in ("md:", "lg:", "sm:", "@media"))), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Responsive CSS grid layout with responsive breakpoint modifiers detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No responsive grid layout with breakpoint modifiers detected.",
    )


# Group 8: PyTorch
def _verify_torch_nn_module(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    py_files = _filter_files_by_ext(files, (".py",))
    for path, content in py_files:
        match = re.search(r"class\s+\w+\s*\([^)]*(?:nn\.Module|torch\.nn\.Module)[^)]*\):", content)
        if match:
            line = next((l.strip() for l in content.splitlines() if "nn.Module" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "PyTorch neural network class inheriting from nn.Module detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No PyTorch nn.Module class inheritance detected in Python files.",
    )


def _verify_batch_evaluation(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    py_files = _filter_files_by_ext(files, (".py",))
    for path, content in py_files:
        has_loader = bool(re.search(r"\bDataLoader\b", content))
        has_eval_mode = bool(re.search(r"\b(?:torch\.no_grad|model\.eval)\b", content))
        if has_loader and has_eval_mode:
            line = next((l.strip() for l in content.splitlines() if "DataLoader" in l or "torch.no_grad" in l or "model.eval" in l), "DataLoader(...) with torch.no_grad()")
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "PyTorch DataLoader batch evaluation loop with torch.no_grad() or model.eval() detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No PyTorch batch evaluation loop (DataLoader with torch.no_grad or model.eval) detected.",
    )


def _verify_cosine_similarity_metric(
    tree: List[str], files: Mapping[str, str]
) -> Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]:
    py_files = _filter_files_by_ext(files, (".py",))
    for path, content in py_files:
        match = re.search(r"(?:cosine_similarity|F\.cosine_similarity|nn\.CosineSimilarity)", content)
        if match:
            line = next((l.strip() for l in content.splitlines() if "cosine_similarity" in l or "CosineSimilarity" in l), match.group(0))
            return (
                CriterionEvaluationStatus.PASSED,
                path,
                line[:MAX_SNIPPET_LENGTH],
                "Cosine similarity metric calculation detected.",
            )

    return (
        CriterionEvaluationStatus.FAILED,
        None,
        None,
        "No cosine similarity metric implementation detected in Python files.",
    )


# ---------------------------------------------------------------------------
# Criterion Registry Mapping (24 Seeded P4 Criteria)
# ---------------------------------------------------------------------------

CRITERIA_REGISTRY: Dict[str, Tuple[Callable[[List[str], Mapping[str, str]], Tuple[CriterionEvaluationStatus, Optional[str], Optional[str], Optional[str]]], str]] = {
    # FastAPI
    "fastapi_dependency_injection": (_verify_fastapi_dependency_injection, "Requires use of FastAPI Depends() dependency injection in Python code."),
    "pydantic_v2_models": (_verify_pydantic_v2_models, "Requires Pydantic v2 BaseModel definitions or ConfigDict configurations."),
    "status_code_testing": (_verify_status_code_testing, "Requires HTTP status code assertions in automated test files."),
    # Docker
    "multi_stage_build": (_verify_multi_stage_build, "Requires multi-stage Docker build with at least two distinct FROM instructions."),
    "non_root_user": (_verify_non_root_user, "Requires Dockerfile to execute under an explicit non-root user."),
    "explicit_workdir": (_verify_explicit_workdir, "Requires explicit WORKDIR instruction in Dockerfile."),
    # Docker Compose
    "named_volumes": (_verify_named_volumes, "Requires named volume definition and service mount in Docker Compose configuration."),
    "service_healthchecks": (_verify_service_healthchecks, "Requires service healthcheck configuration in Docker Compose."),
    "isolated_networks": (_verify_isolated_networks, "Requires custom isolated network definition in Docker Compose."),
    # PostgreSQL
    "foreign_key_constraints": (_verify_foreign_key_constraints, "Requires relational foreign key constraints in database models or SQL schemas."),
    "composite_indexes": (_verify_composite_indexes, "Requires composite database indexes spanning two or more columns."),
    "reversible_migrations": (_verify_reversible_migrations, "Requires Alembic migration with a non-trivial downgrade() implementation."),
    # GitHub Actions
    "pr_branch_trigger": (_verify_pr_branch_trigger, "Requires GitHub Actions workflow triggered on pull requests."),
    "python_test_step": (_verify_python_test_step, "Requires automated test execution step (pytest/unittest) in CI workflow."),
    "coverage_reporting": (_verify_coverage_reporting, "Requires test coverage reporting configuration in CI or project manifest."),
    # React
    "typed_props": (_verify_typed_props, "Requires typed props interface or type definition in React components."),
    "error_boundary": (_verify_error_boundary, "Requires React ErrorBoundary component implementation or fallback integration."),
    "accessible_aria_roles": (_verify_accessible_aria_roles, "Requires accessible ARIA attributes (aria-*) or role attributes in UI components."),
    # Next.js
    "app_router_layout": (_verify_app_router_layout, "Requires Next.js App Router root or nested layout (app/layout.tsx|jsx|js)."),
    "server_actions": (_verify_server_actions, "Requires Next.js Server Actions ('use server' directive)."),
    "responsive_grid": (_verify_responsive_grid, "Requires responsive CSS grid layout with breakpoint modifiers."),
    # PyTorch
    "torch_nn_module": (_verify_torch_nn_module, "Requires PyTorch neural network module class inheriting from nn.Module."),
    "batch_evaluation": (_verify_batch_evaluation, "Requires PyTorch DataLoader batch evaluation loop with torch.no_grad()."),
    "cosine_similarity_metric": (_verify_cosine_similarity_metric, "Requires cosine similarity metric calculation in evaluation or model code."),
}


# ---------------------------------------------------------------------------
# Pure Criteria Evaluation Engine
# ---------------------------------------------------------------------------

def evaluate_criteria(
    tree_entries: Sequence[Union[str, Mapping[str, Any]]],
    file_contents: Optional[Mapping[str, str]],
    verification_criteria: Sequence[str],
) -> CriteriaCheckDetail:
    """
    Deterministically evaluates verification criteria against repository artifacts.

    Locked Correction 4 Semantics:
    - PASSED and FAILED are automated criteria.
    - MANUAL_REVIEW_ONLY is excluded from automated scoring denominator.
    - UNSUPPORTED represents an unrecognized criterion key with no handler.
      It is surfaced visibly and is NOT silently treated as a candidate failure.
    - S_crit = passed_automated / all_evaluated_automated (1.0 if zero automated).
    """
    normalized_tree = extract_tree_paths(tree_entries)
    clean_files: Dict[str, str] = {}
    if file_contents:
        for p, c in file_contents.items():
            norm_p = normalize_repo_path(p)
            if norm_p:
                clean_files[norm_p] = _clean_content(c)

    results: List[CriterionDetail] = []
    unsupported_keys: List[str] = []
    manual_keys: List[str] = []

    for crit_key in verification_criteria:
        clean_key = crit_key.strip()
        if not clean_key:
            continue

        # Check if criterion is a registered automated rule
        if clean_key in CRITERIA_REGISTRY:
            handler, desc = CRITERIA_REGISTRY[clean_key]
            status, matched_file, matched_snippet, reason = handler(normalized_tree, clean_files)
            results.append(
                CriterionDetail(
                    criterion_key=clean_key,
                    status=status,
                    is_automated=True,
                    rule_description=desc,
                    matched_file=matched_file,
                    matched_snippet=matched_snippet,
                    reason=reason,
                )
            )
        # Check if criterion is explicitly designated for manual review
        elif "manual" in clean_key.lower():
            manual_keys.append(clean_key)
            results.append(
                CriterionDetail(
                    criterion_key=clean_key,
                    status=CriterionEvaluationStatus.MANUAL_REVIEW_ONLY,
                    is_automated=False,
                    rule_description="Subjective or non-automatable requirement designated for manual reviewer inspection.",
                    matched_file=None,
                    matched_snippet=None,
                    reason="Excluded from automated scoring; requires manual review.",
                )
            )
        # Unrecognized criterion key with no registered handler
        else:
            unsupported_keys.append(clean_key)
            results.append(
                CriterionDetail(
                    criterion_key=clean_key,
                    status=CriterionEvaluationStatus.UNSUPPORTED,
                    is_automated=False,
                    rule_description="Unrecognized criterion key with no registered deterministic verification handler.",
                    matched_file=None,
                    matched_snippet=None,
                    reason=f"Criterion key '{clean_key}' is unsupported by the deterministic verifier.",
                )
            )

    automated_results = [r for r in results if r.is_automated]
    passed_count = sum(1 for r in automated_results if r.status == CriterionEvaluationStatus.PASSED)
    failed_count = sum(1 for r in automated_results if r.status == CriterionEvaluationStatus.FAILED)
    auto_total = len(automated_results)

    if auto_total == 0:
        score = 1.0
    else:
        score = min(1.0, max(0.0, round(passed_count / auto_total, 2)))

    return CriteriaCheckDetail(
        total_criteria=len(results),
        automated_count=auto_total,
        passed_count=passed_count,
        failed_count=failed_count,
        manual_review_count=len(manual_keys),
        unsupported_count=len(unsupported_keys),
        criteria_score=score,
        results=tuple(results),
        unsupported_criteria=tuple(unsupported_keys),
        manual_review_criteria=tuple(manual_keys),
    )


# ---------------------------------------------------------------------------
# Pure Composite Confidence Calculation Helper
# ---------------------------------------------------------------------------

def compute_composite_confidence(
    deliverables_score: float,
    criteria_score: float,
    demonstrated_skill_score: float,
) -> float:
    """
    Computes composite verification confidence from pure scores:
    C_verif = 0.35 * S_deliv + 0.40 * S_crit + 0.25 * S_skill
    Clamped strictly to [0.0, 1.0] and rounded to 2 decimal places.
    """
    clamped_deliv = min(1.0, max(0.0, deliverables_score))
    clamped_crit = min(1.0, max(0.0, criteria_score))
    clamped_skill = min(1.0, max(0.0, demonstrated_skill_score))
    combined = (0.35 * clamped_deliv) + (0.40 * clamped_crit) + (0.25 * clamped_skill)
    return min(1.0, max(0.0, round(combined, 2)))


# ---------------------------------------------------------------------------
# Orchestrating ProjectVerifier Service
# ---------------------------------------------------------------------------

class ProjectVerifier:
    """
    Pure, deterministic verifier for project deliverables and criteria.
    Has zero network, zero database, and zero AI dependencies.
    """

    def verify(
        self,
        tree_entries: Sequence[Union[str, Mapping[str, Any]]],
        file_contents: Optional[Mapping[str, str]] = None,
        deliverables: Sequence[str] = (),
        verification_criteria: Sequence[str] = (),
        demonstrated_skill_score: Optional[float] = None,
    ) -> ProjectVerificationResult:
        """
        Executes pure deterministic verification of deliverables and criteria.
        If demonstrated_skill_score is provided, computes composite_confidence.
        Does NOT invent or fabricate demonstrated_skill_score if None.
        """
        deliv_detail = check_deliverables(
            tree_entries=tree_entries,
            required_deliverables=deliverables,
        )

        crit_detail = evaluate_criteria(
            tree_entries=tree_entries,
            file_contents=file_contents,
            verification_criteria=verification_criteria,
        )

        is_deliv_sat = (deliv_detail.deliverables_score == 1.0)
        is_crit_sat = (crit_detail.criteria_score >= 0.80 and crit_detail.unsupported_count == 0)

        composite_conf = None
        if demonstrated_skill_score is not None:
            composite_conf = compute_composite_confidence(
                deliverables_score=deliv_detail.deliverables_score,
                criteria_score=crit_detail.criteria_score,
                demonstrated_skill_score=demonstrated_skill_score,
            )

        return ProjectVerificationResult(
            deliverables=deliv_detail,
            criteria=crit_detail,
            deliverables_score=deliv_detail.deliverables_score,
            criteria_score=crit_detail.criteria_score,
            is_deliverables_satisfied=is_deliv_sat,
            is_criteria_satisfied=is_crit_sat,
            demonstrated_skill_score=demonstrated_skill_score,
            composite_confidence=composite_conf,
        )


project_verifier = ProjectVerifier()
