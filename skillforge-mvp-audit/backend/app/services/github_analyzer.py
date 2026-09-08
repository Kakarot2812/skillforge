import base64
import json
import re
import tomllib
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import GitHubRepository, ProjectEvidence, Skill, SkillAlias
from app.services.github_service import GITHUB_API_BASE, get_github_headers
from app.services.skill_normalizer import normalize_string_key

MAX_TREE_ENTRIES = 1000
MAX_FILE_SIZE_BYTES = 512 * 1024  # 512 KB

# Deterministic confidence weights
CONFIDENCE_DEPENDENCY = 0.95
CONFIDENCE_DOCKERFILE = 0.90
CONFIDENCE_COMPOSE = 0.88
CONFIDENCE_CI_WORKFLOW = 0.85
CONFIDENCE_STRUCTURE = 0.70


class DiscoveredEvidenceCandidate:
    def __init__(
        self,
        skill_name_candidate: str,
        evidence_type: str,
        file_path: str,
        artifact_name: str,
        matched_content: str,
        confidence_score: float,
        evidence_metadata: Dict[str, Any],
        evidence_description: str,
    ):
        self.skill_name_candidate = skill_name_candidate
        self.evidence_type = evidence_type
        self.file_path = file_path
        self.artifact_name = artifact_name
        self.matched_content = matched_content
        self.confidence_score = confidence_score
        self.evidence_metadata = evidence_metadata
        self.evidence_description = evidence_description


def is_safe_repo_path(path: str) -> bool:
    """
    Validates repository file paths against directory traversal,
    null bytes, control characters, and absolute filesystem paths.
    """
    if not path or not isinstance(path, str):
        return False
    if "\0" in path or "\r" in path or "\n" in path:
        return False
    if path.startswith(("/", "\\")):
        return False
    normalized = path.replace("\\", "/")
    parts = normalized.split("/")
    if any(p in ("..", ".") for p in parts):
        return False
    return True


