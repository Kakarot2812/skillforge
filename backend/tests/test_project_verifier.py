"""
Comprehensive unit tests for Post-MVP Checkpoint P5-A:
Deterministic Project Verifier.

Tests:
1. Deliverables matching (exact, nested, unique basename, ambiguous, missing, traversal, absolute, null byte, zero deliverables, repeatability).
2. All 24 Seeded P4 Project Criteria (positive, negative, and malformed inputs).
3. Unknown and subjective criteria handling (MANUAL_REVIEW_ONLY and UNSUPPORTED semantics).
4. Static safety (zero code execution, syntax error resilience, oversized buffers).
5. Scoring and composite confidence calculations.
6. Determinism and order independence.
"""

import pytest
from app.schemas.verification import (
    CriterionEvaluationStatus,
    DeliverableMatchStatus,
)
from app.services.project_verifier import (
    MAX_FILE_SIZE_BYTES,
    ProjectVerifier,
    check_deliverables,
    compute_composite_confidence,
    evaluate_criteria,
    is_safe_repo_path,
    normalize_repo_path,
    project_verifier,
)


# ===========================================================================
# 1. DELIVERABLES TESTS
# ===========================================================================

def test_deliverable_exact_root_path_match():
    tree = ["main.py", "Dockerfile", "requirements.txt"]
    result = check_deliverables(tree, ["Dockerfile", "main.py"])
    assert result.total_required == 2
    assert result.passed_count == 2
    assert result.missing_count == 0
    assert result.ambiguous_count == 0
    assert result.deliverables_score == 1.0
    assert "Dockerfile" in result.passed_deliverables
    assert "main.py" in result.passed_deliverables


def test_deliverable_exact_nested_path_match():
    tree = ["backend/main.py", "tests/test_api.py", "alembic/versions/0001_initial.py"]
    result = check_deliverables(tree, ["tests/test_api.py", "alembic/versions/0001_initial.py"])
    assert result.total_required == 2
    assert result.passed_count == 2
    assert result.deliverables_score == 1.0
    assert result.matches[0].status == DeliverableMatchStatus.PASSED
    assert result.matches[0].matched_path == "tests/test_api.py"


def test_deliverable_normalized_path_separators():
    # Backslashes, leading ./ and whitespace
    tree = [r"backend\main.py", "./Dockerfile", "  tests/test_api.py  "]
    result = check_deliverables(tree, [r"backend\main.py", "Dockerfile", "./tests/test_api.py"])
    assert result.total_required == 3
    assert result.passed_count == 3
    assert result.deliverables_score == 1.0


def test_deliverable_missing():
    tree = ["src/index.ts", "package.json"]
    result = check_deliverables(tree, ["Dockerfile", "main.py"])
    assert result.total_required == 2
    assert result.passed_count == 0
    assert result.missing_count == 2
    assert result.deliverables_score == 0.0
    assert "Dockerfile" in result.missing_deliverables
    assert "main.py" in result.missing_deliverables


def test_deliverable_unique_basename_match():
    # 'Dockerfile' requested; repo has single 'backend/deploy/Dockerfile'
    tree = ["backend/deploy/Dockerfile", "src/App.tsx", "package.json"]
    result = check_deliverables(tree, ["Dockerfile"])
    assert result.total_required == 1
    assert result.passed_count == 1
    assert result.deliverables_score == 1.0
    assert result.matches[0].status == DeliverableMatchStatus.PASSED
    assert result.matches[0].matched_path == "backend/deploy/Dockerfile"


def test_deliverable_ambiguous_basename_match():
    # 'main.py' requested; repo has 'backend/main.py' and 'services/worker/main.py'
    tree = ["backend/main.py", "services/worker/main.py", "README.md"]
    result = check_deliverables(tree, ["main.py"])
    assert result.total_required == 1
    assert result.passed_count == 0
    assert result.ambiguous_count == 1
    assert result.deliverables_score == 0.0
    match = result.matches[0]
    assert match.status == DeliverableMatchStatus.AMBIGUOUS
    assert match.matched_path is None
    assert "backend/main.py" in match.candidate_paths
    assert "services/worker/main.py" in match.candidate_paths
    assert "main.py" in result.ambiguous_deliverables


