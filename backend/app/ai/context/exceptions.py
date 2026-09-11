"""
Exceptions for SkillForge AI Verified Context Contract.
Post-MVP Phase 2, Checkpoint P2-B.

Enforces deterministic boundaries between verified facts and AI reasoning.
"""

from typing import Any, Dict, List, Optional


class VerifiedContextError(Exception):
    """Base exception for all verified context contract violations."""
    pass


class ContextValidationError(VerifiedContextError, ValueError):
    """
    Raised when context fails deterministic validation before being passed to AI.
    Guarantees unverified, out-of-bounds, or contradictory claims never enter the LLM.
    """

    def __init__(self, message: str, field_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.field_name = field_name
        self.details = details or {}


class ContextImmutabilityError(VerifiedContextError, TypeError):
    """
    Raised when an attempt is made to mutate verified context facts.
    """
    pass


class ProvenanceError(ContextValidationError):
    """
    Raised when a fact lacks valid deterministic provenance.
    """
    pass
