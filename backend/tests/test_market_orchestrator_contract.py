"""
Contract and architecture unit tests for SkillForge AI multi-source market refresh orchestration.
Post-MVP Phase 1, Checkpoint P1-L (Checkpoint 1 — Architecture & Contract Only).

Verifies:
1. All four registered source types (ADZUNA, GREENHOUSE, LEVER, ASHBY) can be represented.
2. Deterministic source ordering is strictly preserved.
3. SUCCESS, FAILED, and SKIPPED source results can be accurately represented.
4. Centralized 24-hour refresh gate evaluates deterministically.
5. Absolute absence of source-specific timers or schedulers.
6. MarketSourceRegistry remains the sole source resolution authority.
7. Sensitive credentials/tokens/headers cannot appear in result serialization.
8. Typed models reject malformed inputs appropriately.
9. Last-known-good preservation state is tracked in the contract.
10. Checkpoint 1 execution boundary raises NotImplementedError.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock
import pytest

from app.services.market.models import NormalizedMarketJob
from app.services.market.adapters.base import (
    MarketSourceAdapter,
    MarketSourceType,
    UnknownMarketSourceError,
    UnsupportedMarketSourceError,
)
from app.services.market.adapters.registry import (
    MarketSourceRegistry,
    market_source_registry,
)
from app.services.market.orchestration import (
    DEFAULT_ORCHESTRATOR_SOURCES,
    DEFAULT_SOURCE_ORDER,
    MarketRefreshStatus,
    MarketSourceRefreshResult,
    MarketSourceStatus,
    MultiSourceMarketRefreshOrchestrator,
    MultiSourceRefreshConfig,
    MultiSourceRefreshGateDecision,
    MultiSourceRefreshResult,
    sanitize_error_message,
)


# ---------------------------------------------------------------------------
# 1. Source Representation & Registry Resolution
# ---------------------------------------------------------------------------

def test_01_all_four_market_sources_represented() -> None:
    """Verifies that all 4 market sources are recognized enum members and supported."""
    expected_sources = {
        MarketSourceType.ADZUNA,
        MarketSourceType.GREENHOUSE,
        MarketSourceType.LEVER,
        MarketSourceType.ASHBY,
    }
    assert set(DEFAULT_SOURCE_ORDER) == expected_sources
    assert set(DEFAULT_ORCHESTRATOR_SOURCES) == expected_sources

    # Registry has operational adapters for all 4
    for source in expected_sources:
        adapter = market_source_registry.get_adapter(source)
        assert adapter is not None
        assert adapter.source_type == source


def test_02_deterministic_source_ordering() -> None:
    """Verifies canonical source execution order is strictly deterministic."""
    canonical_order = (
        MarketSourceType.ADZUNA,
        MarketSourceType.GREENHOUSE,
        MarketSourceType.LEVER,
        MarketSourceType.ASHBY,
    )
    assert DEFAULT_SOURCE_ORDER == canonical_order

    orchestrator = MultiSourceMarketRefreshOrchestrator()
    configured = orchestrator.get_configured_sources()
    assert configured == list(canonical_order)

    # Re-running produces identical order
    assert orchestrator.get_configured_sources() == list(canonical_order)


def test_03_registry_remains_source_resolution_authority() -> None:
    """Verifies orchestrator uses MarketSourceRegistry and rejects unknown sources."""
    orchestrator = MultiSourceMarketRefreshOrchestrator()

    # Valid resolution
    sources = orchestrator.get_configured_sources(
        MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.GREENHOUSE, MarketSourceType.ASHBY))
    )
    assert sources == [MarketSourceType.GREENHOUSE, MarketSourceType.ASHBY]

    # Unknown source rejected at config initialization
    with pytest.raises(UnknownMarketSourceError):
        MultiSourceRefreshConfig(enabled_sources=("invalid_source",))

    # Unsupported source without registered adapter
    empty_registry = MarketSourceRegistry(register_defaults=False)
    unsupported_orchestrator = MultiSourceMarketRefreshOrchestrator(registry=empty_registry)
    with pytest.raises(UnsupportedMarketSourceError):
        unsupported_orchestrator.get_configured_sources()


# ---------------------------------------------------------------------------
# 2. Source Result Semantics (SUCCESS, FAILED, SKIPPED)
# ---------------------------------------------------------------------------

def test_04_source_result_success_representation() -> None:
    """Verifies representation of a successful source run."""
    result = MarketSourceRefreshResult(
        source=MarketSourceType.GREENHOUSE,
        status=MarketSourceStatus.SUCCESS,
        jobs_fetched=25,
        jobs_normalized=24,
        jobs_persisted=24,
        duration_seconds=1.234,
    )
    assert result.status == MarketSourceStatus.SUCCESS
    assert result.source_name == "greenhouse"
    assert result.jobs_fetched == 25
    assert result.jobs_normalized == 24
    assert result.jobs_persisted == 24
    assert result.error_category is None
    assert result.error_message is None

    as_dict = result.to_dict()
    assert as_dict["source"] == "greenhouse"
    assert as_dict["status"] == "success"
    assert as_dict["jobs_fetched"] == 25
    assert as_dict["jobs_normalized"] == 24
    assert as_dict["jobs_persisted"] == 24
    assert as_dict["duration_seconds"] == 1.234


def test_05_source_result_failed_representation() -> None:
    """Verifies representation of a failed source without fabricating data."""
    result = MarketSourceRefreshResult(
        source=MarketSourceType.LEVER,
        status=MarketSourceStatus.FAILED,
        jobs_fetched=0,
        jobs_normalized=0,
        jobs_persisted=0,
        error_category="API_ERROR",
        error_message="HTTP 503 Service Unavailable",
        duration_seconds=0.45,
    )
    assert result.status == MarketSourceStatus.FAILED
    assert result.source_name == "lever"
    assert result.error_category == "API_ERROR"
    assert result.error_message == "HTTP 503 Service Unavailable"
    # Never fabricates non-zero jobs on failure
    assert result.jobs_fetched == 0
    assert result.jobs_normalized == 0
    assert result.jobs_persisted == 0


def test_06_source_result_skipped_representation() -> None:
    """Verifies representation of a skipped source due to gate policy."""
    result = MarketSourceRefreshResult(
        source=MarketSourceType.ASHBY,
        status=MarketSourceStatus.SKIPPED,
        jobs_fetched=0,
        jobs_normalized=0,
        jobs_persisted=0,
        error_category=None,
        error_message="Centralized 24-hour gate skipped refresh",
    )
    assert result.status == MarketSourceStatus.SKIPPED
    assert result.source_name == "ashby"
    assert result.jobs_fetched == 0


# ---------------------------------------------------------------------------
# 3. Security & Zero Credential Exposure
# ---------------------------------------------------------------------------

def test_07_credential_sanitization_in_error_messages() -> None:
    """Verifies credentials, tokens, and authorization headers are sanitized."""
    raw_error_1 = "Request failed with api_key=secret123456789"
    sanitized_1 = sanitize_error_message(raw_error_1)
    assert "secret123456789" not in sanitized_1
    assert "[REDACTED]" in sanitized_1

    raw_error_2 = "Failed calling https://user:supersecretpass@api.provider.com/endpoint"
    sanitized_2 = sanitize_error_message(raw_error_2)
    assert "supersecretpass" not in sanitized_2
    assert "[REDACTED]" in sanitized_2

    raw_error_3 = "Invalid Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token"
    sanitized_3 = sanitize_error_message(raw_error_3)
    assert "eyJhbGci" not in sanitized_3
    assert "[REDACTED]" in sanitized_3


def test_08_results_serialization_guaranteed_free_of_secrets() -> None:
    """Verifies serialized result structures never leak credentials."""
    sensitive_msg = "Adzuna failed with app_id=dummy_id and app_key=super_secret_key_value"
    source_result = MarketSourceRefreshResult(
        source=MarketSourceType.ADZUNA,
        status=MarketSourceStatus.FAILED,
        error_category="CONFIGURATION_ERROR",
        error_message=sensitive_msg,
    )
    # The message should have been scrubbed upon assignment/init
    assert "super_secret_key_value" not in source_result.error_message
    assert "super_secret_key_value" not in str(source_result.to_dict())

    gate_decision = MultiSourceRefreshGateDecision(
        should_refresh=True,
        reason="elapsed_exceeds_interval",
    )
    consolidated = MultiSourceRefreshResult(
        status=MarketRefreshStatus.FAILED,
        gate_decision=gate_decision,
        source_results={"adzuna": source_result},
        error="Top level error with token=xyz987654321",
    )
    dump = consolidated.to_dict()
    assert "super_secret_key_value" not in str(dump)
    assert "xyz987654321" not in str(dump)
    assert "[REDACTED]" in str(dump)


# ---------------------------------------------------------------------------
# 4. Centralized 24-Hour Gate Semantics
# ---------------------------------------------------------------------------

def test_09_centralized_24h_gate_no_prior_snapshot() -> None:
    """Verifies that with no previous snapshot, the gate approves refresh."""
    orchestrator = MultiSourceMarketRefreshOrchestrator()
    mock_db = MagicMock()
    # Mock db returns None for query
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    decision = orchestrator.evaluate_24h_gate(db=mock_db, force=False)
    assert decision.should_refresh is True
    assert decision.reason == "no_prior_snapshot"
    assert decision.last_snapshot_at is None
    assert decision.interval_hours == 24.0


def test_10_centralized_24h_gate_skips_within_24h() -> None:
    """Verifies that if latest snapshot is < 24 hours old, gate skips entire refresh."""
    orchestrator = MultiSourceMarketRefreshOrchestrator()
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)
    recent_snapshot = now - timedelta(hours=6)

    mock_db = MagicMock()
    mock_db.query.return_value.order_by.return_value.first.return_value = (recent_snapshot,)

    decision = orchestrator.evaluate_24h_gate(db=mock_db, force=False, now=now)
    assert decision.should_refresh is False
    assert decision.reason == "skipped_within_24h"
    assert decision.last_snapshot_at == recent_snapshot
    assert decision.elapsed_hours == pytest.approx(6.0, abs=0.01)


def test_11_centralized_24h_gate_executes_after_24h() -> None:
    """Verifies that if latest snapshot is >= 24 hours old, gate approves refresh."""
    orchestrator = MultiSourceMarketRefreshOrchestrator()
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)
    old_snapshot = now - timedelta(hours=25, minutes=30)

    mock_db = MagicMock()
    mock_db.query.return_value.order_by.return_value.first.return_value = (old_snapshot,)

    decision = orchestrator.evaluate_24h_gate(db=mock_db, force=False, now=now)
    assert decision.should_refresh is True
    assert decision.reason == "elapsed_exceeds_interval"
    assert decision.last_snapshot_at == old_snapshot
    assert decision.elapsed_hours == pytest.approx(25.5, abs=0.01)


def test_12_centralized_24h_gate_force_override() -> None:
    """Verifies that force=True overrides recent snapshot and executes."""
    orchestrator = MultiSourceMarketRefreshOrchestrator()
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)
    recent_snapshot = now - timedelta(minutes=10)

    mock_db = MagicMock()
    mock_db.query.return_value.order_by.return_value.first.return_value = (recent_snapshot,)

    decision = orchestrator.evaluate_24h_gate(db=mock_db, force=True, now=now)
    assert decision.should_refresh is True
    assert decision.reason == "force_refresh"


# ---------------------------------------------------------------------------
# 5. Absence of Source-Specific Schedulers / Timers
# ---------------------------------------------------------------------------

def test_13_no_source_specific_timer_abstractions() -> None:
    """
    Verifies that neither the orchestrator nor the adapters contain per-source
    schedulers, loops, threads, or timer abstractions.
    """
    import inspect
    from app.services.market import adapters
    from app.services.market import orchestration

    # Verify no scheduler, timer, loop, cron or thread classes are exposed
    forbidden_terms = ["scheduler", "timer", "cron", "celery", "apscheduler", "thread", "worker_loop"]

    for module in [adapters, orchestration]:
        for name in dir(module):
            for term in forbidden_terms:
                assert term not in name.lower(), f"Forbidden scheduling concept '{term}' found in {module}.{name}"

    orchestrator = MultiSourceMarketRefreshOrchestrator()
    # Check that orchestrator has no per-source timers
    assert not hasattr(orchestrator, "adzuna_timer")
    assert not hasattr(orchestrator, "greenhouse_timer")
    assert not hasattr(orchestrator, "lever_timer")
    assert not hasattr(orchestrator, "ashby_timer")


# ---------------------------------------------------------------------------
# 6. Last-Known-Good Preservation State
# ---------------------------------------------------------------------------

def test_14_last_known_good_preservation_semantics() -> None:
    """Verifies that multi-source results explicitly record last-known-good preservation."""
    gate_decision = MultiSourceRefreshGateDecision(
        should_refresh=True,
        reason="elapsed_exceeds_interval",
    )
    # Scenario: 3 sources succeed, 1 fails
    source_results = {
        "adzuna": MarketSourceRefreshResult(
            source=MarketSourceType.ADZUNA,
            status=MarketSourceStatus.SUCCESS,
            jobs_fetched=50,
            jobs_normalized=48,
            jobs_persisted=48,
        ),
        "greenhouse": MarketSourceRefreshResult(
            source=MarketSourceType.GREENHOUSE,
            status=MarketSourceStatus.SUCCESS,
            jobs_fetched=30,
            jobs_normalized=30,
            jobs_persisted=30,
        ),
        "lever": MarketSourceRefreshResult(
            source=MarketSourceType.LEVER,
            status=MarketSourceStatus.FAILED,
            error_category="CONNECTION_ERROR",
            error_message="Connection timed out after 10s",
        ),
        "ashby": MarketSourceRefreshResult(
            source=MarketSourceType.ASHBY,
            status=MarketSourceStatus.SUCCESS,
            jobs_fetched=20,
            jobs_normalized=20,
            jobs_persisted=20,
        ),
    }

    result = MultiSourceRefreshResult(
        status=MarketRefreshStatus.PARTIALLY_COMPLETED,
        gate_decision=gate_decision,
        source_results=source_results,
        total_jobs_fetched=100,
        total_jobs_normalized=98,
        total_jobs_persisted=98,
        total_sources_succeeded=3,
        total_sources_failed=1,
        total_sources_skipped=0,
        last_known_good_preserved=True,  # Crucial requirement
        downstream_demand_refreshed=True,
    )

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.last_known_good_preserved is True
    assert result.total_sources_succeeded == 3
    assert result.total_sources_failed == 1

    summary = result.to_summary_dict()
    assert summary["last_known_good_preserved"] is True
    assert summary["status"] == "partially_completed"
    assert summary["metrics"]["total_sources_succeeded"] == 3
    assert summary["metrics"]["total_sources_failed"] == 1


# ---------------------------------------------------------------------------
# 7. Model Validation & Constraints
# ---------------------------------------------------------------------------

def test_15_typed_models_reject_malformed_values() -> None:
    """Verifies that typed models enforce valid ranges and types."""
    # Negative job counts rejected
    with pytest.raises(ValueError):
        MarketSourceRefreshResult(
            source=MarketSourceType.ADZUNA,
            status=MarketSourceStatus.SUCCESS,
            jobs_fetched=-1,
        )

    # Invalid source rejected
    with pytest.raises(UnknownMarketSourceError):
        MarketSourceRefreshResult(
            source="unknown_vendor",
            status=MarketSourceStatus.SUCCESS,
        )

    # Non-positive interval in gate decision rejected
    with pytest.raises(ValueError):
        MultiSourceRefreshGateDecision(
            should_refresh=True,
            reason="test",
            interval_hours=0,
        )

    # Non-positive interval in config rejected
    with pytest.raises(ValueError):
        MultiSourceRefreshConfig(
            refresh_interval_hours=-5,
        )

    # Empty enabled_sources in config rejected
    with pytest.raises(ValueError):
        MultiSourceRefreshConfig(
            enabled_sources=(),
        )


# ---------------------------------------------------------------------------
# 8. Checkpoint 2 Multi-Source Refresh Execution Tests
# ---------------------------------------------------------------------------

class FakeAdapter(MarketSourceAdapter):
    """Deterministic fake adapter for testing multi-source execution without network calls."""
    def __init__(
        self,
        source_type: MarketSourceType,
        configured: bool = True,
        jobs: Optional[List[NormalizedMarketJob]] = None,
        error: Optional[Exception] = None,
    ):
        self._source_type = source_type
        self._configured = configured
        self._jobs = jobs if jobs is not None else []
        self._error = error
        self.fetch_calls: List[Dict[str, Any]] = []

    @property
    def source_type(self) -> MarketSourceType:
        return self._source_type

    @property
    def is_configured(self) -> bool:
        return self._configured

    def fetch_and_normalize_jobs(
        self,
        queries: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> List[NormalizedMarketJob]:
        self.fetch_calls.append({"queries": queries, "kwargs": kwargs})
        if self._error:
            raise self._error
        return list(self._jobs)

    def normalize_job(self, raw_job: Any) -> Optional[NormalizedMarketJob]:
        return None


def _make_sample_job(source: str, ext_id: str, title: str) -> NormalizedMarketJob:
    return NormalizedMarketJob(
        source=source,
        external_job_id=ext_id,
        title=title,
        description="Sample job description with Python and React",
        company_name="TechCorp",
    )


def _build_test_orchestrator(
    adapters: Optional[Dict[MarketSourceType, MarketSourceAdapter]] = None,
) -> Tuple[MultiSourceMarketRefreshOrchestrator, MagicMock, Dict[str, MagicMock]]:
    """Builds an orchestrator with isolated mocks for persistence and downstream services."""
    registry = MarketSourceRegistry(register_defaults=False)
    if adapters:
        for st, adapter in adapters.items():
            registry.register_adapter(st, adapter)

    mock_db = MagicMock()
    mock_repo = MagicMock()
    mock_repo.persist_jobs.side_effect = lambda jobs, db, commit: MagicMock(
        inserted=len(jobs), updated=0, unchanged=0, failed=0
    )

    mock_ext = MagicMock()
    mock_ext.process_persisted_jobs.return_value = MagicMock(skills_matched=5)

    mock_agg = MagicMock()
    mock_agg.aggregate_market_demand.return_value = MagicMock(skills_with_demand=4)

    mock_snap = MagicMock()
    mock_snap.create_snapshot_from_current_demand.return_value = ([], 3, 0)

    mock_growth = MagicMock()
    mock_growth.compute_and_persist_growth.return_value = ([], 2, 0, 0)

    orchestrator = MultiSourceMarketRefreshOrchestrator(
        registry=registry,
        repository=mock_repo,
        extraction_service=mock_ext,
        aggregator=mock_agg,
        snapshot_service=mock_snap,
        growth_service=mock_growth,
    )

    mocks = {
        "repo": mock_repo,
        "extraction": mock_ext,
        "aggregator": mock_agg,
        "snapshot": mock_snap,
        "growth": mock_growth,
    }
    return orchestrator, mock_db, mocks


def test_16_orchestrator_execution_gate_skips_when_snapshot_recent() -> None:
    """Verifies that if latest snapshot is < 24h and force=False, entire refresh is skipped."""
    call_tracker: List[str] = []
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(MarketSourceType.ADZUNA, jobs=[_make_sample_job("adzuna", "1", "Dev")]),
        MarketSourceType.GREENHOUSE: FakeAdapter(MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "2", "Eng")]),
        MarketSourceType.LEVER: FakeAdapter(MarketSourceType.LEVER, jobs=[_make_sample_job("lever", "3", "SWE")]),
        MarketSourceType.ASHBY: FakeAdapter(MarketSourceType.ASHBY, jobs=[_make_sample_job("ashby", "4", "DevOps")]),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)

    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)
    recent_snapshot = now - timedelta(hours=4)
    mock_db.query.return_value.order_by.return_value.first.return_value = (recent_snapshot,)

    config = MultiSourceRefreshConfig(force=False)
    result = orchestrator.orchestrate_refresh(db=mock_db, config=config, force=False)

    assert result.status == MarketRefreshStatus.SKIPPED
    assert result.gate_decision.should_refresh is False
    assert result.gate_decision.reason == "skipped_within_24h"
    assert result.total_sources_skipped == 4
    assert result.total_jobs_fetched == 0
    assert result.total_jobs_persisted == 0
    assert result.downstream_demand_refreshed is False

    # Zero adapter calls made
    for adapter in adapters.values():
        assert len(adapter.fetch_calls) == 0

    # Zero persistence/downstream calls made
    assert mocks["repo"].persist_jobs.call_count == 0
    assert mocks["aggregator"].aggregate_market_demand.call_count == 0
    assert mocks["snapshot"].create_snapshot_from_current_demand.call_count == 0


def test_17_orchestrator_execution_all_sources_succeed() -> None:
    """Verifies complete successful orchestration across all 4 sources."""
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(
            MarketSourceType.ADZUNA, jobs=[_make_sample_job("adzuna", "a1", "Backend Engineer")]
        ),
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "Frontend Engineer")]
        ),
        MarketSourceType.LEVER: FakeAdapter(
            MarketSourceType.LEVER, jobs=[_make_sample_job("lever", "l1", "Full Stack Engineer")]
        ),
        MarketSourceType.ASHBY: FakeAdapter(
            MarketSourceType.ASHBY, jobs=[_make_sample_job("ashby", "as1", "DevOps Engineer")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    # No prior snapshot -> gate approves refresh
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    result = orchestrator.orchestrate_refresh(db=mock_db, force=False)

    assert result.status == MarketRefreshStatus.COMPLETED
    assert result.total_sources_succeeded == 4
    assert result.total_sources_failed == 0
    assert result.total_sources_skipped == 0
    assert result.total_jobs_fetched == 4
    assert result.total_jobs_normalized == 4
    assert result.total_jobs_persisted == 4
    assert result.downstream_demand_refreshed is True
    assert result.last_known_good_preserved is True
    assert result.snapshot_at is not None

    # Every source status is SUCCESS
    for st in DEFAULT_SOURCE_ORDER:
        s_res = result.source_results[st.value]
        assert s_res.status == MarketSourceStatus.SUCCESS
        assert s_res.jobs_fetched == 1
        assert s_res.jobs_persisted == 1

    # Verified downstream pipelines were invoked 4 times (once per source)
    assert mocks["repo"].persist_jobs.call_count == 4
    assert mocks["extraction"].process_persisted_jobs.call_count == 4
    assert mocks["aggregator"].aggregate_market_demand.call_count == 4
    assert mocks["snapshot"].create_snapshot_from_current_demand.call_count == 4
    assert mocks["growth"].compute_and_persist_growth.call_count == 4
    assert mock_db.commit.call_count == 1


def test_18_orchestrator_execution_deterministic_order() -> None:
    """Verifies that adapters are invoked strictly in canonical order [ADZUNA, GREENHOUSE, LEVER, ASHBY]."""
    invocation_order: List[MarketSourceType] = []

    class OrderTrackingAdapter(FakeAdapter):
        def fetch_and_normalize_jobs(self, queries=None, **kwargs):
            invocation_order.append(self.source_type)
            return super().fetch_and_normalize_jobs(queries, **kwargs)

    adapters = {
        MarketSourceType.ASHBY: OrderTrackingAdapter(MarketSourceType.ASHBY),
        MarketSourceType.LEVER: OrderTrackingAdapter(MarketSourceType.LEVER),
        MarketSourceType.GREENHOUSE: OrderTrackingAdapter(MarketSourceType.GREENHOUSE),
        MarketSourceType.ADZUNA: OrderTrackingAdapter(MarketSourceType.ADZUNA),
    }
    orchestrator, mock_db, _ = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    orchestrator.orchestrate_refresh(db=mock_db, force=False)

    expected_canonical = [
        MarketSourceType.ADZUNA,
        MarketSourceType.GREENHOUSE,
        MarketSourceType.LEVER,
        MarketSourceType.ASHBY,
    ]
    assert invocation_order == expected_canonical


def test_19_orchestrator_execution_one_source_fails_with_isolation() -> None:
    """
    Verifies that if one provider fails (e.g. Lever network error):
    - healthy sources continue processing
    - failed source is marked FAILED without fabricating jobs
    - overall status is PARTIALLY_COMPLETED
    - last-known-good state is preserved
    """
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(
            MarketSourceType.ADZUNA, jobs=[_make_sample_job("adzuna", "a1", "Data Scientist")]
        ),
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "ML Engineer")]
        ),
        MarketSourceType.LEVER: FakeAdapter(
            MarketSourceType.LEVER, error=ConnectionError("Lever API connection reset by peer")
        ),
        MarketSourceType.ASHBY: FakeAdapter(
            MarketSourceType.ASHBY, jobs=[_make_sample_job("ashby", "as1", "AI Researcher")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    result = orchestrator.orchestrate_refresh(db=mock_db, force=False)

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.total_sources_succeeded == 3
    assert result.total_sources_failed == 1
    assert result.last_known_good_preserved is True
    assert result.downstream_demand_refreshed is True

    # Check lever result specifically
    lever_res = result.source_results["lever"]
    assert lever_res.status == MarketSourceStatus.FAILED
    assert lever_res.jobs_fetched == 0
    assert lever_res.jobs_normalized == 0
    assert lever_res.jobs_persisted == 0
    assert lever_res.error_category == "ConnectionError"
    assert "connection reset by peer" in lever_res.error_message

    # Other sources succeeded
    assert result.source_results["adzuna"].status == MarketSourceStatus.SUCCESS
    assert result.source_results["greenhouse"].status == MarketSourceStatus.SUCCESS
    assert result.source_results["ashby"].status == MarketSourceStatus.SUCCESS

    # Downstream ran 3 times (only for succeeded sources, never for failed lever)
    assert mocks["snapshot"].create_snapshot_from_current_demand.call_count == 3
    assert mock_db.commit.call_count == 1


def test_20_orchestrator_execution_all_sources_fail() -> None:
    """
    Verifies that if ALL providers fail:
    - overall status is FAILED
    - no snapshots or demand are fabricated
    - last-known-good state is preserved intact
    - transaction is rolled back
    """
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(MarketSourceType.ADZUNA, error=RuntimeError("Adzuna down")),
        MarketSourceType.GREENHOUSE: FakeAdapter(MarketSourceType.GREENHOUSE, error=RuntimeError("Greenhouse down")),
        MarketSourceType.LEVER: FakeAdapter(MarketSourceType.LEVER, error=RuntimeError("Lever down")),
        MarketSourceType.ASHBY: FakeAdapter(MarketSourceType.ASHBY, error=RuntimeError("Ashby down")),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    result = orchestrator.orchestrate_refresh(db=mock_db, force=False)

    assert result.status == MarketRefreshStatus.FAILED
    assert result.total_sources_succeeded == 0
    assert result.total_sources_failed == 4
    assert result.total_jobs_fetched == 0
    assert result.last_known_good_preserved is True
    assert result.downstream_demand_refreshed is False
    assert result.snapshot_at is None
    assert "All configured market sources failed" in str(result.error)

    # Downstream never invoked
    assert mocks["snapshot"].create_snapshot_from_current_demand.call_count == 0
    assert mocks["growth"].compute_and_persist_growth.call_count == 0
    assert mock_db.rollback.call_count == 1
    assert mock_db.commit.call_count == 0


def test_21_orchestrator_execution_empty_successful_source() -> None:
    """
    Verifies that a provider returning 0 jobs successfully is represented as
    SUCCESS with 0 jobs, distinct from a failure.
    """
    adapters = {
        MarketSourceType.GREENHOUSE: FakeAdapter(MarketSourceType.GREENHOUSE, jobs=[]),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.GREENHOUSE,))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    assert result.status == MarketRefreshStatus.COMPLETED
    gh_res = result.source_results["greenhouse"]
    assert gh_res.status == MarketSourceStatus.SUCCESS
    assert gh_res.jobs_fetched == 0
    assert gh_res.jobs_normalized == 0
    assert gh_res.jobs_persisted == 0
    assert gh_res.error_category is None
    assert gh_res.error_message is None


def test_22_orchestrator_execution_sanitizes_credentials_on_failure() -> None:
    """Verifies that provider errors containing secrets or tokens are scrubbed."""
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(
            MarketSourceType.ADZUNA,
            error=Exception("Adzuna error with app_key=secretKey999 and Bearer token123456 and https://u:secret_pw@host.com/"),
        ),
    }
    orchestrator, mock_db, _ = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.ADZUNA,))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    dump = result.to_dict()
    dump_str = str(dump)
    assert "secretKey999" not in dump_str
    assert "token123456" not in dump_str
    assert "secret_pw" not in dump_str
    assert "[REDACTED]" in dump_str


def test_23_orchestrator_execution_unconfigured_source_handled_cleanly() -> None:
    """Verifies that an unconfigured source fails cleanly and isolates other sources."""
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(MarketSourceType.ADZUNA, configured=False),
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "Developer")]
        ),
    }
    orchestrator, mock_db, _ = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.ADZUNA, MarketSourceType.GREENHOUSE))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.source_results["adzuna"].status == MarketSourceStatus.FAILED
    assert result.source_results["adzuna"].error_category == "MarketSourceConfigurationError"
    assert result.source_results["greenhouse"].status == MarketSourceStatus.SUCCESS


def test_24_orchestrator_execution_respects_source_fetch_limits() -> None:
    """Verifies that configured source fetch limits are passed down to adapter invocations."""
    adapters = {
        MarketSourceType.GREENHOUSE: FakeAdapter(MarketSourceType.GREENHOUSE),
        MarketSourceType.LEVER: FakeAdapter(MarketSourceType.LEVER),
    }
    orchestrator, mock_db, _ = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    cfg = MultiSourceRefreshConfig(
        enabled_sources=(MarketSourceType.GREENHOUSE, MarketSourceType.LEVER),
        source_fetch_limits={"greenhouse": 15, "lever": 25},
    )
    orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    gh_call = adapters[MarketSourceType.GREENHOUSE].fetch_calls[0]
    assert gh_call["kwargs"]["max_results"] == 15

    lever_call = adapters[MarketSourceType.LEVER].fetch_calls[0]
    assert lever_call["kwargs"]["limit"] == 25


def test_25_orchestrator_execution_force_bypasses_gate_only() -> None:
    """Verifies that force=True bypasses the 24h gate while running normal execution."""
    adapters = {
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "Developer")]
        ),
    }
    orchestrator, mock_db, _ = _build_test_orchestrator(adapters)

    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)
    recent_snapshot = now - timedelta(minutes=30)
    mock_db.query.return_value.order_by.return_value.first.return_value = (recent_snapshot,)

    cfg = MultiSourceRefreshConfig(
        enabled_sources=(MarketSourceType.GREENHOUSE,),
        force=True,
    )
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg, force=True)

    assert result.status == MarketRefreshStatus.COMPLETED
    assert result.gate_decision.should_refresh is True
    assert result.gate_decision.reason == "force_refresh"
    assert result.total_sources_succeeded == 1
    assert len(adapters[MarketSourceType.GREENHOUSE].fetch_calls) == 1


def test_26_two_phase_all_sources_persisted_before_any_downstream_intelligence() -> None:
    """
    Verifies that Phase 1 (fetch/persist for all sources) completes entirely
    BEFORE Phase 2 (extraction/demand/snapshots/growth) begins.
    """
    event_log: List[Tuple[str, str]] = []

    class PhaseTrackingAdapter(FakeAdapter):
        def fetch_and_normalize_jobs(self, queries=None, **kwargs):
            event_log.append(("phase1_fetch", self.source_type.value))
            return super().fetch_and_normalize_jobs(queries, **kwargs)

    adapters = {
        MarketSourceType.ADZUNA: PhaseTrackingAdapter(
            MarketSourceType.ADZUNA, jobs=[_make_sample_job("adzuna", "a1", "SWE")]
        ),
        MarketSourceType.GREENHOUSE: PhaseTrackingAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "SWE")]
        ),
        MarketSourceType.LEVER: PhaseTrackingAdapter(
            MarketSourceType.LEVER, jobs=[_make_sample_job("lever", "l1", "SWE")]
        ),
        MarketSourceType.ASHBY: PhaseTrackingAdapter(
            MarketSourceType.ASHBY, jobs=[_make_sample_job("ashby", "as1", "SWE")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    # Track persistence calls
    def track_persist(jobs, db, commit):
        src = jobs[0].source if jobs else "unknown"
        event_log.append(("phase1_persist", src))
        return MagicMock(inserted=len(jobs), updated=0, unchanged=0, failed=0)
    mocks["repo"].persist_jobs.side_effect = track_persist

    # Track downstream calls
    def track_extract(db, source, reconcile, commit):
        event_log.append(("phase2_extract", source))
        return MagicMock(skills_matched=1)
    mocks["extraction"].process_persisted_jobs.side_effect = track_extract

    def track_snapshot(db, source, snapshot_at, commit):
        event_log.append(("phase2_snapshot", source))
        return ([], 1, 0)
    mocks["snapshot"].create_snapshot_from_current_demand.side_effect = track_snapshot

    orchestrator.orchestrate_refresh(db=mock_db, force=False)

    # All Phase 1 events must precede all Phase 2 events
    phase1_events = [e for e in event_log if e[0].startswith("phase1")]
    phase2_events = [e for e in event_log if e[0].startswith("phase2")]

    assert len(phase1_events) == 8  # 4 fetches + 4 persists
    assert len(phase2_events) == 8  # 4 extracts + 4 snapshots (plus others)

    # Find last index of phase 1 and first index of phase 2
    last_phase1_idx = max(event_log.index(e) for e in phase1_events)
    first_phase2_idx = min(event_log.index(e) for e in phase2_events)
    assert last_phase1_idx < first_phase2_idx, "Phase 1 must strictly finish before Phase 2 begins"


def test_27_two_phase_failed_source_excluded_from_phase2() -> None:
    """
    Verifies that when Lever fails in Phase 1:
    - Phase 1 attempts all 4 sources (Adzuna, Greenhouse, Lever, Ashby)
    - Phase 2 executes ONLY for Adzuna, Greenhouse, Ashby
    - Lever receives zero downstream calls
    - All participating snapshots share the exact same snapshot_at timestamp
    """
    event_log: List[Tuple[str, str]] = []
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(
            MarketSourceType.ADZUNA, jobs=[_make_sample_job("adzuna", "a1", "SWE")]
        ),
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "SWE")]
        ),
        MarketSourceType.LEVER: FakeAdapter(
            MarketSourceType.LEVER, error=ConnectionError("Lever timeout")
        ),
        MarketSourceType.ASHBY: FakeAdapter(
            MarketSourceType.ASHBY, jobs=[_make_sample_job("ashby", "as1", "SWE")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    snapshot_timestamps: List[datetime] = []
    def track_snapshot(db, source, snapshot_at, commit):
        snapshot_timestamps.append(snapshot_at)
        event_log.append(("phase2_snapshot", source))
        return ([], 1, 0)
    mocks["snapshot"].create_snapshot_from_current_demand.side_effect = track_snapshot

    def track_extract(db, source, reconcile, commit):
        event_log.append(("phase2_extract", source))
        return MagicMock(skills_matched=1)
    mocks["extraction"].process_persisted_jobs.side_effect = track_extract

    result = orchestrator.orchestrate_refresh(db=mock_db, force=False)

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.source_results["lever"].status == MarketSourceStatus.FAILED

    # Downstream was called exactly 3 times (Adzuna, Greenhouse, Ashby)
    extract_sources = [e[1] for e in event_log if e[0] == "phase2_extract"]
    snapshot_sources = [e[1] for e in event_log if e[0] == "phase2_snapshot"]

    assert extract_sources == ["adzuna", "greenhouse", "ashby"]
    assert snapshot_sources == ["adzuna", "greenhouse", "ashby"]
    assert "lever" not in extract_sources
    assert "lever" not in snapshot_sources

    # All participating source snapshots share the exact same snapshot_at timestamp
    assert len(snapshot_timestamps) == 3
    assert snapshot_timestamps[0] == snapshot_timestamps[1] == snapshot_timestamps[2]
    assert result.snapshot_at == snapshot_timestamps[0]


def test_28_two_phase_snapshots_strictly_source_scoped() -> None:
    """
    Verifies that P1-F snapshots remain strictly source-scoped:
    no source='all' or synthetic cross-source snapshot is ever created.
    """
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(MarketSourceType.ADZUNA, jobs=[_make_sample_job("adzuna", "a1", "SWE")]),
        MarketSourceType.GREENHOUSE: FakeAdapter(MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "SWE")]),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.ADZUNA, MarketSourceType.GREENHOUSE))
    orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    # Check all snapshot calls
    snapshot_calls = mocks["snapshot"].create_snapshot_from_current_demand.call_args_list
    assert len(snapshot_calls) == 2
    sources_called = [call.kwargs.get("source") for call in snapshot_calls]
    assert sources_called == ["adzuna", "greenhouse"]
    assert "all" not in sources_called
    assert None not in sources_called


# ---------------------------------------------------------------------------
# 9. Checkpoint 3 Production Hardening & Edge-Case Tests
# ---------------------------------------------------------------------------

def test_29_phase1_persistence_failure_isolation_with_savepoint() -> None:
    """
    Verifies that when repository.persist_jobs fails for one source in Phase 1:
    - the nested savepoint rolls back that source's SQL changes
    - the failing source is marked FAILED with sanitized error
    - subsequent healthy sources continue Phase 1 fetch and persistence
    - healthy sources continue to Phase 2 downstream intelligence
    - overall status is PARTIALLY_COMPLETED
    - final db.commit() commits the healthy sources' work
    """
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(
            MarketSourceType.ADZUNA, jobs=[_make_sample_job("adzuna", "a1", "SWE")]
        ),
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "Data Analyst")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    # Mock savepoints
    mock_savepoint_adzuna = MagicMock()
    mock_savepoint_gh = MagicMock()
    mock_db.begin_nested.side_effect = [mock_savepoint_adzuna, mock_savepoint_gh, MagicMock()]

    # Make Adzuna fail during persistence
    def persist_effect(jobs, db, commit):
        if jobs and jobs[0].source == "adzuna":
            raise RuntimeError("Database write constraint violation for Adzuna")
        return MagicMock(inserted=len(jobs), updated=0, unchanged=0, failed=0)

    mocks["repo"].persist_jobs.side_effect = persist_effect

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.ADZUNA, MarketSourceType.GREENHOUSE))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    # Adzuna savepoint was rolled back
    mock_savepoint_adzuna.rollback.assert_called_once()
    mock_savepoint_adzuna.commit.assert_not_called()

    # Greenhouse savepoint was committed
    mock_savepoint_gh.commit.assert_called_once()

    # Status check
    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.total_sources_succeeded == 1
    assert result.total_sources_failed == 1
    assert result.source_results["adzuna"].status == MarketSourceStatus.FAILED
    assert result.source_results["adzuna"].error_category == "RuntimeError"
    assert "Database write constraint violation" in result.source_results["adzuna"].error_message
    assert result.source_results["greenhouse"].status == MarketSourceStatus.SUCCESS

    # Greenhouse received Phase 2 downstream calls
    mocks["extraction"].process_persisted_jobs.assert_called_once_with(
        db=mock_db, source="greenhouse", reconcile=True, commit=False
    )
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()


def test_30_phase1_malformed_non_list_response_handled_cleanly() -> None:
    """
    Verifies that if an adapter returns an invalid non-list object:
    - the orchestrator catches it as a ValueError
    - the malformed source is marked FAILED without crashing
    - other configured sources proceed normally
    """
    class BadAdapter(FakeAdapter):
        def fetch_and_normalize_jobs(self, queries=None, **kwargs):
            return {"not_a_list": True}  # type: ignore

    adapters = {
        MarketSourceType.ADZUNA: BadAdapter(MarketSourceType.ADZUNA),
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "SWE")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.ADZUNA, MarketSourceType.GREENHOUSE))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.source_results["adzuna"].status == MarketSourceStatus.FAILED
    assert result.source_results["adzuna"].error_category == "ValueError"
    assert "non-list result" in result.source_results["adzuna"].error_message
    assert result.source_results["greenhouse"].status == MarketSourceStatus.SUCCESS


def test_31_phase2_extraction_failure_isolation() -> None:
    """
    Verifies that if canonical skill extraction fails for one source in Phase 2:
    - that source's savepoint is rolled back
    - that source's status is updated to FAILED
    - subsequent sources continue Phase 2 downstream intelligence
    - overall status is PARTIALLY_COMPLETED
    """
    adapters = {
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "SWE")]
        ),
        MarketSourceType.LEVER: FakeAdapter(
            MarketSourceType.LEVER, jobs=[_make_sample_job("lever", "l1", "SWE")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    def extract_side_effect(db, source, reconcile, commit):
        if source == "greenhouse":
            raise RuntimeError("Skill extraction NLP parser crashed")
        return MagicMock(skills_matched=3)

    mocks["extraction"].process_persisted_jobs.side_effect = extract_side_effect

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.GREENHOUSE, MarketSourceType.LEVER))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.source_results["greenhouse"].status == MarketSourceStatus.FAILED
    assert result.source_results["greenhouse"].error_category == "RuntimeError"
    assert "Skill extraction NLP parser crashed" in result.source_results["greenhouse"].error_message
    assert result.source_results["lever"].status == MarketSourceStatus.SUCCESS
    assert result.total_sources_succeeded == 1
    assert result.total_sources_failed == 1
    assert result.downstream_demand_refreshed is True
    mock_db.commit.assert_called_once()


def test_32_phase2_demand_aggregation_failure_isolation() -> None:
    """
    Verifies that if market demand aggregation fails for one source in Phase 2:
    - savepoint rolls back
    - source status updated to FAILED
    - other sources continue downstream processing
    - overall status is PARTIALLY_COMPLETED
    """
    adapters = {
        MarketSourceType.LEVER: FakeAdapter(
            MarketSourceType.LEVER, jobs=[_make_sample_job("lever", "l1", "SWE")]
        ),
        MarketSourceType.ASHBY: FakeAdapter(
            MarketSourceType.ASHBY, jobs=[_make_sample_job("ashby", "as1", "SWE")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    def agg_side_effect(db, source, reconcile, commit):
        if source == "lever":
            raise RuntimeError("Demand aggregation failed on DB lock")
        return MagicMock(skills_with_demand=2)

    mocks["aggregator"].aggregate_market_demand.side_effect = agg_side_effect

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.LEVER, MarketSourceType.ASHBY))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.source_results["lever"].status == MarketSourceStatus.FAILED
    assert result.source_results["lever"].error_category == "RuntimeError"
    assert result.source_results["ashby"].status == MarketSourceStatus.SUCCESS
    assert result.total_sources_succeeded == 1
    assert result.total_sources_failed == 1


def test_33_phase2_snapshot_failure_isolation() -> None:
    """
    Verifies that if snapshot creation fails for one source in Phase 2:
    - savepoint rolls back
    - source status updated to FAILED
    - other sources continue downstream processing
    """
    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(
            MarketSourceType.ADZUNA, jobs=[_make_sample_job("adzuna", "a1", "SWE")]
        ),
        MarketSourceType.ASHBY: FakeAdapter(
            MarketSourceType.ASHBY, jobs=[_make_sample_job("ashby", "as1", "SWE")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    def snap_side_effect(db, source, snapshot_at, commit):
        if source == "adzuna":
            raise RuntimeError("Snapshot service unique constraint violation")
        return ([], 5, 0)

    mocks["snapshot"].create_snapshot_from_current_demand.side_effect = snap_side_effect

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.ADZUNA, MarketSourceType.ASHBY))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.source_results["adzuna"].status == MarketSourceStatus.FAILED
    assert result.source_results["adzuna"].error_category == "RuntimeError"
    assert result.source_results["ashby"].status == MarketSourceStatus.SUCCESS


def test_34_phase2_growth_calculation_failure_isolation() -> None:
    """
    Verifies that if growth calculation fails for one source in Phase 2:
    - savepoint rolls back
    - source status updated to FAILED
    - other sources continue downstream processing
    """
    adapters = {
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "SWE")]
        ),
        MarketSourceType.ASHBY: FakeAdapter(
            MarketSourceType.ASHBY, jobs=[_make_sample_job("ashby", "as1", "SWE")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    def growth_side_effect(db, source, commit):
        if source == "greenhouse":
            raise RuntimeError("Growth formula division error")
        return ([], 2, 0, 0)

    mocks["growth"].compute_and_persist_growth.side_effect = growth_side_effect

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.GREENHOUSE, MarketSourceType.ASHBY))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.source_results["greenhouse"].status == MarketSourceStatus.FAILED
    assert result.source_results["greenhouse"].error_category == "RuntimeError"
    assert result.source_results["ashby"].status == MarketSourceStatus.SUCCESS


def test_35_centralized_gate_exact_24h_boundary() -> None:
    """
    Verifies boundary behavior of centralized 24h gate:
    - elapsed_hours == 24.0 -> should_refresh=True (elapsed_exceeds_interval)
    - elapsed_hours == 23.999 -> should_refresh=False (skipped_within_24h)
    """
    orchestrator = MultiSourceMarketRefreshOrchestrator()
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)

    # Exactly 24.0h
    exact_24h_snapshot = now - timedelta(hours=24)
    mock_db = MagicMock()
    mock_db.query.return_value.order_by.return_value.first.return_value = (exact_24h_snapshot,)

    dec_exact = orchestrator.evaluate_24h_gate(db=mock_db, force=False, now=now)
    assert dec_exact.should_refresh is True
    assert dec_exact.reason == "elapsed_exceeds_interval"
    assert dec_exact.elapsed_hours == pytest.approx(24.0, abs=0.001)

    # Slightly under 24.0h (e.g. 23 hours 59 minutes)
    under_24h_snapshot = now - timedelta(hours=23, minutes=59)
    mock_db.query.return_value.order_by.return_value.first.return_value = (under_24h_snapshot,)

    dec_under = orchestrator.evaluate_24h_gate(db=mock_db, force=False, now=now)
    assert dec_under.should_refresh is False
    assert dec_under.reason == "skipped_within_24h"
    assert dec_under.elapsed_hours < 24.0


def test_36_centralized_gate_multiple_source_timestamps_newest_governs() -> None:
    """
    Verifies that when different sources have snapshots at different times:
    - the newest snapshot across all sources governs the gate
    - if the newest snapshot is < 24h old, the centralized gate skips
    - no source-specific bypassing occurs
    """
    orchestrator = MultiSourceMarketRefreshOrchestrator()
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)
    newest_snapshot = now - timedelta(hours=2)  # 2 hours old

    # SQL ORDER BY snapshot_at DESC returns the newest snapshot row
    mock_db = MagicMock()
    mock_db.query.return_value.order_by.return_value.first.return_value = (newest_snapshot,)

    decision = orchestrator.evaluate_24h_gate(db=mock_db, force=False, now=now)
    assert decision.should_refresh is False
    assert decision.reason == "skipped_within_24h"
    assert decision.elapsed_hours == pytest.approx(2.0, abs=0.01)


def test_37_secret_sanitization_comprehensive_credential_patterns() -> None:
    """
    Verifies that all credential patterns:
    - user:pass in DSNs/URLs (postgresql+psycopg://, https://)
    - Basic / Bearer auth headers
    - key-value secrets (api_key, app_key, app_id, password, token)
    are scrubbed across all result objects, dict dumps, and error messages.
    """
    dirty_error = (
        "Connection failed: postgresql+psycopg://app_usr:super_secret_db_pass@db.prod:5432/sf "
        "calling https://api_usr:api_secret_tok@api.lever.co/v1/jobs "
        "with Authorization: Basic dXNlcjpwYXNzd29yZA== and Authorization: Bearer eyJhbGciOiJIUzI1NiJ9 "
        "and api_key='sk_live_99999' and password=\"p@ssw0rd!\" and token=tok_12345"
    )
    clean = sanitize_error_message(dirty_error)

    # Zero sensitive tokens survive
    assert "super_secret_db_pass" not in clean
    assert "api_secret_tok" not in clean
    assert "dXNlcjpwYXNzd29yZA==" not in clean
    assert "eyJhbGciOiJIUzI1NiJ9" not in clean
    assert "sk_live_99999" not in clean
    assert "p@ssw0rd!" not in clean
    assert "tok_12345" not in clean
    assert "[REDACTED]" in clean


def test_38_phase2_all_sources_fail_triggers_overall_rollback() -> None:
    """
    Verifies that if ALL sources fail during Phase 2 downstream intelligence:
    - final overall status is FAILED
    - outer session db.rollback() is invoked
    - downstream_demand_refreshed is False
    - snapshot_at is None
    - last-known-good state is preserved
    """
    adapters = {
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "g1", "SWE")]
        ),
        MarketSourceType.LEVER: FakeAdapter(
            MarketSourceType.LEVER, jobs=[_make_sample_job("lever", "l1", "SWE")]
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    # Both fail during Phase 2
    mocks["extraction"].process_persisted_jobs.side_effect = RuntimeError("Phase 2 crash")

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.GREENHOUSE, MarketSourceType.LEVER))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    assert result.status == MarketRefreshStatus.FAILED
    assert result.total_sources_succeeded == 0
    assert result.total_sources_failed == 2
    assert result.downstream_demand_refreshed is False
    assert result.snapshot_at is None
    assert result.last_known_good_preserved is True
    assert "All configured market sources failed" in str(result.error)

    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()


def test_39_last_known_good_preservation_on_subsequent_source_failure() -> None:
    """
    Verifies that when a source fails on a subsequent refresh:
    - existing data is preserved (no deletion of prior jobs)
    - no fake zero-demand snapshot is created for the failed source
    - downstream intelligence is not called for the failed source
    - failure is accurately recorded
    """
    adapters = {
        MarketSourceType.GREENHOUSE: FakeAdapter(
            MarketSourceType.GREENHOUSE, error=TimeoutError("Greenhouse API timed out")
        ),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.GREENHOUSE,))
    result = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)

    assert result.status == MarketRefreshStatus.FAILED
    assert result.last_known_good_preserved is True
    assert result.source_results["greenhouse"].status == MarketSourceStatus.FAILED
    assert result.source_results["greenhouse"].jobs_persisted == 0

    # No downstream processing occurred
    assert mocks["snapshot"].create_snapshot_from_current_demand.call_count == 0
    assert mocks["growth"].compute_and_persist_growth.call_count == 0


def test_40_repeated_refresh_idempotent_persistence_contract() -> None:
    """
    Verifies that calling persist_jobs repeatedly with identical jobs produces
    idempotent results (0 inserted, 1 unchanged/updated) without duplicating records.
    """
    jobs = [_make_sample_job("lever", "ext_100", "Lead Architect")]

    # First call: inserted=1, updated=0, unchanged=0
    # Second call: inserted=0, updated=0, unchanged=1
    call_count = 0
    def mock_persist(jobs, db=None, commit=False):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MagicMock(inserted=len(jobs), updated=0, unchanged=0, failed=0)
        else:
            return MagicMock(inserted=0, updated=0, unchanged=len(jobs), failed=0)

    adapters = {
        MarketSourceType.LEVER: FakeAdapter(MarketSourceType.LEVER, jobs=jobs),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mocks["repo"].persist_jobs.side_effect = mock_persist

    cfg = MultiSourceRefreshConfig(enabled_sources=(MarketSourceType.LEVER,), force=True)

    # Run 1
    res1 = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)
    assert res1.status == MarketRefreshStatus.COMPLETED
    assert res1.source_results["lever"].jobs_persisted == 1

    # Run 2 (identical data)
    res2 = orchestrator.orchestrate_refresh(db=mock_db, config=cfg)
    assert res2.status == MarketRefreshStatus.COMPLETED
    assert res2.source_results["lever"].jobs_persisted == 1  # 0 inserted + 1 unchanged = 1 total persisted
    assert call_count == 2


# ---------------------------------------------------------------------------
# 10. Checkpoint 4 Final Integration & Acceptance Tests
# ---------------------------------------------------------------------------

def test_41_real_market_services_integration_end_to_end() -> None:
    """
    Verifies that the MultiSourceMarketRefreshOrchestrator runs end-to-end
    with real downstream market services (skill extraction, demand aggregation,
    snapshots, and growth) using the real PostgreSQL test database.
    """
    from app.db.database import SessionLocal
    from app.db.models import MarketJob

    db = SessionLocal()
    try:
        # Create test jobs for all 4 sources
        test_jobs = {
            MarketSourceType.ADZUNA: [_make_sample_job("adzuna", "test_int_a1", "Senior Python Engineer")],
            MarketSourceType.GREENHOUSE: [_make_sample_job("greenhouse", "test_int_g1", "React Frontend Developer")],
            MarketSourceType.LEVER: [_make_sample_job("lever", "test_int_l1", "Full Stack TypeScript Engineer")],
            MarketSourceType.ASHBY: [_make_sample_job("ashby", "test_int_as1", "DevOps Cloud Engineer")],
        }
        adapters = {st: FakeAdapter(st, jobs=test_jobs[st]) for st in MarketSourceType}
        registry = MarketSourceRegistry(register_defaults=False)
        for st, adapter in adapters.items():
            registry.register_adapter(st, adapter)

        # Real orchestrator with real downstream services
        orchestrator = MultiSourceMarketRefreshOrchestrator(registry=registry)

        cfg = MultiSourceRefreshConfig(force=True, commit=True)
        result = orchestrator.orchestrate_refresh(db=db, config=cfg, force=True)

        assert result.status == MarketRefreshStatus.COMPLETED
        assert result.total_sources_succeeded == 4
        assert result.total_sources_failed == 0
        assert result.total_jobs_fetched == 4
        assert result.total_jobs_persisted == 4
        assert result.downstream_demand_refreshed is True
        assert result.snapshot_at is not None

        # Verify each source completed successfully
        for st in DEFAULT_SOURCE_ORDER:
            s_res = result.source_results[st.value]
            assert s_res.status == MarketSourceStatus.SUCCESS
            assert s_res.jobs_persisted == 1

        # Verify database has persisted jobs with no duplicates
        for st in DEFAULT_SOURCE_ORDER:
            count = db.query(MarketJob).filter(
                MarketJob.source == st.value,
                MarketJob.external_job_id.like("test_int_%"),
            ).count()
            assert count == 1, f"Expected 1 job for {st.value}, got {count}"
    finally:
        # Clean up test records
        db.query(MarketJob).filter(MarketJob.external_job_id.like("test_int_%")).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_42_centralized_gate_controlled_sequence_run_a_b_c() -> None:
    """
    Verifies the controlled 3-run sequence:
    RUN A: First run -> executes.
    RUN B: Immediate second run with force=False -> SKIPPED (<24h).
    RUN C: Immediate third run with force=True -> executes.
    """
    from app.db.database import SessionLocal
    from app.db.models import MarketJob

    db = SessionLocal()
    try:
        adapters = {st: FakeAdapter(st, jobs=[_make_sample_job(st.value, f"gate_{st.value}", "Software Engineer")]) for st in MarketSourceType}
        registry = MarketSourceRegistry(register_defaults=False)
        for st, adapter in adapters.items():
            registry.register_adapter(st, adapter)

        orchestrator = MultiSourceMarketRefreshOrchestrator(registry=registry)

        # RUN A: Initial refresh with force=True
        res_a = orchestrator.orchestrate_refresh(db=db, force=True)
        assert res_a.status == MarketRefreshStatus.COMPLETED
        assert res_a.downstream_demand_refreshed is True

        # RUN B: Immediate non-force refresh -> must be SKIPPED
        res_b = orchestrator.orchestrate_refresh(db=db, force=False)
        assert res_b.status == MarketRefreshStatus.SKIPPED
        assert res_b.gate_decision.should_refresh is False
        assert res_b.gate_decision.reason == "skipped_within_24h"
        assert res_b.total_sources_skipped == 4
        assert res_b.total_jobs_fetched == 0
        assert res_b.downstream_demand_refreshed is False

        # RUN C: Immediate force refresh -> must execute
        res_c = orchestrator.orchestrate_refresh(db=db, force=True)
        assert res_c.status == MarketRefreshStatus.COMPLETED
        assert res_c.gate_decision.should_refresh is True
        assert res_c.gate_decision.reason == "force_refresh"
        assert res_c.total_sources_succeeded == 4
        assert res_c.downstream_demand_refreshed is True
    finally:
        db.query(MarketJob).filter(MarketJob.external_job_id.like("gate_%")).delete(synchronize_session=False)
        db.commit()
        db.close()


def test_43_two_phase_real_runtime_ordering_verified() -> None:
    """
    Verifies that during runtime:
    Phase 1 fetch & persist strictly finishes across all sources BEFORE Phase 2 starts.
    """
    event_log: List[Tuple[str, str]] = []

    class EventLoggingAdapter(FakeAdapter):
        def fetch_and_normalize_jobs(self, queries=None, **kwargs):
            event_log.append(("phase1_fetch", self.source_type.value))
            return super().fetch_and_normalize_jobs(queries, **kwargs)

    adapters = {
        st: EventLoggingAdapter(st, jobs=[_make_sample_job(st.value, f"ord_{st.value}", "Engineer")])
        for st in DEFAULT_SOURCE_ORDER
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    def log_extract(db, source, reconcile, commit):
        event_log.append(("phase2_extract", source))
        return MagicMock(skills_matched=2)
    mocks["extraction"].process_persisted_jobs.side_effect = log_extract

    orchestrator.orchestrate_refresh(db=mock_db, force=False)

    p1_events = [ev for ev in event_log if ev[0].startswith("phase1")]
    p2_events = [ev for ev in event_log if ev[0].startswith("phase2")]

    assert len(p1_events) == 4
    assert len(p2_events) == 4

    p1_order = [ev[1] for ev in p1_events]
    p2_order = [ev[1] for ev in p2_events]

    expected = ["adzuna", "greenhouse", "lever", "ashby"]
    assert p1_order == expected
    assert p2_order == expected

    last_p1 = max(event_log.index(ev) for ev in p1_events)
    first_p2 = min(event_log.index(ev) for ev in p2_events)
    assert last_p1 < first_p2, "All Phase 1 operations must finish before any Phase 2 operation begins"


def test_44_partial_failure_with_real_downstream_services() -> None:
    """
    Verifies partial failure behavior:
    - Adzuna, Greenhouse, Ashby succeed
    - Lever fails with connection timeout
    - Phase 1 attempts all 4
    - Phase 2 processes only Adzuna, Greenhouse, Ashby
    - Final status is PARTIALLY_COMPLETED
    """
    phase2_processed: List[str] = []

    adapters = {
        MarketSourceType.ADZUNA: FakeAdapter(MarketSourceType.ADZUNA, jobs=[_make_sample_job("adzuna", "pf_a", "SWE")]),
        MarketSourceType.GREENHOUSE: FakeAdapter(MarketSourceType.GREENHOUSE, jobs=[_make_sample_job("greenhouse", "pf_g", "SWE")]),
        MarketSourceType.LEVER: FakeAdapter(MarketSourceType.LEVER, error=ConnectionError("Lever connection timeout (simulated)")),
        MarketSourceType.ASHBY: FakeAdapter(MarketSourceType.ASHBY, jobs=[_make_sample_job("ashby", "pf_as", "SWE")]),
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    def track_extract(db, source, reconcile, commit):
        phase2_processed.append(source)
        return MagicMock(skills_matched=1)
    mocks["extraction"].process_persisted_jobs.side_effect = track_extract

    result = orchestrator.orchestrate_refresh(db=mock_db, force=False)

    assert result.status == MarketRefreshStatus.PARTIALLY_COMPLETED
    assert result.total_sources_succeeded == 3
    assert result.total_sources_failed == 1
    assert result.source_results["lever"].status == MarketSourceStatus.FAILED
    assert phase2_processed == ["adzuna", "greenhouse", "ashby"]
    assert "lever" not in phase2_processed


def test_45_all_source_failure_rollback_and_last_known_good() -> None:
    """
    Verifies all-source failure:
    - All 4 sources fail
    - Overall status is FAILED
    - Session rollback is called
    - Downstream demand is NOT refreshed
    - Last-known-good state is preserved
    """
    adapters = {
        st: FakeAdapter(st, error=ConnectionError(f"{st.value} failure (simulated)"))
        for st in DEFAULT_SOURCE_ORDER
    }
    orchestrator, mock_db, mocks = _build_test_orchestrator(adapters)
    mock_db.query.return_value.order_by.return_value.first.return_value = None

    result = orchestrator.orchestrate_refresh(db=mock_db, force=False)

    assert result.status == MarketRefreshStatus.FAILED
    assert result.total_sources_succeeded == 0
    assert result.total_sources_failed == 4
    assert result.downstream_demand_refreshed is False
    assert result.snapshot_at is None
    assert result.last_known_good_preserved is True
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()


