"""
Deterministic historical market skill demand growth service for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-F.

Calculates and materializes deterministic growth between comparable historical snapshots.
Core principles:
- "The LLM never decides what is true."
- Purely deterministic mathematical calculation.
- Zero division safety and explicit zero-base emergence handling.
- Compares CURRENT snapshot against IMMEDIATELY PRECEDING snapshot for the SAME source and canonical skill.
- Materializes current growth in market_skill_demand_growth while keeping snapshots immutable.
- Strictly isolated from frozen MVP skill_demand records.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func, literal_column
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models import (
    MarketSkillDemandGrowth,
    MarketSkillDemandSnapshot,
    Skill,
)
from app.services.market.demand.snapshots import (
    MarketDemandSnapshotService,
    MarketSkillDemandSnapshotRepository,
)
from app.services.market.models import MarketDemandGrowthRecord

logger = logging.getLogger(__name__)


def calculate_growth_rate(current_demand_score: float, previous_demand_score: float) -> float:
    """
    Deterministically computes growth rate between current and previous demand scores.

    Formula:
        growth_rate = (current_demand_score - previous_demand_score) / previous_demand_score
        rounded to 4 decimal places.

    Zero Base Rules:
    - If previous == 0 and current > 0: growth_rate = 1.0 (+100% emergence)
    - If previous == 0 and current == 0: growth_rate = 0.0 (baseline zero)
    - If previous > 0: standard formula, rounded to 4 decimal places.
    """
    curr = float(current_demand_score)
    prev = float(previous_demand_score)

    if prev == 0.0:
        if curr > 0.0:
            return 1.0
        return 0.0

    raw_rate = (curr - prev) / prev
    return round(raw_rate, 4)


def classify_growth_rate(growth_rate: float) -> str:
    """
    Deterministic classification based strictly on growth_rate thresholds:
    - RISING: growth_rate > 0.05
    - STABLE: -0.05 <= growth_rate <= 0.05
    - DECLINING: growth_rate < -0.05

    Boundary examples:
    - 0.06  -> RISING
    - 0.05  -> STABLE
    - 0.00  -> STABLE
    - -0.05 -> STABLE
    - -0.06 -> DECLINING
    """
    if growth_rate > 0.05:
        return "RISING"
    elif growth_rate < -0.05:
        return "DECLINING"
    else:
        return "STABLE"


class MarketSkillDemandGrowthRepository:
    """
    Persistence and query layer for current materialized market skill demand growth.
    """

    def upsert_growth_records(
        self,
        records: List[MarketDemandGrowthRecord],
        source: str,
        db: Session,
    ) -> Tuple[int, int, int]:
        """
        Idempotently persists or updates growth records for a source.

        Returns:
            Tuple of (inserted, updated, unchanged) counts.
        """
        clean_source = source.strip() if source else "adzuna"
        inserted = 0
        updated = 0
        unchanged = 0

        if not records:
            return (0, 0, 0)

        for rec in records:
            skill_uuid = uuid.UUID(str(rec.skill_id)) if not isinstance(rec.skill_id, uuid.UUID) else rec.skill_id
            curr_uuid = (
                uuid.UUID(str(rec.current_snapshot_id))
                if not isinstance(rec.current_snapshot_id, uuid.UUID)
                else rec.current_snapshot_id
            )
            prev_uuid = (
                uuid.UUID(str(rec.previous_snapshot_id))
                if rec.previous_snapshot_id and not isinstance(rec.previous_snapshot_id, uuid.UUID)
                else rec.previous_snapshot_id
            )

            stmt = pg_insert(MarketSkillDemandGrowth).values(
                id=rec.id or uuid.uuid4(),
                skill_id=skill_uuid,
                source=clean_source,
                previous_snapshot_id=prev_uuid,
                current_snapshot_id=curr_uuid,
                previous_demand_score=rec.previous_demand_score,
                current_demand_score=rec.current_demand_score,
                growth_rate=rec.growth_rate,
                growth_class=rec.growth_class,
                computed_at=func.now(),
            )

            update_set = {
                "previous_snapshot_id": stmt.excluded.previous_snapshot_id,
                "current_snapshot_id": stmt.excluded.current_snapshot_id,
                "previous_demand_score": stmt.excluded.previous_demand_score,
                "current_demand_score": stmt.excluded.current_demand_score,
                "growth_rate": stmt.excluded.growth_rate,
                "growth_class": stmt.excluded.growth_class,
                "computed_at": stmt.excluded.computed_at,
            }

            where_condition = (
                (MarketSkillDemandGrowth.previous_snapshot_id.is_distinct_from(stmt.excluded.previous_snapshot_id))
                | (MarketSkillDemandGrowth.current_snapshot_id.is_distinct_from(stmt.excluded.current_snapshot_id))
                | (MarketSkillDemandGrowth.previous_demand_score.is_distinct_from(stmt.excluded.previous_demand_score))
                | (MarketSkillDemandGrowth.current_demand_score.is_distinct_from(stmt.excluded.current_demand_score))
                | (MarketSkillDemandGrowth.growth_rate.is_distinct_from(stmt.excluded.growth_rate))
                | (MarketSkillDemandGrowth.growth_class.is_distinct_from(stmt.excluded.growth_class))
            )

            upsert_stmt = (
                stmt.on_conflict_do_update(
                    constraint="uq_market_skill_demand_growth_source_skill",
                    set_=update_set,
                    where=where_condition,
                )
                .returning(
                    MarketSkillDemandGrowth.id,
                    literal_column("(xmax = 0)").label("is_inserted"),
                )
            )

            result_row = db.execute(upsert_stmt).fetchone()

            if result_row is None:
                unchanged += 1
            elif result_row.is_inserted:
                inserted += 1
            else:
                updated += 1

        db.flush()
        return (inserted, updated, unchanged)

    def get_growth_for_source(
        self,
        db: Session,
        source: str = "adzuna",
    ) -> List[MarketSkillDemandGrowth]:
        """Retrieves all current growth records for a source."""
        clean_source = source.strip() if source else "adzuna"
        return (
            db.query(MarketSkillDemandGrowth)
            .filter(MarketSkillDemandGrowth.source == clean_source)
            .order_by(
                MarketSkillDemandGrowth.growth_rate.desc(),
                MarketSkillDemandGrowth.current_demand_score.desc(),
                MarketSkillDemandGrowth.skill_id.asc(),
            )
            .all()
        )

    def get_growth_by_skill(
        self,
        db: Session,
        skill_id: uuid.UUID,
        source: str = "adzuna",
    ) -> Optional[MarketSkillDemandGrowth]:
        """Retrieves current growth record for a specific skill and source."""
        clean_source = source.strip() if source else "adzuna"
        return (
            db.query(MarketSkillDemandGrowth)
            .filter(
                MarketSkillDemandGrowth.skill_id == skill_id,
                MarketSkillDemandGrowth.source == clean_source,
            )
            .first()
        )

    def count_records(
        self,
        db: Session,
        source: Optional[str] = None,
    ) -> int:
        """Returns total row count in market_skill_demand_growth."""
        query = db.query(func.count(MarketSkillDemandGrowth.id))
        if source:
            query = query.filter(MarketSkillDemandGrowth.source == source.strip())
        return query.scalar() or 0


class MarketDemandGrowthService:
    """
    Domain service for computing and persisting deterministic market skill demand growth.
    """

    def __init__(
        self,
        snapshot_service: Optional[MarketDemandSnapshotService] = None,
        repository: Optional[MarketSkillDemandGrowthRepository] = None,
    ):
        self._snapshot_service = snapshot_service or MarketDemandSnapshotService()
        self._repository = repository or MarketSkillDemandGrowthRepository()

    @property
    def snapshot_service(self) -> MarketDemandSnapshotService:
        return self._snapshot_service

    @property
    def repository(self) -> MarketSkillDemandGrowthRepository:
        return self._repository

    def compute_and_persist_growth(
        self,
        db: Session,
        source: str = "adzuna",
        commit: bool = True,
    ) -> Tuple[List[MarketDemandGrowthRecord], int, int, int]:
        """
        Computes growth by comparing CURRENT snapshot against IMMEDIATELY PRECEDING snapshot
        for the given source, and persists the materialized results.

        Returns:
            Tuple of (records, inserted_count, updated_count, unchanged_count)
        """
        clean_source = source.strip() if source else "adzuna"

        # 1. Fetch latest 2 snapshot timestamps
        timestamps = self._snapshot_service.get_latest_snapshot_timestamps(
            db=db,
            source=clean_source,
            limit=2,
        )

        if not timestamps:
            logger.info("No snapshots found for source '%s'. Skipping growth calculation.", clean_source)
            return ([], 0, 0, 0)

        current_ts = timestamps[0]
        previous_ts = timestamps[1] if len(timestamps) > 1 else None

        current_snapshots = self._snapshot_service.get_snapshots_at(
            db=db,
            snapshot_at=current_ts,
            source=clean_source,
        )

        previous_snapshots = (
            self._snapshot_service.get_snapshots_at(db=db, snapshot_at=previous_ts, source=clean_source)
            if previous_ts
            else []
        )
        prev_map: Dict[uuid.UUID, MarketSkillDemandSnapshot] = {
            s.skill_id: s for s in previous_snapshots
        }

        # 2. Compute pairwise growth
        growth_records: List[MarketDemandGrowthRecord] = []
        computed_at = datetime.now(timezone.utc)

        for curr in current_snapshots:
            if previous_ts is None:
                # No previous snapshot exists in the system: deterministic baseline
                # Do not fabricate growth; establish baseline STABLE state
                record = MarketDemandGrowthRecord(
                    id=uuid.uuid4(),
                    skill_id=curr.skill_id,
                    source=clean_source,
                    previous_snapshot_id=None,
                    current_snapshot_id=curr.id,
                    previous_demand_score=0.0,
                    current_demand_score=curr.demand_score,
                    growth_rate=0.0,
                    growth_class="STABLE",
                    computed_at=computed_at,
                )
            else:
                prev = prev_map.get(curr.skill_id)
                if prev is not None:
                    # Same skill present in immediately preceding snapshot
                    prev_id = prev.id
                    prev_score = prev.demand_score
                    rate = calculate_growth_rate(curr.demand_score, prev_score)
                    classification = classify_growth_rate(rate)
                else:
                    # Newly appeared skill in current snapshot (not in immediately preceding)
                    prev_id = None
                    prev_score = 0.0
                    rate = calculate_growth_rate(curr.demand_score, 0.0)
                    classification = classify_growth_rate(rate)

                record = MarketDemandGrowthRecord(
                    id=uuid.uuid4(),
                    skill_id=curr.skill_id,
                    source=clean_source,
                    previous_snapshot_id=prev_id,
                    current_snapshot_id=curr.id,
                    previous_demand_score=prev_score,
                    current_demand_score=curr.demand_score,
                    growth_rate=rate,
                    growth_class=classification,
                    computed_at=computed_at,
                )
            growth_records.append(record)

        # 3. Upsert growth records
        inserted, updated, unchanged = self._repository.upsert_growth_records(
            records=growth_records,
            source=clean_source,
            db=db,
        )

        if commit:
            db.commit()

        logger.info(
            "Growth computed for source '%s': %d skills (inserted=%d, updated=%d, unchanged=%d)",
            clean_source,
            len(growth_records),
            inserted,
            updated,
            unchanged,
        )
        return (growth_records, inserted, updated, unchanged)