class GitHubAnalyzerService:
    """
    Inspects repository trees via GitHub API, parses dependency manifests,
    identifies infrastructure/CI artifacts, and normalizes findings into
    auditable, idempotent ProjectEvidence records.
    """

    def __init__(self, client: Optional[httpx.Client] = None):
        self.client = client or httpx.Client(timeout=20.0)

    def fetch_repo_tree(
        self,
        full_name: str,
        default_branch: str = "main",
        token: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves repository git tree without cloning repository files.
        """
        url = f"{GITHUB_API_BASE}/repos/{full_name}/git/trees/{default_branch}"
        params = {"recursive": "1"}
        headers = get_github_headers(token)

        try:
            res = self.client.get(url, headers=headers, params=params)
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"GitHub API tree inspection timed out for repository '{full_name}'.",
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to communicate with GitHub API for repository '{full_name}'.",
            )

        if res.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository '{full_name}' or branch '{default_branch}' not found on GitHub.",
            )
        elif res.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GitHub authorization failed during repository tree inspection.",
            )
        elif res.status_code in (403, 429):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit reached during repository analysis.",
            )
        elif res.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"GitHub API returned error {res.status_code} for repository '{full_name}'.",
            )

        data = res.json()
        tree = data.get("tree", [])
        return tree[:MAX_TREE_ENTRIES]

    def fetch_file_content(
        self,
        full_name: str,
        path: str,
        token: Optional[str] = None,
    ) -> Optional[str]:
        """
        Retrieves file text content from GitHub contents API with size safeguard.
        """
        if not is_safe_repo_path(path):
            return None

        url = f"{GITHUB_API_BASE}/repos/{full_name}/contents/{path}"
        headers = get_github_headers(token)

        try:
            res = self.client.get(url, headers=headers)
        except (httpx.TimeoutException, httpx.RequestError):
            return None

        if res.status_code != 200:
            return None

        data = res.json()
        if not isinstance(data, dict) or data.get("size", 0) > MAX_FILE_SIZE_BYTES:
            return None

        content_b64 = data.get("content")
        if not content_b64:
            return None

        try:
            return base64.b64decode(content_b64).decode("utf-8", errors="replace")
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Manifest Parsers
    # -------------------------------------------------------------------------

    def parse_requirements_txt(self, content: str, file_path: str) -> List[DiscoveredEvidenceCandidate]:
        candidates = []
        for line in content.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("#") or line_str.startswith("-"):
                continue

            # Strip environment markers and version operators
            clean_part = line_str.split(";")[0].strip()
            match = re.match(r"^([a-zA-Z0-9_\-\.]+)(.*)$", clean_part)
            if not match:
                continue

            pkg_name = match.group(1).strip()
            specifier = match.group(2).strip()

            candidates.append(
                DiscoveredEvidenceCandidate(
                    skill_name_candidate=pkg_name,
                    evidence_type="dependency",
                    file_path=file_path,
                    artifact_name="requirements.txt",
                    matched_content=line_str[:128],
                    confidence_score=CONFIDENCE_DEPENDENCY,
                    evidence_metadata={
                        "manifest": "requirements.txt",
                        "package": pkg_name,
                        "specifier": specifier,
                        "ecosystem": "pypi",
                    },
                    evidence_description=f"{pkg_name} is declared as a Python dependency in {file_path}.",
                )
            )
        return candidates

    def parse_pyproject_toml(self, content: str, file_path: str) -> List[DiscoveredEvidenceCandidate]:
        candidates = []
        try:
            data = tomllib.loads(content)
        except Exception:
            return candidates

        dependencies: List[str] = []
        # PEP 621 dependencies
        project_sec = data.get("project", {})
        if isinstance(project_sec.get("dependencies"), list):
            dependencies.extend(project_sec["dependencies"])

        # Poetry dependencies
        poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
        if isinstance(poetry_deps, dict):
            for k in poetry_deps.keys():
                if k.lower() != "python":
                    dependencies.append(k)

        for dep in dependencies:
            clean = re.split(r"[><=~^!;]", dep)[0].strip()
            if clean:
                candidates.append(
                    DiscoveredEvidenceCandidate(
                        skill_name_candidate=clean,
                        evidence_type="dependency",
                        file_path=file_path,
                        artifact_name="pyproject.toml",
                        matched_content=dep[:128],
                        confidence_score=CONFIDENCE_DEPENDENCY,
                        evidence_metadata={
                            "manifest": "pyproject.toml",
                            "package": clean,
                            "ecosystem": "pypi",
                        },
                        evidence_description=f"{clean} is declared as a Python dependency in {file_path}.",
                    )
                )
        return candidates

    def parse_package_json(self, content: str, file_path: str) -> List[DiscoveredEvidenceCandidate]:
        candidates = []
        try:
            pkg = json.loads(content)
        except Exception:
            return candidates

        all_deps: Dict[str, str] = {}
        for key in ("dependencies", "devDependencies", "peerDependencies"):
            if isinstance(pkg.get(key), dict):
                all_deps.update(pkg[key])

        for dep_name, version in all_deps.items():
            candidates.append(
                DiscoveredEvidenceCandidate(
                    skill_name_candidate=dep_name,
                    evidence_type="dependency",
                    file_path=file_path,
                    artifact_name="package.json",
                    matched_content=f'"{dep_name}": "{version}"',
                    confidence_score=CONFIDENCE_DEPENDENCY,
                    evidence_metadata={
                        "manifest": "package.json",
                        "package": dep_name,
                        "version": str(version),
                        "ecosystem": "npm",
                    },
                    evidence_description=f"{dep_name} is declared as an npm dependency in {file_path}.",
                )
            )
        return candidates

    def parse_pom_xml(self, content: str, file_path: str) -> List[DiscoveredEvidenceCandidate]:
        candidates = []
        try:
            # Strip XML namespaces for robust parsing
            clean_xml = re.sub(r'\sxmlns="[^"]+"', "", content, count=1)
            root = ET.fromstring(clean_xml)
            for dep in root.findall(".//dependency"):
                artifact_id = dep.findtext("artifactId")
                if artifact_id:
                    candidates.append(
                        DiscoveredEvidenceCandidate(
                            skill_name_candidate=artifact_id,
                            evidence_type="dependency",
                            file_path=file_path,
                            artifact_name="pom.xml",
                            matched_content=f"<artifactId>{artifact_id}</artifactId>",
                            confidence_score=CONFIDENCE_DEPENDENCY,
                            evidence_metadata={
                                "manifest": "pom.xml",
                                "package": artifact_id,
                                "ecosystem": "maven",
                            },
                            evidence_description=f"{artifact_id} is declared as a Maven dependency in {file_path}.",
                        )
                    )
        except Exception:
            pass
        return candidates

    def parse_go_mod(self, content: str, file_path: str) -> List[DiscoveredEvidenceCandidate]:
        candidates = []
        for line in content.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("//"):
                continue
            parts = line_str.split()
            if len(parts) >= 2 and parts[0] == "require":
                mod_path = parts[1]
                mod_name = mod_path.split("/")[-1]
                candidates.append(
                    DiscoveredEvidenceCandidate(
                        skill_name_candidate=mod_name,
                        evidence_type="dependency",
                        file_path=file_path,
                        artifact_name="go.mod",
                        matched_content=line_str[:128],
                        confidence_score=CONFIDENCE_DEPENDENCY,
                        evidence_metadata={"manifest": "go.mod", "module": mod_path, "ecosystem": "go"},
                        evidence_description=f"{mod_name} module is required in {file_path}.",
                    )
                )
            elif len(parts) >= 1 and "/" in parts[0]:
                mod_path = parts[0]
                mod_name = mod_path.split("/")[-1]
                candidates.append(
                    DiscoveredEvidenceCandidate(
                        skill_name_candidate=mod_name,
                        evidence_type="dependency",
                        file_path=file_path,
                        artifact_name="go.mod",
                        matched_content=line_str[:128],
                        confidence_score=CONFIDENCE_DEPENDENCY,
                        evidence_metadata={"manifest": "go.mod", "module": mod_path, "ecosystem": "go"},
                        evidence_description=f"{mod_name} module is declared in {file_path}.",
                    )
                )
        return candidates

    def parse_dockerfile(self, content: str, file_path: str) -> List[DiscoveredEvidenceCandidate]:
        candidates = []
        has_from = "FROM " in content.upper()
        if has_from:
            snippet = "\n".join([l for l in content.splitlines() if l.strip().upper().startswith(("FROM", "WORKDIR", "RUN"))][:3])
            candidates.append(
                DiscoveredEvidenceCandidate(
                    skill_name_candidate="Docker",
                    evidence_type="dockerfile",
                    file_path=file_path,
                    artifact_name="Dockerfile",
                    matched_content=snippet[:256] or "FROM instruction present",
                    confidence_score=CONFIDENCE_DOCKERFILE,
                    evidence_metadata={"instructions": ["FROM"], "path": file_path},
                    evidence_description=f"Repository contains a valid Dockerfile demonstrating containerization in {file_path}.",
                )
            )
        return candidates

    def parse_compose_file(self, content: str, file_path: str) -> List[DiscoveredEvidenceCandidate]:
        candidates = []
        # Check for service images in docker-compose
        for match in re.finditer(r"image:\s*([a-zA-Z0-9_\-\.\/]+)", content):
            image_name = match.group(1).split("/")[-1].split(":")[0]
            candidates.append(
                DiscoveredEvidenceCandidate(
                    skill_name_candidate=image_name,
                    evidence_type="dockerfile",
                    file_path=file_path,
                    artifact_name="docker-compose.yml",
                    matched_content=match.group(0)[:128],
                    confidence_score=CONFIDENCE_COMPOSE,
                    evidence_metadata={"compose_image": image_name, "path": file_path},
                    evidence_description=f"{image_name} container service configured in {file_path}.",
                )
            )
        return candidates

    def parse_ci_workflow(self, content: str, file_path: str) -> List[DiscoveredEvidenceCandidate]:
        candidates = []
        # CI Workflow evidence: GitHub Actions
        candidates.append(
            DiscoveredEvidenceCandidate(
                skill_name_candidate="CI/CD",
                evidence_type="ci_workflow",
                file_path=file_path,
                artifact_name=file_path.split("/")[-1],
                matched_content="name: CI / workflow triggers",
                confidence_score=CONFIDENCE_CI_WORKFLOW,
                evidence_metadata={"ci_platform": "GitHub Actions", "workflow_path": file_path},
                evidence_description=f"Automated CI/CD workflow defined in {file_path}.",
            )
        )
        return candidates

    # -------------------------------------------------------------------------
    # Analysis & Database Reconciliation Pipeline
    # -------------------------------------------------------------------------

    def analyze_repository(
        self,
        db: Session,
        repo: GitHubRepository,
        token: Optional[str] = None,
    ) -> List[ProjectEvidence]:
        """
        Coordinates tree inspection, artifact parsing, canonical normalization,
        and idempotent reconciliation in project_evidence.
        """
        full_name = repo.full_name or repo.repo_name
        default_branch = repo.default_branch or "main"

        # 1. Inspect repository tree
        tree_entries = self.fetch_repo_tree(full_name, default_branch, token=token)

        # 2. Identify candidate artifact paths
        paths_to_fetch: List[Tuple[str, str]] = []  # (path, parser_type)
        has_tests_dir = False

        for entry in tree_entries:
            path = entry.get("path", "")
            if not is_safe_repo_path(path):
                continue
            lower_path = path.lower()
            name = lower_path.split("/")[-1]

            if lower_path.startswith(("tests/", "test/")):
                has_tests_dir = True

            if name == "requirements.txt" or name.startswith("requirements-") and name.endswith(".txt"):
                paths_to_fetch.append((path, "requirements"))
            elif name == "pyproject.toml":
                paths_to_fetch.append((path, "pyproject"))
            elif name == "package.json":
                paths_to_fetch.append((path, "package_json"))
            elif name == "pom.xml":
                paths_to_fetch.append((path, "pom"))
            elif name == "go.mod":
                paths_to_fetch.append((path, "go_mod"))
            elif name == "dockerfile" or name.endswith(".dockerfile"):
                paths_to_fetch.append((path, "dockerfile"))
            elif "docker-compose" in name or name in ("compose.yml", "compose.yaml"):
                paths_to_fetch.append((path, "compose"))
            elif lower_path.startswith(".github/workflows/") and (lower_path.endswith(".yml") or lower_path.endswith(".yaml")):
                paths_to_fetch.append((path, "ci"))

        # 3. Fetch contents & extract raw candidates
        raw_candidates: List[DiscoveredEvidenceCandidate] = []

        # Process max 15 key manifests to avoid rate-limit exhaustion
        for path, p_type in paths_to_fetch[:15]:
            content = self.fetch_file_content(full_name, path, token=token)
            if not content:
                continue

            if p_type == "requirements":
                raw_candidates.extend(self.parse_requirements_txt(content, path))
            elif p_type == "pyproject":
                raw_candidates.extend(self.parse_pyproject_toml(content, path))
            elif p_type == "package_json":
                raw_candidates.extend(self.parse_package_json(content, path))
            elif p_type == "pom":
                raw_candidates.extend(self.parse_pom_xml(content, path))
            elif p_type == "go_mod":
                raw_candidates.extend(self.parse_go_mod(content, path))
            elif p_type == "dockerfile":
                raw_candidates.extend(self.parse_dockerfile(content, path))
            elif p_type == "compose":
                raw_candidates.extend(self.parse_compose_file(content, path))
            elif p_type == "ci":
                raw_candidates.extend(self.parse_ci_workflow(content, path))

        # Add repository language as structure/baseline evidence if defined
        if repo.primary_language:
            raw_candidates.append(
                DiscoveredEvidenceCandidate(
                    skill_name_candidate=repo.primary_language,
                    evidence_type="repository_structure",
                    file_path=repo.repo_name,
                    artifact_name="repository_primary_language",
                    matched_content=f"Primary language: {repo.primary_language}",
                    confidence_score=CONFIDENCE_STRUCTURE,
                    evidence_metadata={"source": "github_metadata", "language": repo.primary_language},
                    evidence_description=f"Repository primary programming language is {repo.primary_language}.",
                )
            )

        # 4. Canonical Skill Normalization
        # Pre-load taxonomy mapping: normalized_key -> Skill
        all_skills = db.query(Skill).all()
        all_aliases = db.query(SkillAlias).all()

        key_to_skill: Dict[str, Skill] = {}
        for s in all_skills:
            key_to_skill[normalize_string_key(s.name)] = s
            key_to_skill[normalize_string_key(s.slug)] = s

        for a in all_aliases:
            key_to_skill[normalize_string_key(a.alias)] = a.skill
            key_to_skill[normalize_string_key(a.normalized_alias)] = a.skill

        # Map candidates to canonical skills (ignoring unknown technologies)
        normalized_evidence: List[Tuple[Skill, DiscoveredEvidenceCandidate]] = []
        for cand in raw_candidates:
            cand_key = normalize_string_key(cand.skill_name_candidate)
            matched_skill = key_to_skill.get(cand_key)
            if matched_skill:
                normalized_evidence.append((matched_skill, cand))

        # 5. Idempotent Reconciliation in project_evidence
        persisted_records: List[ProjectEvidence] = []
        matched_keys: Set[Tuple[uuid.UUID, str, str]] = set()  # (skill_id, evidence_type, file_path)
        now = datetime.now()

        for skill, cand in normalized_evidence:
            record_key = (skill.id, cand.evidence_type, cand.file_path)
            if record_key in matched_keys:
                continue
            matched_keys.add(record_key)

            existing = (
                db.query(ProjectEvidence)
                .filter(
                    ProjectEvidence.repo_id == repo.id,
                    ProjectEvidence.skill_id == skill.id,
                    ProjectEvidence.evidence_type == cand.evidence_type,
                    ProjectEvidence.file_path == cand.file_path,
                )
                .first()
            )

            if existing:
                # Update in-place
                existing.artifact_name = cand.artifact_name
                existing.evidence_description = cand.evidence_description
                existing.matched_content = cand.matched_content
                existing.evidence_metadata = cand.evidence_metadata
                existing.confidence_score = cand.confidence_score
                existing.updated_at = now
                persisted_records.append(existing)
            else:
                new_evidence = ProjectEvidence(
                    id=uuid.uuid4(),
                    user_id=repo.user_id,
                    repo_id=repo.id,
                    skill_id=skill.id,
                    evidence_type=cand.evidence_type,
                    file_path=cand.file_path,
                    artifact_name=cand.artifact_name,
                    evidence_description=cand.evidence_description,
                    matched_content=cand.matched_content,
                    evidence_metadata=cand.evidence_metadata,
                    confidence_score=cand.confidence_score,
                    created_at=now,
                    updated_at=now,
                    detected_at=now,
                )
                db.add(new_evidence)
                persisted_records.append(new_evidence)

        # 6. Reconcile stale evidence: remove any previously recorded evidence for this repo
        # that was not found in the current scan
        all_existing_for_repo = (
            db.query(ProjectEvidence).filter(ProjectEvidence.repo_id == repo.id).all()
        )
        stale_skill_ids: Set[uuid.UUID] = set()
        for old_ev in all_existing_for_repo:
            if (old_ev.skill_id, old_ev.evidence_type, old_ev.file_path) not in matched_keys:
                stale_skill_ids.add(old_ev.skill_id)
                db.delete(old_ev)

        # 7. Update repository metadata
        detected_dep_names = sorted(
            list({s.name for s, c in normalized_evidence if c.evidence_type == "dependency"})
        )
        has_docker = any(c.evidence_type == "dockerfile" for _, c in normalized_evidence)
        has_ci = any(c.evidence_type == "ci_workflow" for _, c in normalized_evidence)

        repo_meta = dict(repo.repo_metadata or {})
        repo_meta["has_dockerfile"] = has_docker
        repo_meta["has_ci_workflow"] = has_ci
        repo_meta["detected_dependencies"] = detected_dep_names
        repo_meta["evidence_count"] = len(persisted_records)
        repo_meta["last_analyzed_at"] = now.isoformat()
        repo.repo_metadata = repo_meta

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        for rec in persisted_records:
            db.refresh(rec)

        affected_skill_ids = {s.id for s, _ in normalized_evidence} | stale_skill_ids
        return persisted_records, affected_skill_ids


github_analyzer = GitHubAnalyzerService()
