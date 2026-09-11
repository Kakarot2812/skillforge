"""
Historical market skill demand snapshot service for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-F.

Provides immutable, point-in-time snapshots of market skill demand.
Core principles:
- "The LLM never decides what is true."
- Purely deterministic, historical record persistence.
- Immutable snapshots: snapshots once written are never updated or deleted by normal operations.
- Deterministic idempotency: submitting an identical snapshot at the same timestamp produces no new rows.
- Conflict rejection: submitting conflicting values for an existing (source, skill, timestamp) is rejected.
- Strict isolation from frozen MVP skill_demand records.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional, Tuple
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import MarketSkillDemand, MarketSkillDemandSnapshot, Skill
from app.services.market.models import MarketDemandSnapshotRecord

logger = logging.getLogger(__name__)


class MarketDemandSnapshotConflictError(ValueError):
    """Raised when an attempt is made to overwrite an existing historical snapshot with conflicting data."""
    pass


class MarketSkillDemandSnapshotRepository:
    """
    Persistence and query layer for immutable market skill demand snapshots.
    """

    def persist_snapshot(
        self,
        records: List[MarketDemandSnapshotRecord],
        source: str,
        snapshot_at: datetime,
        db: Session,
    ) -> Tuple[int, int, List[MarketSkillDemandSnapshot]]:
        """
        Persists snapshot records for a given source and snapshot_at timestamp.

        Enforces:
        - If no records exist for (source, snapshot_at): inserts all records.
        - If identical records already exist for (source, snapshot_at): returns (0, count) idempotently.
        - If conflicting records exist for (source, snapshot_at): raises MarketDemandSnapshotConflictError.

        Returns:
            Tuple of (inserted_count, unchanged_count, persisted_entities)
        """
        clean_source = source.strip() if source else "adzuna"

        # Query existing snapshot rows for this (source, snapshot_at)
        existing_rows: List[MarketSkillDemandSnapshot] = (
            db.query(MarketSkillDemandSnapshot)
            .filter(
                MarketSkillDemandSnapshot.source == clean_source,
                MarketSkillDemandSnapshot.snapshot_at == snapshot_at,
            )
            .all()
        )

        if existing_rows:
            # Check for identical vs conflicting data
            existing_map: Dict[uuid.UUID, MarketSkillDemandSnapshot] = {
                row.skill_id: row for row in existing_rows
            }
            incoming_map: Dict[uuid.UUID, MarketDemandSnapshotRecord] = {
                (uuid.UUID(str(rec.skill_id)) if not isinstance(rec.skill_id, uuid.UUID) else rec.skill_id): rec
                for rec in records
            }

            if set(existing_map.keys()) != set(incoming_map.keys()):
                raise MarketDemandSnapshotConflictError(
                    f"Conflicting snapshot: skill set mismatch for source '{clean_source}' at timestamp {snapshot_at.isoformat()}. "
                    f"Existing skills: {len(existing_map)}, incoming skills: {len(incoming_map)}"
                )

            for skill_id, incoming_rec in incoming_map.items():
                existing = existing_map[skill_id]
                if (
                    existing.job_count != incoming_rec.job_count
                    or existing.sample_size != incoming_rec.sample_size
                    or abs(float(existing.demand_share) - float(incoming_rec.demand_share)) > 1e-6
                    or abs(float(existing.demand_score) - float(incoming_rec.demand_score)) > 1e-6
                ):
                    raise MarketDemandSnapshotConflictError(
                        f"Conflicting snapshot values detected for skill {skill_id} in source '{clean_source}' at {snapshot_at.isoformat()}: "
                        f"existing=(count={existing.job_count}, sample={existing.sample_size}, score={existing.demand_score}) vs "
                        f"incoming=(count={incoming_rec.job_count}, sample={incoming_rec.sample_size}, score={incoming_rec.demand_score})"
                    )

            logger.info(
                "Idempotent snapshot detected for source '%s' at %s: %d records unchanged.",
                clean_source,
                snapshot_at.isoformat(),
                len(existing_rows),
            )
            return (0, len(existing_rows), existing_rows)

        # No existing records: persist new immutable snapshot rows
        persisted_entities: List[MarketSkillDemandSnapshot] = []
        for rec in records:
            skill_uuid = uuid.UUID(str(rec.skill_id)) if not isinstance(rec.skill_id, uuid.UUID) else rec.skill_id
            snapshot_entity = MarketSkillDemandSnapshot(
                id=rec.id or uuid.uuid4(),
                skill_id=skill_uuid,
                source=clean_source,
                job_count=rec.job_count,
                sample_size=rec.sample_size,
                demand_share=rec.demand_share,
                demand_score=rec.demand_score,
                snapshot_at=snapshot_at,
            )
            db.add(snapshot_entity)
            persisted_entities.append(snapshot_entity)

        db.flush()
        logger.info(
            "Persisted %d new historical snapshot records for source '%s' at %s.",
            len(persisted_entities),
            clean_source,
            snapshot_at.isoformat(),
        )
        return (len(persisted_entities), 0, persisted_entities)

    def get_latest_snapshot_timestamps(
        self,
        db: Session,
        source: str = "adzuna",
        limit: int = 2,
    ) -> List[datetime]:
        """
        Returns the latest distinct snapshot timestamps for a source,
        ordered descending (newest first).
        """
        clean_source = source.strip() if source else "adzuna"
        rows = (
            db.query(MarketSkillDemandSnapshot.snapshot_at)
            .filter(MarketSkillDemandSnapshot.source == clean_source)
            .distinct()
            .order_by(MarketSkillDemandSnapshot.snapshot_at.desc())
            .limit(limit)
            .all()
        )
        return [r[0] for r in rows]

    def get_snapshots_at(
        self,
        db: Session,
        snapshot_at: datetime,
        source: str = "adzuna",
    ) -> List[MarketSkillDemandSnapshot]:
        """
        Retrieves all snapshot records for a given timestamp and source.
        """
        clean_source = source.strip() if source else "adzuna"
        return (
            db.query(MarketSkillDemandSnapshot)
            .filter(
                MarketSkillDemandSnapshot.source == clean_source,
                MarketSkillDemandSnapshot.snapshot_at == snapshot_at,
            )
            .order_by(
                MarketSkillDemandSnapshot.demand_score.desc(),
                MarketSkillDemandSnapshot.skill_id.asc(),
            )
            .all()
        )

    def count_snapshot_rows(
        self,
        db: Session,
        source: Optional[str] = None,
    ) -> int:
        """Returns total row count in market_skill_demand_snapshots."""
        query = db.query(func.count(MarketSkillDemandSnapshot.id))
        if source:
            query = query.filter(MarketSkillDemandSnapshot.source == source.strip())
        return query.scalar() or 0


class MarketDemandSnapshotService:
    """
    Domain service for creating and querying historical market skill demand snapshots.
    """

    def __init__(
        self,
        repository: Optional[MarketSkillDemandSnapshotRepository] = None,
    ):
        self._repository = repository or MarketSkillDemandSnapshotRepository()

    @property
    def repository(self) -> MarketSkillDemandSnapshotRepository:
        return self._repository

    def create_snapshot_from_current_demand(
        self,
        db: Session,
        source: str = "adzuna",
        snapshot_at: Optional[datetime] = None,
        commit: bool = True,
    ) -> Tuple[List[MarketSkillDemandSnapshot], int, int]:
        """
        Captures the current market_skill_demand records for a source into an immutable snapshot.

        Args:
            db: Active database session.
            source: Source identifier (default 'adzuna').
            snapshot_at: Explicit snapshot timestamp. If None, current UTC time is used.
            commit: Whether to commit the session.

        Returns:
            Tuple of (persisted_snapshot_entities, inserted_count, unchanged_count)
        """
        clean_source = source.strip() if source else "adzuna"
        if snapshot_at is None:
            snapshot_at = datetime.now(timezone.utc)
        elif snapshot_at.tzinfo is None:
            snapshot_at = snapshot_at.replace(tzinfo=timezone.utc)

        # 1. Read current market_skill_demand for this source
        current_demands: List[Tuple[MarketSkillDemand, str]] = (
            db.query(MarketSkillDemand, Skill.name.label("skill_name"))
            .join(Skill, Skill.id == MarketSkillDemand.skill_id)
            .filter(MarketSkillDemand.source == clean_source)
            .order_by(
                MarketSkillDemand.demand_score.desc(),
                MarketSkillDemand.job_count.desc(),
                MarketSkillDemand.skill_id.asc(),
            )
            .all()
        )

        records: List[MarketDemandSnapshotRecord] = []
        for demand, skill_name in current_demands:
            rec = MarketDemandSnapshotRecord(
                id=uuid.uuid4(),
                skill_id=demand.skill_id,
                canonical_skill_name=skill_name,
                source=clean_source,
                job_count=demand.job_count,
                sample_size=demand.sample_size,
                demand_share=demand.demand_share,
                demand_score=demand.demand_score,
                snapshot_at=snapshot_at,
            )
            records.append(rec)

        # 2. Persist snapshot idempotently
        inserted, unchanged, entities = self._repository.persist_snapshot(
            records=records,
            source=clean_source,
            snapshot_at=snapshot_at,
            db=db,
        )

        if commit:
            db.commit()

        return (entities, inserted, unchanged)

    def get_latest_snapshot_timestamps(
        self,
        db: Session,
        source: str = "adzuna",
        limit: int = 2,
    ) -> List[datetime]:
        """Retrieves latest snapshot timestamps for source."""
        return self._repository.get_latest_snapshot_timestamps(db=db, source=source, limit=limit)

    def get_snapshots_at(
        self,
        db: Session,
        snapshot_at: datetime,
        source: str = "adzuna",
    ) -> List[MarketSkillDemandSnapshot]:
        """Retrieves snapshot records at a specific timestamp for source."""
        return self._repository.get_snapshots_at(db=db, snapshot_at=snapshot_at, source=source)
