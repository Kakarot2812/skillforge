"""
Market skill extraction service for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-D.

Provides controlled batch processing of persisted market jobs, deterministic
skill extraction against canonical taxonomy, idempotent persistence, and reconciliation.
"""

from collections import Counter
import logging
from typing import Dict, List, Optional, Set
import uuid

from sqlalchemy.orm import Session

from app.db.models import MarketJob
from app.services.market.extraction.matcher import DeterministicSkillMatcher
from app.services.market.models import (
    MarketJobSkillEvidence,
    MarketSkillExtractionMetrics,
)
from app.services.market.repository import MarketJobSkillRepository

logger = logging.getLogger(__name__)


class MarketSkillExtractionService:
    """
    Orchestration service for batch deterministic skill extraction from persisted market jobs.
    Post-MVP Phase 1, Checkpoint P1-D.

    - Processes market jobs in controlled, configurable batches.
    - Uses DeterministicSkillMatcher with canonical taxonomy.
    - Idempotently persists relationships via MarketJobSkillRepository.
    - Reconciles stale skills when job texts are updated.
    - Collects and reports audit metrics (zero credentials).
    """

    def __init__(
        self,
        matcher: Optional[DeterministicSkillMatcher] = None,
        repository: Optional[MarketJobSkillRepository] = None,
    ):
        """
        Initializes the extraction service with optional custom matcher or repository.
        If matcher is None, it will be loaded lazily from the database during processing.
        """
        self._matcher = matcher
        self._repository = repository or MarketJobSkillRepository()

    def get_matcher(self, db: Session) -> DeterministicSkillMatcher:
        """Lazily initializes and caches the DeterministicSkillMatcher from the database."""
        if self._matcher is None:
            self._matcher = DeterministicSkillMatcher(db=db)
        return self._matcher

    def extract_and_persist_for_job(
        self,
        job: MarketJob,
        db: Session,
        reconcile: bool = True,
        commit: bool = False,
    ) -> List[MarketJobSkillEvidence]:
        """
        Extracts deterministic canonical skills from a single MarketJob and persists them.

        Args:
            job: The persisted MarketJob instance.
            db: Active database session.
            reconcile: Whether to delete stale skills not present in current extraction.
            commit: Whether to commit the transaction immediately.

        Returns:
            List of extracted MarketJobSkillEvidence records.
        """
        if not job or not job.id:
            raise ValueError("Invalid job: job and job.id must be provided")

        if not job.title or not job.title.strip():
            logger.warning("Skipping job %s: empty title", job.id)
            return []

        matcher = self.get_matcher(db)
        extracted = matcher.extract_skills_for_job(
            title=job.title,
            description=job.description,
            market_job_id=job.id,
        )

        self._repository.persist_job_skills(
            market_job_id=job.id,
            skills=extracted,
            db=db,
            reconcile=reconcile,
        )

        if commit:
            db.commit()

        return extracted

    def process_persisted_jobs(
        self,
        db: Session,
        batch_size: int = 50,
        max_jobs: Optional[int] = None,
        source: Optional[str] = None,
        reconcile: bool = True,
        commit: bool = True,
    ) -> MarketSkillExtractionMetrics:
        """
        Processes persisted market jobs in a controlled batch.

        Args:
            db: Active database session.
            batch_size: Maximum number of jobs to fetch per query batch (default 50).
            max_jobs: Maximum total number of jobs to process across this invocation.
            source: Optional source filter (e.g., 'adzuna').
            reconcile: Whether to reconcile existing skills for updated jobs (default True).
            commit: Whether to commit the database session upon completion (default True).

        Returns:
            MarketSkillExtractionMetrics containing detailed operational audit metrics.
        """
        metrics = MarketSkillExtractionMetrics()
        matcher = self.get_matcher(db)

        # Build query for candidate jobs
        query = db.query(MarketJob)
        if source and source.strip():
            query = query.filter(MarketJob.source == source.strip())

        # Process in deterministic order: newest created_at first, stable tiebreaker by id
        query = query.order_by(MarketJob.created_at.desc().nullslast(), MarketJob.id.asc())

        # Determine fetch limit
        limit = batch_size
        if max_jobs is not None:
            limit = min(max_jobs, batch_size)

        jobs: List[MarketJob] = query.limit(limit).all()

        skill_counter: Counter = Counter()
        unique_skill_ids: Set[uuid.UUID] = set()

        for job in jobs:
            # Validate essential fields
            if not job.title or not job.title.strip():
                metrics.invalid_jobs_skipped += 1
                continue

            extracted = matcher.extract_skills_for_job(
                title=job.title,
                description=job.description,
                market_job_id=job.id,
            )

            metrics.jobs_processed += 1

            if extracted:
                metrics.jobs_with_skills += 1
                metrics.skills_matched += len(extracted)

                for ev in extracted:
                    skill_counter[ev.canonical_skill_name] += 1
                    unique_skill_ids.add(ev.skill_id)
            else:
                metrics.jobs_without_skills += 1

            # Persist to PostgreSQL idempotently
            ins, upd, unc, dele = self._repository.persist_job_skills(
                market_job_id=job.id,
                skills=extracted,
                db=db,
                reconcile=reconcile,
            )

            metrics.persistence_inserts += ins
            metrics.persistence_updates += upd
            metrics.persistence_unchanged += unc
            metrics.persistence_deletions += dele

        metrics.unique_skill_relationships = len(unique_skill_ids)
        metrics.top_skills = sorted(skill_counter.items(), key=lambda x: (-x[1], x[0]))

        if commit:
            db.commit()

        logger.info(
            "Market skill extraction batch completed: processed=%d, with_skills=%d, "
            "no_skills=%d, matched=%d, unique_skills=%d, inserts=%d, updates=%d, unchanged=%d, deletions=%d",
            metrics.jobs_processed,
            metrics.jobs_with_skills,
            metrics.jobs_without_skills,
            metrics.skills_matched,
            metrics.unique_skill_relationships,
            metrics.persistence_inserts,
            metrics.persistence_updates,
            metrics.persistence_unchanged,
            metrics.persistence_deletions,
        )

        return metrics
