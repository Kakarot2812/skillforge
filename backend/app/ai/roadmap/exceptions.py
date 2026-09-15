"""
Domain exceptions for AI Roadmap PDF Narrative Generation and Validation.
Post-MVP Career Roadmap PDF Feature (Phase 3).
"""

from typing import List, Optional


class RoadmapNarrativeError(Exception):
    """Base exception for all roadmap PDF narrative generation and validation errors."""
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NarrativeGenerationError(RoadmapNarrativeError):
    """Raised when the LLM provider fails to generate structured narrative output."""
    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


class NarrativeValidationError(RoadmapNarrativeError):
    """Raised when the generated narrative fails structural or schema validation rules."""
    pass


class ReferenceIntegrityError(NarrativeValidationError):
    """
    Raised when the generated narrative contains unauthorized references, unknown IDs,
    invented URLs/entities, or contradicts authoritative deterministic SkillForge data.
    Fails closed: unverified or hallucinated content is never accepted.
    """
    def __init__(self, message: str, violations: Optional[List[str]] = None):
        super().__init__(message)
        self.violations = violations or []
