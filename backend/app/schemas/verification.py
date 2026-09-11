"""
Pydantic v2 data contracts for Post-MVP Checkpoint P5-A:
Deterministic Project Verifier.

Enforces:
- Strict immutability and schema restrictions (frozen=True, extra="forbid").
- Deeply typed collections (Tuple instead of mutable List).
- Explicit status enums for deliverable matching and criterion evaluation.
- Fully bounded confidence and score fields [0.0, 1.0].
- Zero PAT / credential exposure.
"""

from enum import Enum
from typing import Any, Dict, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DeliverableMatchStatus(str, Enum):
    """Status of an individual deliverable path resolution."""
    PASSED = "PASSED"
    MISSING = "MISSING"
    AMBIGUOUS = "AMBIGUOUS"


class CriterionEvaluationStatus(str, Enum):
    """
    Status of an individual verification criterion rule evaluation.
    - PASSED: Deterministic rule evaluated successfully and requirement is satisfied.
    - FAILED: Deterministic rule evaluated successfully and requirement is not satisfied.
    - MANUAL_REVIEW_ONLY: Criterion is intentionally subjective or non-automatable.
    - UNSUPPORTED: Criterion key has no registered deterministic implementation.
    """
    PASSED = "PASSED"
    FAILED = "FAILED"
    MANUAL_REVIEW_ONLY = "MANUAL_REVIEW_ONLY"
    UNSUPPORTED = "UNSUPPORTED"


class DeliverableMatchItem(BaseModel):
    """Detailed resolution for a single required project deliverable."""
    deliverable: str = Field(..., description="Required deliverable path as declared in project")
    status: DeliverableMatchStatus = Field(..., description="Match resolution outcome")
    matched_path: Optional[str] = Field(None, description="Exact repository tree path matched if uniquely resolved")
    candidate_paths: Tuple[str, ...] = Field(default_factory=tuple, description="Candidate matches found if ambiguous")
    detail: str = Field("", description="Deterministic explanation of the match resolution")

    model_config = ConfigDict(frozen=True, extra="forbid")


class DeliverableCheckDetail(BaseModel):
    """Aggregated evaluation of all required project deliverables."""
    total_required: int = Field(..., ge=0, description="Total number of required deliverables")
    passed_count: int = Field(..., ge=0, description="Count of uniquely matched deliverables")
    missing_count: int = Field(..., ge=0, description="Count of unlocated deliverables")
    ambiguous_count: int = Field(..., ge=0, description="Count of deliverables with multiple matches")
    deliverables_score: float = Field(..., ge=0.0, le=1.0, description="Deliverables score in [0.0, 1.0]")
    required_deliverables: Tuple[str, ...] = Field(default_factory=tuple)
    passed_deliverables: Tuple[str, ...] = Field(default_factory=tuple)
    missing_deliverables: Tuple[str, ...] = Field(default_factory=tuple)
    ambiguous_deliverables: Tuple[str, ...] = Field(default_factory=tuple)
    matches: Tuple[DeliverableMatchItem, ...] = Field(default_factory=tuple)

    model_config = ConfigDict(frozen=True, extra="forbid")


class CriterionDetail(BaseModel):
    """Detailed evaluation result for a single verification criterion rule."""
    criterion_key: str = Field(..., description="Deterministic criterion identifier")
    status: CriterionEvaluationStatus = Field(..., description="Evaluation outcome")
    is_automated: bool = Field(..., description="True if criterion contributes to automated scoring")
    rule_description: str = Field(..., description="Description of the deterministic rule applied")
    matched_file: Optional[str] = Field(None, description="Repository file path that provided evidence")
    matched_snippet: Optional[str] = Field(None, max_length=512, description="Bounded code/pattern snippet evidence")
    reason: Optional[str] = Field(None, description="Deterministic explanation of pass/fail/unsupported outcome")

    model_config = ConfigDict(frozen=True, extra="forbid")


class CriteriaCheckDetail(BaseModel):
    """Aggregated evaluation of all verification criteria."""
    total_criteria: int = Field(..., ge=0, description="Total criteria evaluated")
    automated_count: int = Field(..., ge=0, description="Criteria contributing to automated score (PASSED + FAILED)")
    passed_count: int = Field(..., ge=0, description="Automated criteria that passed")
    failed_count: int = Field(..., ge=0, description="Automated criteria that failed")
    manual_review_count: int = Field(..., ge=0, description="Subjective criteria excluded from automated score")
    unsupported_count: int = Field(..., ge=0, description="Unrecognized criteria with no handler")
    criteria_score: float = Field(..., ge=0.0, le=1.0, description="Automated criteria pass rate in [0.0, 1.0]")
    results: Tuple[CriterionDetail, ...] = Field(default_factory=tuple)
    unsupported_criteria: Tuple[str, ...] = Field(default_factory=tuple)
    manual_review_criteria: Tuple[str, ...] = Field(default_factory=tuple)

    model_config = ConfigDict(frozen=True, extra="forbid")


class ProjectVerificationResult(BaseModel):
    """
    Immutable container representing the complete deterministic verification of an approved project.
    Purely functional and independent of external I/O or LLM invocation.
    """
    deliverables: DeliverableCheckDetail = Field(..., description="Deliverables evaluation details")
    criteria: CriteriaCheckDetail = Field(..., description="Verification criteria evaluation details")
    deliverables_score: float = Field(..., ge=0.0, le=1.0, description="Deliverables score in [0.0, 1.0]")
    criteria_score: float = Field(..., ge=0.0, le=1.0, description="Criteria score in [0.0, 1.0]")
    is_deliverables_satisfied: bool = Field(..., description="True if 100% of required deliverables exist uniquely")
    is_criteria_satisfied: bool = Field(..., description="True if criteria score >= 0.80 and no unsupported criteria")
    demonstrated_skill_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Demonstrated skill score if supplied by caller"
    )
    composite_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Combined confidence if demonstrated_skill_score was supplied"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")
