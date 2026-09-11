"""
Pydantic v2 data contracts for Post-MVP Checkpoint P5-E:
AI Verification Explanation Layer.

Enforces:
- Strict immutability and schema restrictions (frozen=True, extra="forbid").
- Deeply typed collections (Tuple instead of mutable List).
- Server-authoritative preservation of deterministic verification status and confidence.
- Zero PAT / credential exposure.
"""

from typing import Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MilestoneVerificationExplainRequest(BaseModel):
    """Optional candidate request payload for AI verification explanation."""
    user_query: Optional[str] = Field(
        None, max_length=500, description="Optional candidate question regarding verification outcome"
    )
    temperature: float = Field(0.2, ge=0.0, le=1.0, description="Sampling temperature for Qwen")

    model_config = ConfigDict(frozen=True, extra="forbid")


class MilestoneVerificationExplainResponse(BaseModel):
    """
    Immutable typed response for AI milestone verification explanation.
    Guarantees deterministic verification status and confidence remain authoritative.
    """
    milestone_id: UUID = Field(..., description="Roadmap milestone UUID")
    verification_status: str = Field(..., description="Deterministic authoritative verification status")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Authoritative composite confidence")
    summary: str = Field(..., max_length=2000, description="High-level explanation of verification outcome")
    evidence_explanation: str = Field(..., max_length=8000, description="Detailed explanation of deliverable and criteria evidence")
    missing_evidence: Tuple[str, ...] = Field(default_factory=tuple, description="Explicit list of missing deliverables or failed criteria")
    next_steps: Tuple[str, ...] = Field(default_factory=tuple, description="Actionable recommendations for the candidate")
    model: str = Field(..., description="Name of local LLM generating explanation")

    model_config = ConfigDict(frozen=True, extra="forbid")
