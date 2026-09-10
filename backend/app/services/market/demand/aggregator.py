"""
Deterministic market demand aggregation engine for SkillForge AI.
Post-MVP Phase 1, Checkpoint P1-E.

Aggregates persisted market job skill evidence into live/computed market-demand snapshots.
Core principles:
- Deterministic aggregation: "The LLM never decides what is true."
- Zero LLMs, Qwen, embeddings, vector similarity, or semantic inference.
- Exactly one job count per canonical skill per unique market job posting.
- Pure database set-based aggregation via COUNT(DISTINCT market_job_id).
- Strictly isolated from frozen MVP skill_demand records.
"""

from datetime import datetime, timezone
import logging
from typing import List, Optional, Tuple
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import MarketJob, MarketJobSkill, Skill
from app.services.market.demand.repository import MarketSkillDemandRepository
from app.services.market.models import (
    MarketDemandAggregationMetrics,
    MarketSkillDemandRecord,
)

logger = logging.getLogger(__name__)


def calculate_demand_metrics(job_count: int, sample_size: int) -> Tuple[float, float]:
    """
    Deterministically computes bounded demand_share and demand_score.

    Args:
        job_count: Number of unique jobs demanding the skill.
        sample_size: Total jobs evaluated in the market sample.

    Returns:
        Tuple of (demand_share, demand_score) clamped to [0.0, 1.0].
    """
    if sample_size <= 0 or job_count <= 0:
        return (0.0, 0.0)

    raw_share = float(job_count) / float(sample_size)
    clamped_share = max(0.0, min(1.0, raw_share))
    demand_score = round(clamped_share, 4)
    return (clamped_share, demand_score)


class MarketDemandAggregator:
    """
    Orchestration service for aggregating persisted market jobs and extracted skills
    into live, snapshot-based market demand metrics.
    Post-MVP Phase 1, Checkpoint P1-E.
    """

    def __init__(
        self,
        repository: Optional[MarketSkillDemandRepository] = None,
    ):
        """Initializes aggregator with an optional custom repository instance."""
        self._repository = repository or MarketSkillDemandRepository()

    @property
    def repository(self) -> MarketSkillDemandRepository:
        return self._repository

    def aggregate_market_demand(
        self,
        db: Session,
        source: str = "adzuna",
        reconcile: bool = True,
        commit: bool = True,
    ) -> MarketDemandAggregationMetrics:
        """
        Aggregates market demand for the given source scope from current database state.

        Args:
            db: Active database session.
            source: Target source identifier scope (default 'adzuna').
            reconcile: Whether to purge stale skills no longer demanded in this snapshot.
            commit: Whether to commit the database session upon completion.

        Returns:
            MarketDemandAggregationMetrics containing complete operational audit metrics.
        """
        clean_source = source.strip() if source else "adzuna"
        computed_at = datetime.now(timezone.utc)

        # 1. Calculate sample_size (total unique market jobs in source scope)
        sample_size_query = (
            db.query(func.count(MarketJob.id))
            .filter(MarketJob.source == clean_source)
        )
        sample_size: int = sample_size_query.scalar() or 0

        # 2. Database aggregation: count distinct market jobs per canonical skill
        query = (
            db.query(
                MarketJobSkill.skill_id,
                Skill.name.label("skill_name"),
                func.count(func.distinct(MarketJobSkill.market_job_id)).label("job_count"),
            )
            .join(MarketJob, MarketJob.id == MarketJobSkill.market_job_id)
            .join(Skill, Skill.id == MarketJobSkill.skill_id)
            .filter(MarketJob.source == clean_source)
            .group_by(MarketJobSkill.skill_id, Skill.name)
            .order_by(
                func.count(func.distinct(MarketJobSkill.market_job_id)).desc(),
                Skill.name.asc(),
            )
        )
        aggregated_rows = query.all()

        # 3. Build snapshot records
        records: List[MarketSkillDemandRecord] = []
        for row in aggregated_rows:
            job_cnt = int(row.job_count)
            share, score = calculate_demand_metrics(job_cnt, sample_size)

            record = MarketSkillDemandRecord(
                skill_id=row.skill_id,
                canonical_skill_name=row.skill_name,
                source=clean_source,
                job_count=job_cnt,
                sample_size=sample_size,
                demand_share=share,
                demand_score=score,
                computed_at=computed_at,
            )
            records.append(record)

        # 4. Idempotently persist snapshot via repository
        ins, upd, unc, dele = self._repository.upsert_demand_records(
            records=records,
            source=clean_source,
            db=db,
            reconcile=reconcile,
        )

        if commit:
            db.commit()

        # 5. Assemble and return metrics
        total_relationships = sum(r.job_count for r in records)
        top_skills = [(r.canonical_skill_name, r.job_count, r.demand_score) for r in records[:10]]

        metrics = MarketDemandAggregationMetrics(
            source=clean_source,
            sample_size=sample_size,
            skills_with_demand=len(records),
            total_relationships=total_relationships,
            rows_inserted=ins,
            rows_updated=upd,
            rows_unchanged=unc,
            rows_deleted=dele,
            computed_at=computed_at,
            top_demanded_skills=top_skills,
        )

        logger.info(
            "Market demand aggregation completed for source '%s': sample_size=%d, skills_with_demand=%d, "
            "relationships=%d, inserts=%d, updates=%d, unchanged=%d, deletions=%d",
            clean_source,
            sample_size,
            len(records),
            total_relationships,
            ins,
            upd,
            unc,
            dele,
        )

        return metrics


def aggregate_market_demand(
    db: Session,
    source: str = "adzuna",
    reconcile: bool = True,
    commit: bool = True,
) -> MarketDemandAggregationMetrics:
    """Convenience function delegating to MarketDemandAggregator."""
    aggregator = MarketDemandAggregator()
    return aggregator.aggregate_market_demand(
        db=db,
        source=source,
        reconcile=reconcile,
        commit=commit,
    )