def test_deliverable_ambiguous_nested_match():
    # 'tests/test_api.py' requested; repo has both 'service_a/tests/test_api.py' and 'service_b/tests/test_api.py'
    # Under the locked rule, directory-containing paths must NOT use suffix matching; must be marked MISSING.
    tree = ["service_a/tests/test_api.py", "service_b/tests/test_api.py"]
    result = check_deliverables(tree, ["tests/test_api.py"])
    assert result.total_required == 1
    assert result.passed_count == 0
    assert result.ambiguous_count == 0
    assert result.missing_count == 1
    assert result.deliverables_score == 0.0
    assert result.matches[0].status == DeliverableMatchStatus.MISSING
    assert "tests/test_api.py" in result.missing_deliverables


def test_deliverable_nested_path_does_not_use_suffix_matching():
    # Exact regression test: required='tests/test_api.py', tree=['backend/tests/test_api.py']
    # Suffix matching is strictly prohibited for directory-containing paths; must be marked MISSING.
    tree = ["backend/tests/test_api.py"]
    result = check_deliverables(tree, ["tests/test_api.py"])
    assert result.total_required == 1
    assert result.passed_count == 0
    assert result.missing_count == 1
    assert result.ambiguous_count == 0
    assert result.deliverables_score == 0.0
    assert result.matches[0].status == DeliverableMatchStatus.MISSING
    assert "tests/test_api.py" in result.missing_deliverables


def test_deliverable_traversal_path_rejected():
    tree = ["main.py", "Dockerfile"]
    result = check_deliverables(tree, ["../../etc/passwd", "../Dockerfile"])
    assert result.total_required == 2
    assert result.passed_count == 0
    assert result.missing_count == 2
    assert result.deliverables_score == 0.0


def test_deliverable_absolute_path_rejected():
    tree = ["main.py", "Dockerfile"]
    result = check_deliverables(tree, ["/usr/local/bin/main.py"])
    assert result.total_required == 1
    assert result.passed_count == 0
    assert result.missing_count == 1
    assert result.deliverables_score == 0.0


def test_deliverable_null_byte_rejected():
    tree = ["main.py"]
    result = check_deliverables(tree, ["main\0.py"])
    assert result.total_required == 1
    assert result.passed_count == 0
    assert result.missing_count == 1
    assert result.deliverables_score == 0.0


def test_deliverable_zero_required():
    tree = ["main.py", "Dockerfile"]
    result = check_deliverables(tree, [])
    assert result.total_required == 0
    assert result.passed_count == 0
    assert result.deliverables_score == 1.0


def test_deliverable_deterministic_repeatability():
    tree = ["src/App.tsx", "package.json", "src/components/Dashboard.tsx"]
    reqs = ["package.json", "src/App.tsx", "src/components/Dashboard.tsx"]
    first = check_deliverables(tree, reqs)
    for _ in range(10):
        again = check_deliverables(tree, reqs)
        assert first == again


# ===========================================================================
# 2. ALL 24 SEEDED CRITERIA TESTS (POSITIVE + NEGATIVE + MALFORMED)
# ===========================================================================

