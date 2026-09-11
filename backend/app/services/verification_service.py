"""
VerificationService: Deterministic Milestone Verification Orchestration Layer.
Post-MVP Checkpoint P5-C.

Orchestrates:
roadmap milestone
  -> candidate-owned GitHub repository
  -> refreshed GitHub evidence
  -> ProjectVerifier
  -> demonstrated-skill recomputation
  -> deterministic verification result
  -> milestone verification persistence
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union
import uuid

from fastapi import HTTPException
import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.models import (
    ApprovedProject,
    CandidateRoadmap,
    DemonstratedSkill,
    GitHubRepository,
    MilestoneVerification,
    ProjectEvidence,
    RoadmapMilestone,
    User,
)
from app.services.demonstrated_skill_service import (
    demonstrated_skill_service,
    is_repo_owned_by_user,
)
from app.services.github_analyzer import github_analyzer
from app.services.github_service import (
    GITHUB_API_BASE,
    get_github_headers,
    github_service,
)
from app.services.project_verifier import (
    compute_composite_confidence,
    project_verifier,
)


# -----------------------------------------------------------------------------
# Domain Exceptions
# -----------------------------------------------------------------------------

class VerificationError(Exception):
    """Base domain exception for verification service operations."""
    pass


class VerificationNotFoundError(VerificationError):
    """Required entity (user, roadmap, milestone, repository) not found."""
    pass


class VerificationSecurityError(VerificationError):
    """Security or ownership violation during verification."""
    pass


class RoadmapOwnershipError(VerificationSecurityError):
    """Roadmap does not belong to the candidate."""
    pass


class MilestoneRoadmapMismatchError(VerificationSecurityError):
    """Milestone does not belong to the specified roadmap."""
    pass


class RepositoryOwnershipError(VerificationSecurityError):
    """Repository does not belong to candidate or connected GitHub account."""
    pass


class ForkedRepositoryError(VerificationSecurityError):
    """Forked repositories cannot be used for project verification."""
    pass


class VerificationInfrastructureError(VerificationError):
    """External service or infrastructure failure during verification."""
    pass


# -----------------------------------------------------------------------------
# Result Contract
# -----------------------------------------------------------------------------

class VerificationServiceResult(BaseModel):
    """
    Immutable typed result returned by VerificationService.
    Preserves audit history identifiers, scores, and updated milestone status.
    """
    id: uuid.UUID = Field(..., description="MilestoneVerification primary key")
    milestone_id: uuid.UUID = Field(..., description="Roadmap milestone ID")
    roadmap_id: uuid.UUID = Field(..., description="Candidate roadmap ID")
    user_id: uuid.UUID = Field(..., description="Candidate user ID")
    repository_id: uuid.UUID = Field(..., description="Verified GitHub repository ID")
    commit_sha: str = Field(..., description="Git commit SHA snapshot")
    status: str = Field(..., description="VERIFIED, PARTIAL, UNVERIFIED, or FAILED")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Composite confidence")
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured bounded audit details")
    milestone_status: str = Field(..., description="Milestone state after verification")
    created_at: datetime = Field(..., description="Verification timestamp")

    model_config = ConfigDict(frozen=True, extra="forbid")


# -----------------------------------------------------------------------------
# Verification Orchestrator Service
# -----------------------------------------------------------------------------

class VerificationService:
    """
    Orchestrates deterministic project verification for roadmap milestones.
    Integrates existing GitHub refresh, ProjectVerifier, and demonstrated-skill
    recomputation into an auditable, immutable verification pipeline.
    """

    def _resolve_commit_sha(
        self,
        repo: GitHubRepository,
        token: Optional[str] = None,
    ) -> str:
        """
        Resolves the authoritative Git commit SHA for the repository's default branch.
        Uses cached repo metadata if present, or queries GitHub commits API with token header.
        Never persists or logs access tokens.
        """
        # If repo metadata already contains authoritative commit SHA (e.g. from prior sync or offline mock), use it
        if repo.repo_metadata and repo.repo_metadata.get("commit_sha"):
            return str(repo.repo_metadata["commit_sha"])

        full_name = repo.full_name or repo.repo_name
        default_branch = repo.default_branch or "main"
        url = f"{GITHUB_API_BASE}/repos/{full_name}/commits/{default_branch}"
        headers = get_github_headers(token)

        try:
            res = github_analyzer.client.get(url, headers=headers)
        except (httpx.TimeoutException, httpx.RequestError) as e:
            raise VerificationInfrastructureError(
                f"Network failure while resolving commit SHA for '{full_name}': {str(e)}"
            )

        if res.status_code == 200:
            data = res.json()
            sha = data.get("sha")
            if sha and isinstance(sha, str) and len(sha) >= 7:
                return sha

        if res.status_code in (403, 429):
            raise VerificationInfrastructureError(
                "GitHub API rate limit reached while resolving commit SHA."
            )

        if res.status_code >= 500:
            raise VerificationInfrastructureError(
                f"GitHub API service unavailable (status {res.status_code})."
            )

        # Fall back to deterministic placeholder if repo is brand new
        return "0" * 40

    def verify_milestone(
        self,
        db: Session,
        user_id: uuid.UUID,
        roadmap_id: uuid.UUID,
        milestone_id: uuid.UUID,
        repository_id: Optional[uuid.UUID] = None,
        token: Optional[str] = None,
        github_username: Optional[str] = None,
    ) -> VerificationServiceResult:
        """
        Orchestrates milestone verification across 13 deterministic steps:
        1. Resolve & validate candidate user existence.
        2. Validate roadmap ownership (candidate IDOR check).
        3. Validate milestone existence and roadmap linkage.
        4. Resolve & validate candidate-owned repository (ownership + fork rejection).
        5. Verify connected GitHub username matches repository owner.
        6. Refresh GitHub repository evidence via existing analyzer.
        7. Resolve snapshot commit SHA.
        8. Load canonical ApprovedProject deliverables and criteria.
        9. Fetch relevant candidate file contents (bounded, max 512 KB).
        10. Recompute canonical demonstrated skill score via existing service.
        11. Run deterministic ProjectVerifier.
        12. Evaluate frozen P5 scoring rules (VERIFIED / PARTIAL / UNVERIFIED).
        13. Persist MilestoneVerification record and transition milestone state.
        """
        # ---------------------------------------------------------------------
        # Step 1: Candidate Validation
        # ---------------------------------------------------------------------
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise VerificationNotFoundError(f"Candidate user '{user_id}' not found.")

        # ---------------------------------------------------------------------
        # Step 2: Roadmap Ownership Validation
        # ---------------------------------------------------------------------
        roadmap = db.query(CandidateRoadmap).filter(CandidateRoadmap.id == roadmap_id).first()
        if not roadmap:
            raise VerificationNotFoundError(f"Roadmap '{roadmap_id}' not found.")
        if roadmap.user_id != user_id:
            raise RoadmapOwnershipError(
                f"Roadmap '{roadmap_id}' does not belong to candidate '{user_id}'."
            )

        # ---------------------------------------------------------------------
        # Step 3: Milestone Validation & Roadmap Linkage
        # ---------------------------------------------------------------------
        milestone = db.query(RoadmapMilestone).filter(RoadmapMilestone.id == milestone_id).first()
        if not milestone:
            raise VerificationNotFoundError(f"Milestone '{milestone_id}' not found.")
        if milestone.roadmap_id != roadmap.id:
            raise MilestoneRoadmapMismatchError(
                f"Milestone '{milestone_id}' does not belong to roadmap '{roadmap_id}'."
            )

        # ---------------------------------------------------------------------
        # Step 4: Repository Resolution & Ownership Validation
        # ---------------------------------------------------------------------
        if repository_id:
            repo = db.query(GitHubRepository).filter(GitHubRepository.id == repository_id).first()
            if not repo:
                raise VerificationNotFoundError(f"GitHub repository '{repository_id}' not found.")
        else:
            repo = (
                db.query(GitHubRepository)
                .filter(GitHubRepository.user_id == user_id, GitHubRepository.is_fork.is_(False))
                .first()
            )
            if not repo:
                raise VerificationNotFoundError(
                    f"No candidate-owned GitHub repository registered for user '{user_id}'."
                )

        # Cross-candidate access rejection
        if repo.user_id != user_id:
            raise RepositoryOwnershipError(
                f"Repository '{repo.id}' does not belong to candidate '{user_id}'."
            )

        # Fork rejection
        if repo.is_fork:
            raise ForkedRepositoryError(
                f"Repository '{repo.full_name or repo.repo_name}' is a fork. Forked repositories cannot be verified."
            )

        # ---------------------------------------------------------------------
        # Step 5: Connected GitHub Username Verification
        # ---------------------------------------------------------------------
        if github_username:
            repo_dict = {
                "repo_url": repo.repo_url,
                "full_name": repo.full_name,
                "owner": (repo.repo_metadata or {}).get("owner"),
                "repo_name": repo.repo_name,
            }
            if not is_repo_owned_by_user(repo_dict, github_username):
                raise RepositoryOwnershipError(
                    f"Repository '{repo.full_name or repo.repo_name}' owner does not match connected GitHub username '{github_username}'."
                )

        # ---------------------------------------------------------------------
        # Step 6 & 7: GitHub Refresh & Commit SHA Resolution
        # ---------------------------------------------------------------------
        commit_sha = "unknown"
        try:
            # Resolve commit SHA snapshot
            commit_sha = self._resolve_commit_sha(repo, token=token)

            # Refresh repository evidence via existing analyzer
            github_analyzer.analyze_repository(db=db, repo=repo, token=token)

            # Fetch git tree entries
            tree_entries = github_analyzer.fetch_repo_tree(
                repo.full_name or repo.repo_name,
                repo.default_branch or "main",
                token=token,
            )
        except (HTTPException, httpx.RequestError, httpx.TimeoutException, VerificationInfrastructureError) as exc:
            # Map external/infrastructure failures cleanly to FAILED status
            err_msg = exc.detail if isinstance(exc, HTTPException) else str(exc)
            # Never leak PAT in error details
            if token:
                err_msg = err_msg.replace(token, "[REDACTED]")

            failure_details = {
                "failure_type": "infrastructure_failure",
                "error": err_msg,
                "commit_sha": commit_sha if commit_sha != "unknown" else "unresolved",
                "attempted_at": datetime.now(timezone.utc).isoformat(),
            }

            # Persist FAILED verification record (preserves audit history)
            verification_record = MilestoneVerification(
                id=uuid.uuid4(),
                milestone_id=milestone.id,
                roadmap_id=roadmap.id,
                user_id=user_id,
                repository_id=repo.id,
                commit_sha=commit_sha if commit_sha != "unknown" else "unresolved",
                status="FAILED",
                confidence=None,
                details=failure_details,
                created_at=datetime.now(timezone.utc),
            )
            db.add(verification_record)
            db.commit()
            db.refresh(verification_record)

            # FAILED does NOT modify milestone status; preserve existing status
            return VerificationServiceResult(
                id=verification_record.id,
                milestone_id=milestone.id,
                roadmap_id=roadmap.id,
                user_id=user_id,
                repository_id=repo.id,
                commit_sha=verification_record.commit_sha,
                status="FAILED",
                confidence=None,
                details=failure_details,
                milestone_status=milestone.status,
                created_at=verification_record.created_at,
            )

        # ---------------------------------------------------------------------
        # Step 8: Load Canonical Approved Project Deliverables & Criteria
        # ---------------------------------------------------------------------
        project: Optional[ApprovedProject] = None
        if milestone.project_id:
            project = db.query(ApprovedProject).filter(ApprovedProject.id == milestone.project_id).first()
        if not project:
            project = db.query(ApprovedProject).filter(ApprovedProject.skill_id == milestone.skill_id).first()

        deliverables: List[str] = []
        criteria: List[str] = []
        if project:
            if isinstance(project.deliverables, list):
                deliverables = list(project.deliverables)
            if isinstance(project.verification_criteria, list):
                criteria = list(project.verification_criteria)

        # ---------------------------------------------------------------------
        # Step 9: Fetch Candidate File Contents for ProjectVerifier
        # ---------------------------------------------------------------------
        file_contents: Dict[str, str] = {}
        tree_paths = [
            e["path"] for e in tree_entries if isinstance(e, dict) and "path" in e
        ]

        # Prioritize required deliverables, standard manifests, dockerfiles, and CI workflows
        paths_to_fetch: Set[str] = set(deliverables)
        for tp in tree_paths:
            tp_lower = tp.lower()
            name = tp_lower.split("/")[-1]
            if name in (
                "dockerfile",
                "docker-compose.yml",
                "compose.yaml",
                "compose.yml",
                "requirements.txt",
                "package.json",
                "pyproject.toml",
            ):
                paths_to_fetch.add(tp)
            elif tp_lower.startswith(".github/workflows/") and (tp_lower.endswith(".yml") or tp_lower.endswith(".yaml")):
                paths_to_fetch.add(tp)
            elif tp_lower.endswith((".py", ".tsx", ".jsx", ".sql")):
                if len(paths_to_fetch) < 20:
                    paths_to_fetch.add(tp)

        for p in list(paths_to_fetch)[:20]:
            content = github_analyzer.fetch_file_content(
                repo.full_name or repo.repo_name,
                p,
                token=token,
            )
            if content is not None:
                file_contents[p] = content

        # ---------------------------------------------------------------------
        # Step 10: Recompute Canonical Demonstrated Skill Score
        # ---------------------------------------------------------------------
        demonstrated_skill = demonstrated_skill_service.recompute_demonstrated_skill(
            db=db,
            skill_id=milestone.skill_id,
            user_id=user_id,
        )
        demonstrated_skill_score = demonstrated_skill.confidence_score if demonstrated_skill else 0.0

        # ---------------------------------------------------------------------
        # Step 11: Execute Pure Deterministic ProjectVerifier
        # ---------------------------------------------------------------------
        verifier_result = project_verifier.verify(
            tree_entries=tree_entries,
            file_contents=file_contents,
            deliverables=deliverables,
            verification_criteria=criteria,
            demonstrated_skill_score=demonstrated_skill_score,
        )

        # ---------------------------------------------------------------------
        # Step 12: Calculate P5 Verification Status using Frozen Rules
        # ---------------------------------------------------------------------
        s_deliv = verifier_result.deliverables_score
        s_crit = verifier_result.criteria_score
        s_skill = demonstrated_skill_score
        c_conf = (
            verifier_result.composite_confidence
            if verifier_result.composite_confidence is not None
            else compute_composite_confidence(s_deliv, s_crit, s_skill)
        )

        # VERIFIED requires ALL:
        # 1. All required deliverables found (is_deliverables_satisfied is True)
        # 2. Automated criteria score >= 0.80 and no unsupported criteria
        # 3. Demonstrated skill score >= 0.70
        # 4. Composite confidence >= 0.85
        is_verified = (
            verifier_result.is_deliverables_satisfied
            and (s_crit >= 0.80 and verifier_result.criteria.unsupported_count == 0)
            and (s_skill >= 0.70)
            and (c_conf >= 0.85)
        )

        if is_verified:
            final_status = "VERIFIED"
        elif (c_conf >= 0.50 or s_deliv >= 0.50 or s_crit >= 0.50):
            final_status = "PARTIAL"
        else:
            final_status = "UNVERIFIED"

        # ---------------------------------------------------------------------
        # Step 13: Milestone State Transition & Audit Persistence
        # ---------------------------------------------------------------------
        if final_status == "VERIFIED":
            milestone.status = "VERIFIED"
        elif final_status in ("PARTIAL", "UNVERIFIED"):
            if milestone.status == "NOT_STARTED":
                milestone.status = "IN_PROGRESS"

        # Build bounded, typed audit details payload (zero credentials / raw dumps)
        bounded_details: Dict[str, Any] = {
            "deliverables": {
                "total_required": verifier_result.deliverables.total_required,
                "passed_count": verifier_result.deliverables.passed_count,
                "missing_count": verifier_result.deliverables.missing_count,
                "ambiguous_count": verifier_result.deliverables.ambiguous_count,
                "deliverables_score": s_deliv,
                "passed_deliverables": list(verifier_result.deliverables.passed_deliverables),
                "missing_deliverables": list(verifier_result.deliverables.missing_deliverables),
                "ambiguous_deliverables": list(verifier_result.deliverables.ambiguous_deliverables),
                "matches": [
                    {
                        "deliverable": m.deliverable,
                        "status": m.status.value,
                        "matched_path": m.matched_path,
                        "candidate_paths": list(m.candidate_paths),
                        "detail": m.detail,
                    }
                    for m in verifier_result.deliverables.matches
                ],
            },
            "criteria": {
                "total_criteria": verifier_result.criteria.total_criteria,
                "automated_count": verifier_result.criteria.automated_count,
                "passed_count": verifier_result.criteria.passed_count,
                "failed_count": verifier_result.criteria.failed_count,
                "manual_review_count": verifier_result.criteria.manual_review_count,
                "unsupported_count": verifier_result.criteria.unsupported_count,
                "criteria_score": s_crit,
                "unsupported_criteria": list(verifier_result.criteria.unsupported_criteria),
                "manual_review_criteria": list(verifier_result.criteria.manual_review_criteria),
                "results": [
                    {
                        "criterion_key": r.criterion_key,
                        "status": r.status.value,
                        "is_automated": r.is_automated,
                        "rule_description": r.rule_description,
                        "matched_file": r.matched_file,
                        "matched_snippet": r.matched_snippet,
                        "reason": r.reason,
                    }
                    for r in verifier_result.criteria.results
                ],
            },
            "scores": {
                "deliverables_score": s_deliv,
                "criteria_score": s_crit,
                "demonstrated_skill_score": s_skill,
                "composite_confidence": c_conf,
            },
            "evaluation": {
                "is_deliverables_satisfied": verifier_result.is_deliverables_satisfied,
                "is_criteria_satisfied": verifier_result.is_criteria_satisfied,
                "is_skill_satisfied": s_skill >= 0.70,
                "is_confidence_satisfied": c_conf >= 0.85,
            },
            "commit_sha": commit_sha,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

        verification_record = MilestoneVerification(
            id=uuid.uuid4(),
            milestone_id=milestone.id,
            roadmap_id=roadmap.id,
            user_id=user_id,
            repository_id=repo.id,
            commit_sha=commit_sha,
            status=final_status,
            confidence=c_conf,
            details=bounded_details,
            created_at=datetime.now(timezone.utc),
        )
        db.add(verification_record)
        db.commit()
        db.refresh(verification_record)

        return VerificationServiceResult(
            id=verification_record.id,
            milestone_id=milestone.id,
            roadmap_id=roadmap.id,
            user_id=user_id,
            repository_id=repo.id,
            commit_sha=commit_sha,
            status=final_status,
            confidence=c_conf,
            details=bounded_details,
            milestone_status=milestone.status,
            created_at=verification_record.created_at,
        )


verification_service = VerificationService()
