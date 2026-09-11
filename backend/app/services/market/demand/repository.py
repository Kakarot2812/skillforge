"""
Market skill demand repository for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-E.

Implements PostgreSQL-native idempotent persistence for aggregated market skill demand snapshots.
Guarantees:
- Exactly one demand record per canonical skill per source snapshot.
- Idempotent upsert via ON CONFLICT (source, skill_id) DO UPDATE.
- Deterministic reconciliation to purge stale skills no longer demanded in the current snapshot.
- Strict isolation from frozen MVP skill_demand records and zero credential exposure.
"""

import logging
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func, literal_column
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import MarketSkillDemand
from app.services.market.models import MarketSkillDemandRecord

logger = logging.getLogger(__name__)


class MarketSkillDemandRepository:
    """
    Data access and idempotent persistence layer for computed market skill demand snapshots.
    Post-MVP Phase 1, Checkpoint P1-E.
    """

    def upsert_demand_records(
        self,
        records: List[MarketSkillDemandRecord],
        source: str,
        db: Session,
        reconcile: bool = True,
    ) -> Tuple[int, int, int, int]:
        """
        Idempotently persists a list of aggregated skill demand records for a given source.

        Args:
            records: Collection of MarketSkillDemandRecord items to persist.
            source: Source identifier scope (e.g., 'adzuna').
            db: Active database session.
            reconcile: If True, deletes existing MarketSkillDemand records for this
                       source whose skill_id is not in the active records list.

        Returns:
            Tuple of (inserted, updated, unchanged, deleted) counts.
        """
        clean_source = source.strip() if source else "adzuna"
        inserted = 0
        updated = 0
        unchanged = 0
        deleted = 0

        # Deterministic reconciliation: purge stale records for this source no longer in the snapshot
        if reconcile:
            if records:
                active_skill_ids = [r.skill_id for r in records]
                deleted = (
                    db.query(MarketSkillDemand)
                    .filter(
                        MarketSkillDemand.source == clean_source,
                        MarketSkillDemand.skill_id.notin_(active_skill_ids),
                    )
                    .delete(synchronize_session=False)
                )
            else:
                deleted = (
                    db.query(MarketSkillDemand)
                    .filter(MarketSkillDemand.source == clean_source)
                    .delete(synchronize_session=False)
                )

        if not records:
            return (inserted, updated, unchanged, deleted)

        for rec in records:
            stmt = pg_insert(MarketSkillDemand).values(
                id=uuid.uuid4(),
                skill_id=rec.skill_id,
                source=clean_source,
                job_count=rec.job_count,
                sample_size=rec.sample_size,
                demand_share=rec.demand_share,
                demand_score=rec.demand_score,
                computed_at=func.now(),
            )

            update_set = {
                "job_count": stmt.excluded.job_count,
                "sample_size": stmt.excluded.sample_size,
                "demand_share": stmt.excluded.demand_share,
                "demand_score": stmt.excluded.demand_score,
                "computed_at": stmt.excluded.computed_at,
            }

            where_condition = (
                (MarketSkillDemand.job_count.is_distinct_from(stmt.excluded.job_count)) |
                (MarketSkillDemand.sample_size.is_distinct_from(stmt.excluded.sample_size)) |
                (MarketSkillDemand.demand_share.is_distinct_from(stmt.excluded.demand_share)) |
                (MarketSkillDemand.demand_score.is_distinct_from(stmt.excluded.demand_score))
            )

            upsert_stmt = (
                stmt.on_conflict_do_update(
                    constraint="uq_market_skill_demand_source_skill",
                    set_=update_set,
                    where=where_condition,
                )
                .returning(MarketSkillDemand.id, literal_column("(xmax = 0)").label("is_inserted"))
            )

            result_row = db.execute(upsert_stmt).fetchone()

            if result_row is None:
                unchanged += 1
            elif result_row.is_inserted:
                inserted += 1
            else:
                updated += 1

        logger.debug(
            "Market skill demand snapshot upserted for source '%s': inserted=%d, updated=%d, unchanged=%d, deleted=%d",
            clean_source,
            inserted,
            updated,
            unchanged,
            deleted,
        )

        return (inserted, updated, unchanged, deleted)

    def get_demand_for_source(
        self,
        source: str,
        db: Session,
    ) -> List[MarketSkillDemand]:
        """
        Retrieves all computed demand records for a specific source,
        ordered deterministically by demand_score DESC, job_count DESC, skill_id ASC.
        """
        clean_source = source.strip() if source else "adzuna"
        return (
            db.query(MarketSkillDemand)
            .filter(MarketSkillDemand.source == clean_source)
            .order_by(
                MarketSkillDemand.demand_score.desc(),
                MarketSkillDemand.job_count.desc(),
                MarketSkillDemand.skill_id.asc(),
            )
            .all()
        )

    def get_demand_by_skill(
        self,
        skill_id: uuid.UUID,
        source: str,
        db: Session,
    ) -> Optional[MarketSkillDemand]:
        """Retrieves a single computed demand record for a skill and source."""
        clean_source = source.strip() if source else "adzuna"
        return (
            db.query(MarketSkillDemand)
            .filter(
                MarketSkillDemand.skill_id == skill_id,
                MarketSkillDemand.source == clean_source,
            )
            .first()
        )

    def count_records(
        self,
        db: Session,
        source: Optional[str] = None,
    ) -> int:
        """Returns the total number of market skill demand records, optionally filtered by source."""
        query = db.query(func.count(MarketSkillDemand.id))
        if source:
            query = query.filter(MarketSkillDemand.source == source.strip())
        return query.scalar() or 0

    def delete_by_source(
        self,
        source: str,
        db: Session,
    ) -> int:
        """Deletes all demand records for a specific source."""
        clean_source = source.strip() if source else "adzuna"
        return (
            db.query(MarketSkillDemand)
            .filter(MarketSkillDemand.source == clean_source)
            .delete(synchronize_session=False)
        )