# --- Group 1: FastAPI ---
def test_criterion_fastapi_dependency_injection_positive():
    files = {"main.py": "from fastapi import FastAPI, Depends\n\ndef get_db(): pass\n\n@app.get('/')\ndef index(db = Depends(get_db)): pass"}
    res = evaluate_criteria(["main.py"], files, ["fastapi_dependency_injection"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_fastapi_dependency_injection_negative():
    files = {"main.py": "from flask import Flask\napp = Flask(__name__)"}
    res = evaluate_criteria(["main.py"], files, ["fastapi_dependency_injection"])
    assert res.passed_count == 0
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_pydantic_v2_models_positive():
    files = {"schemas.py": "from pydantic import BaseModel, ConfigDict, Field\n\nclass UserOut(BaseModel):\n    id: int\n    model_config = ConfigDict(frozen=True)"}
    res = evaluate_criteria(["schemas.py"], files, ["pydantic_v2_models"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_pydantic_v2_models_negative():
    files = {"models.py": "class PlainUser:\n    def __init__(self, name): self.name = name"}
    res = evaluate_criteria(["models.py"], files, ["pydantic_v2_models"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_status_code_testing_positive():
    files = {"tests/test_api.py": "from fastapi import status\ndef test_health(client):\n    res = client.get('/health')\n    assert res.status_code == status.HTTP_200_OK"}
    res = evaluate_criteria(["tests/test_api.py"], files, ["status_code_testing"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_status_code_testing_negative():
    files = {"tests/test_math.py": "def test_add():\n    assert 1 + 1 == 2"}
    res = evaluate_criteria(["tests/test_math.py"], files, ["status_code_testing"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


# --- Group 2: Docker ---
def test_criterion_multi_stage_build_positive():
    content = "FROM python:3.12-slim as builder\nWORKDIR /build\nRUN pip install ...\n\nFROM python:3.12-alpine\nCOPY --from=builder /build /app"
    res = evaluate_criteria(["Dockerfile"], {"Dockerfile": content}, ["multi_stage_build"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_multi_stage_build_negative():
    content = "FROM python:3.12-slim\nWORKDIR /app\nCMD ['python', 'main.py']"
    res = evaluate_criteria(["Dockerfile"], {"Dockerfile": content}, ["multi_stage_build"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_non_root_user_positive():
    content = "FROM python:3.12-slim\nRUN useradd -m appuser\nUSER appuser\nCMD ['python']"
    res = evaluate_criteria(["Dockerfile"], {"Dockerfile": content}, ["non_root_user"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_non_root_user_negative_explicit_root():
    content = "FROM python:3.12-slim\nUSER root\nCMD ['python']"
    res = evaluate_criteria(["Dockerfile"], {"Dockerfile": content}, ["non_root_user"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_non_root_user_negative_missing():
    content = "FROM python:3.12-slim\nWORKDIR /app\nCMD ['python']"
    res = evaluate_criteria(["Dockerfile"], {"Dockerfile": content}, ["non_root_user"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_explicit_workdir_positive():
    content = "FROM python:3.12\nWORKDIR /usr/src/app\nCOPY . ."
    res = evaluate_criteria(["Dockerfile"], {"Dockerfile": content}, ["explicit_workdir"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_explicit_workdir_negative():
    content = "FROM python:3.12\nCOPY . /root\nCMD ['python']"
    res = evaluate_criteria(["Dockerfile"], {"Dockerfile": content}, ["explicit_workdir"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


# --- Group 3: Docker Compose ---
def test_criterion_named_volumes_positive():
    content = """
services:
  db:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
"""
    res = evaluate_criteria(["docker-compose.yml"], {"docker-compose.yml": content}, ["named_volumes"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_named_volumes_negative():
    content = """
services:
  web:
    image: nginx
    ports:
      - "80:80"
"""
    res = evaluate_criteria(["docker-compose.yml"], {"docker-compose.yml": content}, ["named_volumes"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_service_healthchecks_positive():
    content = """
services:
  db:
    image: postgres:15
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
"""
    res = evaluate_criteria(["docker-compose.yml"], {"docker-compose.yml": content}, ["service_healthchecks"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_service_healthchecks_negative():
    content = "services:\n  redis:\n    image: redis:alpine"
    res = evaluate_criteria(["docker-compose.yml"], {"docker-compose.yml": content}, ["service_healthchecks"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_isolated_networks_positive():
    content = """
services:
  api:
    image: myapi
    networks:
      - backend
networks:
  backend:
    driver: bridge
"""
    res = evaluate_criteria(["docker-compose.yml"], {"docker-compose.yml": content}, ["isolated_networks"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_isolated_networks_negative():
    content = "services:\n  api:\n    image: myapi"
    res = evaluate_criteria(["docker-compose.yml"], {"docker-compose.yml": content}, ["isolated_networks"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


# --- Group 4: PostgreSQL ---
def test_criterion_foreign_key_constraints_positive():
    files = {"models.py": "from sqlalchemy import Column, Integer, ForeignKey\nclass Item(Base):\n    user_id = Column(Integer, ForeignKey('users.id'))"}
    res = evaluate_criteria(["models.py"], files, ["foreign_key_constraints"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_foreign_key_constraints_negative():
    files = {"models.py": "class Item(Base):\n    name = Column(String)"}
    res = evaluate_criteria(["models.py"], files, ["foreign_key_constraints"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_composite_indexes_positive():
    files = {"models.py": "from sqlalchemy import Index\nIndex('ix_user_repo', 'user_id', 'repo_id')"}
    res = evaluate_criteria(["models.py"], files, ["composite_indexes"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_composite_indexes_negative():
    files = {"models.py": "from sqlalchemy import Index\nIndex('ix_name', 'name')"}
    res = evaluate_criteria(["models.py"], files, ["composite_indexes"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_reversible_migrations_positive():
    files = {"alembic/versions/0001_initial.py": "def upgrade():\n    op.create_table('users')\n\ndef downgrade() -> None:\n    op.drop_table('users')\n"}
    res = evaluate_criteria(["alembic/versions/0001_initial.py"], files, ["reversible_migrations"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_reversible_migrations_negative_pass_only():
    files = {"alembic/versions/0001_initial.py": "def upgrade():\n    op.create_table('users')\n\ndef downgrade():\n    pass\n"}
    res = evaluate_criteria(["alembic/versions/0001_initial.py"], files, ["reversible_migrations"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


# --- Group 5: GitHub Actions ---
def test_criterion_pr_branch_trigger_positive():
    content = "name: CI\non:\n  pull_request:\n    branches: [main]\njobs:\n  build:\n    runs-on: ubuntu-latest"
    res = evaluate_criteria([".github/workflows/ci.yml"], {".github/workflows/ci.yml": content}, ["pr_branch_trigger"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_pr_branch_trigger_negative():
    content = "name: CD\non:\n  push:\n    branches: [main]"
    res = evaluate_criteria([".github/workflows/ci.yml"], {".github/workflows/ci.yml": content}, ["pr_branch_trigger"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_python_test_step_positive():
    content = "jobs:\n  test:\n    steps:\n      - run: pytest -q --cov=app"
    res = evaluate_criteria([".github/workflows/ci.yml"], {".github/workflows/ci.yml": content}, ["python_test_step"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_python_test_step_negative():
    content = "jobs:\n  lint:\n    steps:\n      - run: flake8 ."
    res = evaluate_criteria([".github/workflows/ci.yml"], {".github/workflows/ci.yml": content}, ["python_test_step"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_coverage_reporting_positive():
    content = "jobs:\n  test:\n    steps:\n      - run: pytest --cov=app\n      - uses: codecov/codecov-action@v3"
    res = evaluate_criteria([".github/workflows/ci.yml"], {".github/workflows/ci.yml": content}, ["coverage_reporting"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_coverage_reporting_negative():
    content = "jobs:\n  build:\n    steps:\n      - run: echo 'build done'"
    res = evaluate_criteria([".github/workflows/ci.yml"], {".github/workflows/ci.yml": content}, ["coverage_reporting"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


# --- Group 6: React ---
def test_criterion_typed_props_positive():
    content = "import React from 'react';\ninterface DashboardProps {\n  title: string;\n  count: number;\n}\nexport const Dashboard: React.FC<DashboardProps> = ({ title }) => <div>{title}</div>;"
    res = evaluate_criteria(["src/components/Dashboard.tsx"], {"src/components/Dashboard.tsx": content}, ["typed_props"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_typed_props_negative():
    content = "export function Dashboard(props) { return <div>{props.title}</div>; }"
    res = evaluate_criteria(["src/components/Dashboard.jsx"], {"src/components/Dashboard.jsx": content}, ["typed_props"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_error_boundary_positive():
    content = "class ErrorBoundary extends React.Component {\n  componentDidCatch(error, info) { log(error); }\n  render() { return this.props.children; }\n}"
    res = evaluate_criteria(["src/ErrorBoundary.tsx"], {"src/ErrorBoundary.tsx": content}, ["error_boundary"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_error_boundary_negative():
    content = "export const Simple = () => <div>Hello</div>;"
    res = evaluate_criteria(["src/Simple.tsx"], {"src/Simple.tsx": content}, ["error_boundary"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_accessible_aria_roles_positive():
    content = "<button aria-label='Submit evidence' role='button'>Submit</button>"
    res = evaluate_criteria(["src/Button.tsx"], {"src/Button.tsx": content}, ["accessible_aria_roles"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_accessible_aria_roles_negative():
    content = "<div><span>Text</span></div>"
    res = evaluate_criteria(["src/Component.tsx"], {"src/Component.tsx": content}, ["accessible_aria_roles"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


# --- Group 7: Next.js ---
def test_criterion_app_router_layout_positive():
    tree = ["app/layout.tsx", "app/page.tsx", "package.json"]
    res = evaluate_criteria(tree, {}, ["app_router_layout"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_app_router_layout_negative():
    tree = ["pages/_app.tsx", "pages/index.tsx"]
    res = evaluate_criteria(tree, {}, ["app_router_layout"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_server_actions_positive():
    content = "'use server';\nexport async function createUser(data) { await db.insert(data); }"
    res = evaluate_criteria(["app/actions.ts"], {"app/actions.ts": content}, ["server_actions"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_server_actions_negative():
    content = "'use client';\nexport default function ClientComp() { return <div />; }"
    res = evaluate_criteria(["app/page.tsx"], {"app/page.tsx": content}, ["server_actions"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_responsive_grid_positive():
    content = "<div className='grid grid-cols-1 md:grid-cols-3 gap-4'>"
    res = evaluate_criteria(["app/page.tsx"], {"app/page.tsx": content}, ["responsive_grid"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_responsive_grid_negative():
    content = "<div className='flex flex-col'>"
    res = evaluate_criteria(["app/page.tsx"], {"app/page.tsx": content}, ["responsive_grid"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


# --- Group 8: PyTorch ---
def test_criterion_torch_nn_module_positive():
    content = "import torch\nimport torch.nn as nn\n\nclass EmbeddingModel(nn.Module):\n    def __init__(self):\n        super().__init__()\n        self.fc = nn.Linear(128, 64)"
    res = evaluate_criteria(["model.py"], {"model.py": content}, ["torch_nn_module"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_torch_nn_module_negative():
    content = "class SimpleClassifier:\n    def fit(self, X, y): pass"
    res = evaluate_criteria(["model.py"], {"model.py": content}, ["torch_nn_module"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_batch_evaluation_positive():
    content = "from torch.utils.data import DataLoader\nimport torch\n\nwith torch.no_grad():\n    for batch in DataLoader(dataset, batch_size=32):\n        output = model(batch)"
    res = evaluate_criteria(["evaluate.py"], {"evaluate.py": content}, ["batch_evaluation"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_batch_evaluation_negative():
    content = "for item in dataset:\n    predict(item)"
    res = evaluate_criteria(["evaluate.py"], {"evaluate.py": content}, ["batch_evaluation"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_criterion_cosine_similarity_metric_positive():
    content = "import torch.nn.functional as F\n\nsim = F.cosine_similarity(tensor_a, tensor_b, dim=-1)"
    res = evaluate_criteria(["evaluate.py"], {"evaluate.py": content}, ["cosine_similarity_metric"])
    assert res.passed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.PASSED


def test_criterion_cosine_similarity_metric_negative():
    content = "accuracy = correct / total"
    res = evaluate_criteria(["evaluate.py"], {"evaluate.py": content}, ["cosine_similarity_metric"])
    assert res.failed_count == 1
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


# ===========================================================================
# 3. UNKNOWN AND SUBJECTIVE CRITERIA TESTS (Correction 4)
# ===========================================================================

def test_unsupported_criterion_surfaced_explicitly():
    # Unknown criterion key not in the 24 registered keys
    res = evaluate_criteria(["main.py"], {}, ["completely_unknown_criterion_key"])
    assert res.total_criteria == 1
    assert res.automated_count == 0
    assert res.unsupported_count == 1
    # Unsupported criteria do not penalize automated criteria score
    assert res.criteria_score == 1.0
    item = res.results[0]
    assert item.status == CriterionEvaluationStatus.UNSUPPORTED
    assert item.is_automated is False
    assert "completely_unknown_criterion_key" in res.unsupported_criteria


def test_manual_review_only_criterion_excluded_from_automated_denominator():
    # Mix of 1 passed automated, 1 manual review only
    files = {"main.py": "from fastapi import Depends\n\ndef get_db(): pass\ndef ep(d=Depends(get_db)): pass"}
    res = evaluate_criteria(
        ["main.py"],
        files,
        ["fastapi_dependency_injection", "manual_review_creative_ui_design"],
    )
    assert res.total_criteria == 2
    assert res.automated_count == 1
    assert res.passed_count == 1
    assert res.manual_review_count == 1
    # S_crit is 1 / 1 = 1.0 (manual_review_creative_ui_design excluded from denominator)
    assert res.criteria_score == 1.0
    assert res.results[1].status == CriterionEvaluationStatus.MANUAL_REVIEW_ONLY
    assert res.results[1].is_automated is False


def test_unsupported_criterion_does_not_silently_become_failed():
    # 1 failed automated rule + 1 unsupported rule
    res = evaluate_criteria(
        ["main.py"],
        {"main.py": "print('hello')"},
        ["fastapi_dependency_injection", "unsupported_legacy_rule"],
    )
    assert res.total_criteria == 2
    assert res.automated_count == 1
    assert res.failed_count == 1
    assert res.unsupported_count == 1
    # S_crit is 0 / 1 = 0.0, because only the automated rule counted
    assert res.criteria_score == 0.0
    assert res.results[0].status == CriterionEvaluationStatus.FAILED
    assert res.results[1].status == CriterionEvaluationStatus.UNSUPPORTED


# ===========================================================================
# 4. STATIC SAFETY AND BOUNDARY TESTS
# ===========================================================================

def test_static_safety_malformed_python_does_not_crash():
    # Completely broken Python syntax
    broken_code = "def syntax_error( ::: {{ unclosed string '"
    res = evaluate_criteria(["bad.py"], {"bad.py": broken_code}, ["fastapi_dependency_injection", "pydantic_v2_models"])
    assert res.automated_count == 2
    assert res.failed_count == 2
    assert res.results[0].status == CriterionEvaluationStatus.FAILED
    assert res.results[1].status == CriterionEvaluationStatus.FAILED


def test_static_safety_malformed_yaml_does_not_crash():
    broken_yaml = "services:\n  - [unclosed yaml: {}}"
    res = evaluate_criteria(
        ["docker-compose.yml"],
        {"docker-compose.yml": broken_yaml},
        ["named_volumes", "service_healthchecks", "isolated_networks"],
    )
    assert res.automated_count == 3
    assert res.failed_count == 3


def test_static_safety_zero_code_execution():
    # Ensure source is never executed or imported: if it were executed, a NameError or side effect would occur
    dangerous_code = "import sys\n# If executed, this would raise an explicit exception\nif False:\n    raise SystemExit('Code execution happened!')"
    res = evaluate_criteria(["main.py"], {"main.py": dangerous_code}, ["fastapi_dependency_injection"])
    assert res.results[0].status == CriterionEvaluationStatus.FAILED


def test_static_safety_oversized_file_buffer_clamped():
    # Buffer larger than 512 KB
    giant_prefix = "# " + ("A" * 600 * 1024) + "\n"
    code = giant_prefix + "from fastapi import Depends\n"
    # The verifier clamps to MAX_FILE_SIZE_BYTES so the appended Depends at > 600 KB will not be read
    res = evaluate_criteria(["main.py"], {"main.py": code}, ["fastapi_dependency_injection"])
    assert res.failed_count == 1


# ===========================================================================
# 5. SCORING AND COMPOSITE CONFIDENCE TESTS
# ===========================================================================

def test_deliverable_score_boundaries():
    tree = ["a.py", "b.py"]
    # 0 of 2 passed -> 0.0
    r0 = check_deliverables(tree, ["c.py", "d.py"])
    assert r0.deliverables_score == 0.0

    # 1 of 2 passed -> 0.5
    r5 = check_deliverables(tree, ["a.py", "d.py"])
    assert r5.deliverables_score == 0.5

    # 2 of 2 passed -> 1.0
    r1 = check_deliverables(tree, ["a.py", "b.py"])
    assert r1.deliverables_score == 1.0


def test_criteria_score_zero_automated():
    # Zero criteria
    r_empty = evaluate_criteria(["main.py"], {}, [])
    assert r_empty.criteria_score == 1.0

    # Only manual review criteria -> 1.0
    r_manual = evaluate_criteria(["main.py"], {}, ["manual_review_code_style"])
    assert r_manual.criteria_score == 1.0


def test_composite_confidence_calculation():
    # C_verif = 0.35 * S_deliv + 0.40 * S_crit + 0.25 * S_skill
    # Example 1: 1.0, 1.0, 1.0 -> 1.0
    assert compute_composite_confidence(1.0, 1.0, 1.0) == 1.0

    # Example 2: 0.0, 0.0, 0.0 -> 0.0
    assert compute_composite_confidence(0.0, 0.0, 0.0) == 0.0

    # Example 3: S_deliv=1.0, S_crit=1.0, S_skill=0.95 -> 0.35 + 0.40 + 0.2375 = 0.9875 -> 0.99
    assert compute_composite_confidence(1.0, 1.0, 0.95) == 0.99

    # Example 4: Clamping test (exceeding 1.0 or negative)
    assert compute_composite_confidence(1.5, 2.0, 1.0) == 1.0
    assert compute_composite_confidence(-0.5, 0.0, 0.0) == 0.0


def test_project_verifier_orchestration_without_skill_score():
    tree = ["main.py", "requirements.txt", "Dockerfile", "tests/test_api.py"]
    files = {
        "main.py": "from fastapi import FastAPI, Depends\nfrom pydantic import BaseModel, ConfigDict\nclass Item(BaseModel):\n    model_config = ConfigDict()",
        "tests/test_api.py": "def test_ok():\n    assert res.status_code == 200",
    }
    deliverables = ["main.py", "requirements.txt", "Dockerfile", "tests/test_api.py"]
    criteria = ["fastapi_dependency_injection", "pydantic_v2_models", "status_code_testing"]

    # Without demonstrated skill score: composite_confidence must be None (zero score fabrication)
    result = project_verifier.verify(
        tree_entries=tree,
        file_contents=files,
        deliverables=deliverables,
        verification_criteria=criteria,
        demonstrated_skill_score=None,
    )
    assert result.deliverables_score == 1.0
    assert result.criteria_score == 1.0
    assert result.is_deliverables_satisfied is True
    assert result.is_criteria_satisfied is True
    assert result.demonstrated_skill_score is None
    assert result.composite_confidence is None


def test_project_verifier_orchestration_with_skill_score():
    tree = ["main.py"]
    files = {"main.py": "from fastapi import Depends"}
    result = project_verifier.verify(
        tree_entries=tree,
        file_contents=files,
        deliverables=["main.py"],
        verification_criteria=["fastapi_dependency_injection"],
        demonstrated_skill_score=0.90,
    )
    assert result.deliverables_score == 1.0
    assert result.criteria_score == 1.0
    assert result.demonstrated_skill_score == 0.90
    # 0.35 * 1.0 + 0.40 * 1.0 + 0.25 * 0.90 = 0.75 + 0.225 = 0.975 -> 0.97 (round-to-even)
    assert result.composite_confidence == 0.97


# ===========================================================================
# 6. DETERMINISM AND ORDER INDEPENDENCE TESTS
# ===========================================================================

def test_determinism_tree_and_criteria_order_independence():
    tree_a = ["Dockerfile", "main.py", "requirements.txt"]
    tree_b = ["requirements.txt", "Dockerfile", "main.py"]
    files_a = {
        "main.py": "from fastapi import Depends\nfrom pydantic import BaseModel, ConfigDict\nmodel_config = ConfigDict()",
    }
    files_b = dict(reversed(list(files_a.items())))

    criteria_a = ["pydantic_v2_models", "fastapi_dependency_injection"]
    criteria_b = ["fastapi_dependency_injection", "pydantic_v2_models"]

    res_a = project_verifier.verify(tree_a, files_a, ["main.py", "Dockerfile"], criteria_a)
    res_b = project_verifier.verify(tree_b, files_b, ["Dockerfile", "main.py"], criteria_b)

    assert res_a.deliverables_score == res_b.deliverables_score
    assert res_a.criteria_score == res_b.criteria_score
    assert res_a.is_deliverables_satisfied == res_b.is_deliverables_satisfied
    assert res_a.is_criteria_satisfied == res_b.is_criteria_satisfied


def test_path_normalization_utilities():
    assert is_safe_repo_path("backend/main.py") is True
    assert is_safe_repo_path("../backend/main.py") is False
    assert is_safe_repo_path("/etc/passwd") is False
    assert is_safe_repo_path("src\0/file.ts") is False
    assert is_safe_repo_path("") is False

    assert normalize_repo_path(r"backend\app\main.py") == "backend/app/main.py"
    assert normalize_repo_path("./src/index.ts") == "src/index.ts"
    assert normalize_repo_path("/root/file.py") is None
