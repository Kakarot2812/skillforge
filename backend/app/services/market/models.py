"""
Market data contracts for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-B.

Defines normalized market job representations and ingestion result summaries.
Strictly in-memory at this stage; no database tables are modified.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class NormalizedMarketJob:
    """
    Controlled normalized representation of an ingested market job posting.

    Adheres to P1-B contract:
    - source: Data source identifier (always 'adzuna' for Adzuna postings)
    - external_job_id: Stable identifier from the source provider
    - title: Non-empty normalized job title
    - description: Normalized job description text, or None if unavailable
    - company_name: Normalized hiring company name, or None if unavailable
    - location: Normalized job location string, or None if unavailable
    - category: Industry/job category classification, or None
    - contract_type: Contract nature (e.g., 'permanent', 'contract'), or None
    - contract_time: Work schedule (e.g., 'full_time', 'part_time'), or None
    - created_at: ISO timestamp of original job creation, or None
    - redirect_url: Canonical URL to original posting, or None
    - raw_data: Complete upstream dictionary for provenance and auditability
    """

    source: str
    external_job_id: str
    title: str
    description: Optional[str] = None
    company_name: Optional[str] = None
    location: Optional[str] = None
    category: Optional[str] = None
    contract_type: Optional[str] = None
    contract_time: Optional[str] = None
    created_at: Optional[str] = None
    redirect_url: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def deduplication_key(self) -> Tuple[str, str]:
        """
        Deterministic primary deduplication key.
        Pairs source namespace with external job ID to prevent collisions across sources.
        """
        return (self.source, self.external_job_id)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes normalized job record to dictionary without modifying contents."""
        return {
            "source": self.source,
            "external_job_id": self.external_job_id,
            "title": self.title,
            "description": self.description,
            "company_name": self.company_name,
            "location": self.location,
            "category": self.category,
            "contract_type": self.contract_type,
            "contract_time": self.contract_time,
            "created_at": self.created_at,
            "redirect_url": self.redirect_url,
        }


@dataclass
class AdzunaIngestionResult:
    """
    Summary result structure for an Adzuna market ingestion run.
    Contains audit metrics and the final deduplicated job collection.
    Guaranteed free of credentials or sensitive request headers.
    """

    source: str = "adzuna"
    requested_queries: List[str] = field(default_factory=list)
    pages_fetched: int = 0
    raw_jobs_seen: int = 0
    valid_jobs: int = 0
    cleaned_jobs: int = 0
    duplicates_removed: int = 0
    final_jobs: List[NormalizedMarketJob] = field(default_factory=list)

    def to_summary_dict(self) -> Dict[str, Any]:
        """Returns safe summary audit dictionary without dumping all job records."""
        return {
            "source": self.source,
            "requested_queries": list(self.requested_queries),
            "pages_fetched": self.pages_fetched,
            "raw_jobs_seen": self.raw_jobs_seen,
            "valid_jobs": self.valid_jobs,
            "cleaned_jobs": self.cleaned_jobs,
            "duplicates_removed": self.duplicates_removed,
            "final_jobs_count": len(self.final_jobs),
        }


@dataclass
class MarketJobSkillEvidence:
    """
    Normalized representation of a canonical skill extracted from market job text.
    Post-MVP Phase 1, Checkpoint P1-D.

    Retains:
    - Target market job ID and canonical skill ID
    - Human-readable canonical name and the exact matched alias
    - Source field ('title' or 'description')
    - Verbatim evidence snippet directly from the job text
    - Deterministic extraction metadata
    """

    skill_id: Any  # uuid.UUID
    canonical_skill_name: str
    matched_alias: str
    source_field: str
    evidence_text: str
    market_job_id: Optional[Any] = None  # Optional[uuid.UUID]
    extraction_method: str = "deterministic_taxonomy_match"
    confidence_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_job_id": str(self.market_job_id) if self.market_job_id else None,
            "skill_id": str(self.skill_id),
            "canonical_skill_name": self.canonical_skill_name,
            "matched_alias": self.matched_alias,
            "source_field": self.source_field,
            "evidence_text": self.evidence_text,
            "extraction_method": self.extraction_method,
            "confidence_score": self.confidence_score,
        }


@dataclass
class MarketSkillExtractionMetrics:
    """
    Audit metrics for a batch market skill extraction and reconciliation run.
    Guaranteed free of credentials or sensitive headers.
    """

    jobs_processed: int = 0
    jobs_with_skills: int = 0
    jobs_without_skills: int = 0
    skills_matched: int = 0
    unique_skill_relationships: int = 0
    invalid_jobs_skipped: int = 0
    persistence_inserts: int = 0
    persistence_updates: int = 0
    persistence_unchanged: int = 0
    persistence_deletions: int = 0
    top_skills: List[Tuple[str, int]] = field(default_factory=list)

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "jobs_processed": self.jobs_processed,
            "jobs_with_skills": self.jobs_with_skills,
            "jobs_without_skills": self.jobs_without_skills,
            "skills_matched": self.skills_matched,
            "unique_skill_relationships": self.unique_skill_relationships,
            "invalid_jobs_skipped": self.invalid_jobs_skipped,
            "persistence": {
                "inserts": self.persistence_inserts,
                "updates": self.persistence_updates,
                "unchanged": self.persistence_unchanged,
                "deletions": self.persistence_deletions,
            },
            "top_skills": list(self.top_skills),
        }


@dataclass
class MarketSkillDemandRecord:
    """
    Normalized representation of an aggregated canonical skill demand metric.
    Post-MVP Phase 1, Checkpoint P1-E.

    Represents live demand computed empirically from current market jobs:
    - skill_id: Canonical UUID from skills table
    - canonical_skill_name: Canonical technology name (e.g. 'Python')
    - source: Data provider identifier (default 'adzuna')
    - job_count: Unique market jobs containing this canonical skill
    - sample_size: Total market jobs evaluated for this source snapshot
    - demand_share: Raw proportion (job_count / sample_size)
    - demand_score: Clamped normalized score in [0.0, 1.0] mathematically compatible
      with SkillForge demand intelligence
    - computed_at: Timestamp when this demand snapshot was calculated
    """

    skill_id: Any  # uuid.UUID
    canonical_skill_name: str
    source: str = "adzuna"
    job_count: int = 0
    sample_size: int = 0
    demand_share: float = 0.0
    demand_score: float = 0.0
    computed_at: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": str(self.skill_id),
            "canonical_skill_name": self.canonical_skill_name,
            "source": self.source,
            "job_count": self.job_count,
            "sample_size": self.sample_size,
            "demand_share": self.demand_share,
            "demand_score": self.demand_score,
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }


@dataclass
class MarketDemandAggregationMetrics:
    """
    Audit metrics for a deterministic market demand aggregation run.
    Post-MVP Phase 1, Checkpoint P1-E.
    Guaranteed free of credentials or sensitive headers.
    """

    source: str = "adzuna"
    sample_size: int = 0
    skills_with_demand: int = 0
    total_relationships: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_unchanged: int = 0
    rows_deleted: int = 0
    computed_at: Optional[Any] = None
    top_demanded_skills: List[Tuple[str, int, float]] = field(default_factory=list)

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "sample_size": self.sample_size,
            "skills_with_demand": self.skills_with_demand,
            "total_relationships": self.total_relationships,
            "persistence": {
                "inserts": self.rows_inserted,
                "updates": self.rows_updated,
                "unchanged": self.rows_unchanged,
                "deletions": self.rows_deleted,
            },
            "top_demanded_skills": list(self.top_demanded_skills),
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }

