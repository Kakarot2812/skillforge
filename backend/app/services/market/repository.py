"""
Market job repository service for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-C.

Implements PostgreSQL-native idempotent persistence for NormalizedMarketJob records.
Guarantees:
- Idempotent upsert on (source, external_job_id).
- Non-destructive updates (preserves existing field values if incoming is None).
- Deterministic tracking of persistence metrics (attempted, inserted, updated, unchanged, failed).
- Strict isolation from MVP skill_demand table and zero credential storage.
"""

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func, literal_column
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import MarketJob, MarketJobSkill
from app.services.market.models import MarketJobSkillEvidence, NormalizedMarketJob

logger = logging.getLogger(__name__)


@dataclass
class PersistenceMetrics:
    """
    Summary metrics for a batch persistence operation.
    Guaranteed free of credentials or sensitive headers.
    """
    attempted: int = 0
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "attempted": self.attempted,
            "inserted": self.inserted,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "failed": self.failed,
        }


def parse_iso_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Safely parses ISO 8601 timestamp strings from upstream job payloads."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


class MarketJobRepository:
    """
    Data access and idempotent persistence layer for market jobs.
    Uses PostgreSQL-native ON CONFLICT (source, external_job_id) DO UPDATE.
    """

    def persist_job(
        self,
        job: NormalizedMarketJob,
        db: Session,
    ) -> Tuple[Optional[uuid.UUID], str]:
        """
        Idempotently persists a single NormalizedMarketJob record.

        Returns:
            Tuple of (job_id, status) where status is 'inserted', 'updated', or 'unchanged'.

        Raises:
            ValueError: If job lacks valid source or external_job_id.
            Exception: If database execution fails.
        """
        if not job.source or not job.source.strip():
            raise ValueError("job.source cannot be empty")
        if not job.external_job_id or not job.external_job_id.strip():
            raise ValueError("job.external_job_id cannot be empty")
        if not job.title or not job.title.strip():
            raise ValueError("job.title cannot be empty")

        clean_source = job.source.strip()
        clean_ext_id = job.external_job_id.strip()
        created_dt = parse_iso_datetime(job.created_at)
        raw_payload = job.raw_data if isinstance(job.raw_data, dict) else {}

        # Construct PostgreSQL native upsert statement
        stmt = pg_insert(MarketJob).values(
            id=uuid.uuid4(),
            source=clean_source,
            external_job_id=clean_ext_id,
            title=job.title.strip(),
            description=job.description,
            company_name=job.company_name,
            location=job.location,
            category=job.category,
            contract_type=job.contract_type,
            contract_time=job.contract_time,
            created_at=created_dt,
            redirect_url=job.redirect_url,
            raw_data=raw_payload,
        )

        # Coalesce: incoming None values will NOT overwrite existing non-null data
        update_set = {
            "title": stmt.excluded.title,
            "description": func.coalesce(stmt.excluded.description, MarketJob.description),
            "company_name": func.coalesce(stmt.excluded.company_name, MarketJob.company_name),
            "location": func.coalesce(stmt.excluded.location, MarketJob.location),
            "category": func.coalesce(stmt.excluded.category, MarketJob.category),
            "contract_type": func.coalesce(stmt.excluded.contract_type, MarketJob.contract_type),
            "contract_time": func.coalesce(stmt.excluded.contract_time, MarketJob.contract_time),
            "created_at": func.coalesce(stmt.excluded.created_at, MarketJob.created_at),
            "redirect_url": func.coalesce(stmt.excluded.redirect_url, MarketJob.redirect_url),
            "raw_data": stmt.excluded.raw_data,
            "updated_at": func.now(),
        }

        # Only perform the UPDATE if at least one meaningful field actually changed
        where_condition = (
            (MarketJob.title.is_distinct_from(stmt.excluded.title)) |
            (stmt.excluded.description.isnot(None) & MarketJob.description.is_distinct_from(stmt.excluded.description)) |
            (stmt.excluded.company_name.isnot(None) & MarketJob.company_name.is_distinct_from(stmt.excluded.company_name)) |
            (stmt.excluded.location.isnot(None) & MarketJob.location.is_distinct_from(stmt.excluded.location)) |
            (stmt.excluded.category.isnot(None) & MarketJob.category.is_distinct_from(stmt.excluded.category)) |
            (stmt.excluded.contract_type.isnot(None) & MarketJob.contract_type.is_distinct_from(stmt.excluded.contract_type)) |
            (stmt.excluded.contract_time.isnot(None) & MarketJob.contract_time.is_distinct_from(stmt.excluded.contract_time)) |
            (stmt.excluded.created_at.isnot(None) & MarketJob.created_at.is_distinct_from(stmt.excluded.created_at)) |
            (stmt.excluded.redirect_url.isnot(None) & MarketJob.redirect_url.is_distinct_from(stmt.excluded.redirect_url)) |
            (MarketJob.raw_data.is_distinct_from(stmt.excluded.raw_data))
        )

        upsert_stmt = (
            stmt.on_conflict_do_update(
                constraint="uq_market_jobs_source_external_job_id",
                set_=update_set,
                where=where_condition,
            )
            .returning(MarketJob.id, literal_column("(xmax = 0)").label("is_inserted"))
        )

        result_row = db.execute(upsert_stmt).fetchone()

        if result_row is None:
            # Conflict occurred and no fields differed -> row was unchanged
            existing = self.get_job(clean_source, clean_ext_id, db)
            existing_id = existing.id if existing else None
            return (existing_id, "unchanged")

        row_id, is_inserted = result_row
        status = "inserted" if is_inserted else "updated"
        return (row_id, status)

    def persist_jobs(
        self,
        jobs: List[NormalizedMarketJob],
        db: Session,
        commit: bool = True,
    ) -> PersistenceMetrics:
        """
        Persists a collection of NormalizedMarketJob records within a transaction.

        Args:
            jobs: Collection of normalized market jobs.
            db: Active SQLAlchemy database session.
            commit: Whether to commit the transaction upon completion.

        Returns:
            PersistenceMetrics containing detailed audit counts.
        """
        metrics = PersistenceMetrics(attempted=len(jobs))

        if not jobs:
            return metrics

        for job in jobs:
            try:
                _, status = self.persist_job(job, db)
                if status == "inserted":
                    metrics.inserted += 1
                elif status == "updated":
                    metrics.updated += 1
                elif status == "unchanged":
                    metrics.unchanged += 1
            except Exception as exc:
                metrics.failed += 1
                logger.error(
                    "Failed to persist job (source=%s, external_id=%s): %s",
                    getattr(job, "source", None),
                    getattr(job, "external_job_id", None),
                    exc,
                )
                raise exc

        if commit:
            db.commit()

        logger.info(
            "Market job persistence finished: attempted=%d, inserted=%d, updated=%d, unchanged=%d, failed=%d",
            metrics.attempted,
            metrics.inserted,
            metrics.updated,
            metrics.unchanged,
            metrics.failed,
        )

        return metrics

    def get_job(
        self,
        source: str,
        external_job_id: str,
        db: Session,
    ) -> Optional[MarketJob]:
        """Retrieves a single MarketJob by its unique natural key."""
        return (
            db.query(MarketJob)
            .filter(
                MarketJob.source == source.strip(),
                MarketJob.external_job_id == external_job_id.strip(),
            )
            .first()
        )

    def count_jobs(
        self,
        db: Session,
        source: Optional[str] = None,
    ) -> int:
        """Returns the total number of market jobs, optionally filtered by source."""
        query = db.query(func.count(MarketJob.id))
        if source:
            query = query.filter(MarketJob.source == source.strip())
        return query.scalar() or 0


class MarketJobSkillRepository:
    """
    Data access and idempotent persistence layer for market job extracted skills.
    Post-MVP Phase 1, Checkpoint P1-D.

    Uses PostgreSQL-native ON CONFLICT (market_job_id, skill_id) DO UPDATE.
    Guarantees:
    - Exactly one relationship per canonical skill per job.
    - Idempotent execution (duplicate extraction runs do not create duplicate rows).
    - Deterministic reconciliation to purge stale skills when job description changes.
    - Preserves verbatim evidence snippet and extraction metadata.
    """

    def persist_job_skills(
        self,
        market_job_id: uuid.UUID,
        skills: List[MarketJobSkillEvidence],
        db: Session,
        reconcile: bool = True,
    ) -> Tuple[int, int, int, int]:
        """
        Idempotently persists a list of extracted skills for a given market job.

        Args:
            market_job_id: UUID of the parent MarketJob.
            skills: List of unique MarketJobSkillEvidence items to persist.
            db: Active database session.
            reconcile: If True, deletes existing MarketJobSkill records for this
                       job whose skill_id is not in the new extracted skill set.

        Returns:
            Tuple of (inserted, updated, unchanged, deleted) counts.
        """
        inserted = 0
        updated = 0
        unchanged = 0
        deleted = 0

        # Deterministic reconciliation: delete stale skills no longer present in extracted set
        if reconcile:
            new_skill_ids = [s.skill_id for s in skills]
            if new_skill_ids:
                deleted = (
                    db.query(MarketJobSkill)
                    .filter(
                        MarketJobSkill.market_job_id == market_job_id,
                        MarketJobSkill.skill_id.notin_(new_skill_ids),
                    )
                    .delete(synchronize_session=False)
                )
            else:
                deleted = (
                    db.query(MarketJobSkill)
                    .filter(MarketJobSkill.market_job_id == market_job_id)
                    .delete(synchronize_session=False)
                )

        if not skills:
            return (inserted, updated, unchanged, deleted)

        for ev in skills:
            stmt = pg_insert(MarketJobSkill).values(
                id=uuid.uuid4(),
                market_job_id=market_job_id,
                skill_id=ev.skill_id,
                matched_alias=ev.matched_alias,
                source_field=ev.source_field,
                evidence_text=ev.evidence_text,
                extraction_method=ev.extraction_method,
                confidence_score=ev.confidence_score,
                extracted_at=func.now(),
            )

            update_set = {
                "matched_alias": stmt.excluded.matched_alias,
                "source_field": stmt.excluded.source_field,
                "evidence_text": stmt.excluded.evidence_text,
                "extraction_method": stmt.excluded.extraction_method,
                "confidence_score": stmt.excluded.confidence_score,
                "extracted_at": stmt.excluded.extracted_at,
            }

            where_condition = (
                (MarketJobSkill.matched_alias.is_distinct_from(stmt.excluded.matched_alias)) |
                (MarketJobSkill.source_field.is_distinct_from(stmt.excluded.source_field)) |
                (MarketJobSkill.evidence_text.is_distinct_from(stmt.excluded.evidence_text)) |
                (MarketJobSkill.extraction_method.is_distinct_from(stmt.excluded.extraction_method)) |
                (MarketJobSkill.confidence_score.is_distinct_from(stmt.excluded.confidence_score))
            )

            upsert_stmt = (
                stmt.on_conflict_do_update(
                    constraint="uq_market_job_skills_job_skill",
                    set_=update_set,
                    where=where_condition,
                )
                .returning(MarketJobSkill.id, literal_column("(xmax = 0)").label("is_inserted"))
            )

            result_row = db.execute(upsert_stmt).fetchone()

            if result_row is None:
                unchanged += 1
            elif result_row.is_inserted:
                inserted += 1
            else:
                updated += 1

        return (inserted, updated, unchanged, deleted)

    def get_skills_for_job(
        self,
        market_job_id: uuid.UUID,
        db: Session,
    ) -> List[MarketJobSkill]:
        """Retrieves all MarketJobSkill records for a given market job."""
        return (
            db.query(MarketJobSkill)
            .filter(MarketJobSkill.market_job_id == market_job_id)
            .order_by(MarketJobSkill.extracted_at.asc())
            .all()
        )

    def count_job_skills(
        self,
        db: Session,
        market_job_id: Optional[uuid.UUID] = None,
    ) -> int:
        """Returns the total number of market job skill relationships, optionally for a specific job."""
        query = db.query(func.count(MarketJobSkill.id))
        if market_job_id:
            query = query.filter(MarketJobSkill.market_job_id == market_job_id)
        return query.scalar() or 0

    def delete_skills_for_job(
        self,
        market_job_id: uuid.UUID,
        db: Session,
    ) -> int:
        """Deletes all extracted skill records for a given market job."""
        return (
            db.query(MarketJobSkill)
            .filter(MarketJobSkill.market_job_id == market_job_id)
            .delete(synchronize_session=False)
        )

