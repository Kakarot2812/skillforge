"""
Unit and integration tests for P1-G Multi-Source Market Ingestion Foundation.

Verifies:
1. Source type values (ADZUNA, GREENHOUSE, LEVER, ASHBY) and from_str normalization.
2. Common adapter contract enforcement (ABC properties and methods).
3. Registry resolves Adzuna adapter via enum, lowercase, and uppercase strings.
4. Registry rejects unknown source names with typed UnknownMarketSourceError.
5. Registry rejects unsupported Greenhouse with typed UnsupportedMarketSourceError.
6. Registry rejects unsupported Lever with typed UnsupportedMarketSourceError.
7. Registry rejects unsupported Ashby with typed UnsupportedMarketSourceError.
8. Adzuna adapter returns the existing NormalizedMarketJob contract.
9. Source metadata and provenance are strictly preserved.
10. Existing Adzuna client, cleaning, and ingestion behavior remains 100% compatible.
"""

from unittest.mock import MagicMock
import pytest

from app.services.market.adapters import (
    AdzunaAdapter,
    MarketSourceAdapter,
    MarketSourceConfigurationError,
    MarketSourceError,
    MarketSourceRegistry,
    MarketSourceType,
    UnknownMarketSourceError,
    UnsupportedMarketSourceError,
    get_market_source_adapter,
    market_source_registry,
)
from app.services.market.clients.adzuna_client import (
    AdzunaClient,
    AdzunaJobItem,
    AdzunaSearchResponse,
)
from app.services.market.ingestion.adzuna_ingestion import AdzunaIngestionService
from app.services.market.models import NormalizedMarketJob


# ===========================================================================
# 1. Source Type Values
# ===========================================================================

def test_01_market_source_type_enum_values():
    """TEST 1: MarketSourceType contains ADZUNA, GREENHOUSE, LEVER, ASHBY with correct values."""
    assert MarketSourceType.ADZUNA.value == "adzuna"
    assert MarketSourceType.GREENHOUSE.value == "greenhouse"
    assert MarketSourceType.LEVER.value == "lever"
    assert MarketSourceType.ASHBY.value == "ashby"

    # All 4 sources are present in enumeration
    member_names = {m.name for m in MarketSourceType}
    assert member_names == {"ADZUNA", "GREENHOUSE", "LEVER", "ASHBY"}

    # from_str resolver tests
    assert MarketSourceType.from_str("adzuna") == MarketSourceType.ADZUNA
    assert MarketSourceType.from_str("ADZUNA") == MarketSourceType.ADZUNA
    assert MarketSourceType.from_str("AdZuNa") == MarketSourceType.ADZUNA
    assert MarketSourceType.from_str("greenhouse") == MarketSourceType.GREENHOUSE
    assert MarketSourceType.from_str("GREENHOUSE") == MarketSourceType.GREENHOUSE
    assert MarketSourceType.from_str("lever") == MarketSourceType.LEVER
    assert MarketSourceType.from_str("LEVER") == MarketSourceType.LEVER
    assert MarketSourceType.from_str("ashby") == MarketSourceType.ASHBY
    assert MarketSourceType.from_str("ASHBY") == MarketSourceType.ASHBY

    # Idempotent if already MarketSourceType
    assert MarketSourceType.from_str(MarketSourceType.ADZUNA) == MarketSourceType.ADZUNA


# ===========================================================================
# 2. Common Adapter Contract
# ===========================================================================

def test_02_market_source_adapter_abc_contract():
    """TEST 2: MarketSourceAdapter is an ABC that cannot be instantiated without required methods."""
    class IncompleteAdapter(MarketSourceAdapter):
        pass

    with pytest.raises(TypeError) as exc_info:
        IncompleteAdapter()  # type: ignore

    # Verify abstract methods are enforced
    err_str = str(exc_info.value)
    assert "Can't instantiate abstract class" in err_str or "abstract methods" in err_str

    # Valid subclass implementation succeeds
    class DummyAdapter(MarketSourceAdapter):
        @property
        def source_type(self) -> MarketSourceType:
            return MarketSourceType.ADZUNA

        @property
        def is_configured(self) -> bool:
            return True

        def fetch_and_normalize_jobs(self, queries=None, **kwargs):
            return []

        def normalize_job(self, raw_job):
            return None

    adapter = DummyAdapter()
    assert adapter.source_type == MarketSourceType.ADZUNA
    assert adapter.source_name == "adzuna"
    assert adapter.is_configured is True
    assert adapter.fetch_and_normalize_jobs() == []
    assert adapter.normalize_job({}) is None


# ===========================================================================
# 3. Registry Resolves Adzuna
# ===========================================================================

def test_03_registry_resolves_adzuna():
    """TEST 3: MarketSourceRegistry resolves ADZUNA to an AdzunaAdapter instance."""
    registry = MarketSourceRegistry()

    # Via Enum
    adapter_enum = registry.get_adapter(MarketSourceType.ADZUNA)
    assert isinstance(adapter_enum, AdzunaAdapter)
    assert adapter_enum.source_type == MarketSourceType.ADZUNA
    assert adapter_enum.source_name == "adzuna"

    # Via lowercase string
    adapter_lower = registry.get_adapter("adzuna")
    assert isinstance(adapter_lower, AdzunaAdapter)

    # Via uppercase string
    adapter_upper = registry.get_adapter("ADZUNA")
    assert isinstance(adapter_upper, AdzunaAdapter)

    # Convenience function using singleton registry
    global_adapter = get_market_source_adapter("adzuna")
    assert isinstance(global_adapter, AdzunaAdapter)

    # is_supported helper
    assert registry.is_supported(MarketSourceType.ADZUNA) is True
    assert registry.is_supported("adzuna") is True
    assert registry.is_supported("ADZUNA") is True

    # Check supported sources list
    assert MarketSourceType.ADZUNA in registry.get_supported_sources()


# ===========================================================================
# 4. Registry Rejects Unknown Source
# ===========================================================================

def test_04_registry_rejects_unknown_source():
    """TEST 4: Registry rejects unknown or unmapped sources with UnknownMarketSourceError."""
    registry = MarketSourceRegistry()

    with pytest.raises(UnknownMarketSourceError) as exc_info:
        registry.get_adapter("indeed")
    assert "Unknown market source 'indeed'" in str(exc_info.value)

    with pytest.raises(UnknownMarketSourceError):
        registry.get_adapter("linkedin")

    with pytest.raises(UnknownMarketSourceError):
        registry.get_adapter("")

    with pytest.raises(UnknownMarketSourceError):
        registry.get_adapter("   ")

    with pytest.raises(UnknownMarketSourceError):
        registry.get_adapter(None)  # type: ignore

    # is_supported returns False without throwing
    assert registry.is_supported("indeed") is False
    assert registry.is_supported("monster") is False
    assert registry.is_supported("") is False


# ===========================================================================
# 5. Registry Rejects Unsupported Greenhouse
# ===========================================================================

def test_05_registry_rejects_unsupported_greenhouse():
    """TEST 5: Registry rejects GREENHOUSE with typed UnsupportedMarketSourceError."""
    registry = MarketSourceRegistry()

    # Via Enum
    with pytest.raises(UnsupportedMarketSourceError) as exc_info:
        registry.get_adapter(MarketSourceType.GREENHOUSE)
    assert "Market source 'greenhouse' is not implemented yet" in str(exc_info.value)

    # Via String
    with pytest.raises(UnsupportedMarketSourceError):
        registry.get_adapter("greenhouse")

    with pytest.raises(UnsupportedMarketSourceError):
        registry.get_adapter("GREENHOUSE")

    # Never silently falls back to Adzuna
    assert registry.is_supported(MarketSourceType.GREENHOUSE) is False
    assert registry.is_supported("greenhouse") is False


# ===========================================================================
# 6. Registry Rejects Unsupported Lever
# ===========================================================================

def test_06_registry_rejects_unsupported_lever():
    """TEST 6: Registry rejects LEVER with typed UnsupportedMarketSourceError."""
    registry = MarketSourceRegistry()

    with pytest.raises(UnsupportedMarketSourceError) as exc_info:
        registry.get_adapter(MarketSourceType.LEVER)
    assert "Market source 'lever' is not implemented yet" in str(exc_info.value)

    with pytest.raises(UnsupportedMarketSourceError):
        registry.get_adapter("lever")

    assert registry.is_supported(MarketSourceType.LEVER) is False


# ===========================================================================
# 7. Registry Rejects Unsupported Ashby
# ===========================================================================

def test_07_registry_rejects_unsupported_ashby():
    """TEST 7: Registry rejects ASHBY with typed UnsupportedMarketSourceError."""
    registry = MarketSourceRegistry()

    with pytest.raises(UnsupportedMarketSourceError) as exc_info:
        registry.get_adapter(MarketSourceType.ASHBY)
    assert "Market source 'ashby' is not implemented yet" in str(exc_info.value)

    with pytest.raises(UnsupportedMarketSourceError):
        registry.get_adapter("ashby")

    assert registry.is_supported(MarketSourceType.ASHBY) is False


# ===========================================================================
# 8. Adzuna Adapter Returns Existing Normalized Job Contract
# ===========================================================================

def test_08_adzuna_adapter_returns_normalized_job_contract():
    """TEST 8: AdzunaAdapter transforms raw postings into canonical NormalizedMarketJob objects."""
    # Set up mock client returning a single test posting
    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[
            AdzunaJobItem(
                id="adzuna-999",
                title="Lead Backend Engineer",
                description="We need FastAPI, Docker, and PostgreSQL expertise.",
                company_name="Tech Solutions Ltd",
                location_name="Bengaluru, India",
                category_label="IT Jobs",
                created="2026-09-10T12:00:00Z",
                redirect_url="https://adzuna.in/job/999",
                salary_min=1500000.0,
                salary_max=2500000.0,
                raw_data={"id": "adzuna-999", "contract_type": "permanent"},
            )
        ],
        total_count=1,
        page=1,
        country="in",
        raw_response={},
    )

    adapter = AdzunaAdapter(client=mock_client)
    jobs = adapter.fetch_and_normalize_jobs(queries=["backend engineer"], country="in")

    assert len(jobs) == 1
    job = jobs[0]

    # Verify existing NormalizedMarketJob contract
    assert isinstance(job, NormalizedMarketJob)
    assert job.source == "adzuna"
    assert job.external_job_id == "adzuna-999"
    assert job.title == "Lead Backend Engineer"
    assert "FastAPI, Docker, and PostgreSQL" in (job.description or "")
    assert job.company_name == "Tech Solutions Ltd"
    assert job.location == "Bengaluru, India"
    assert job.category == "IT Jobs"
    assert job.redirect_url == "https://adzuna.in/job/999"
    assert job.created_at == "2026-09-10T12:00:00Z"
    assert job.contract_type == "permanent"

    # Verify normalize_job directly on AdzunaJobItem
    single_normalized = adapter.normalize_job(mock_client.search_jobs.return_value.results[0])
    assert isinstance(single_normalized, NormalizedMarketJob)
    assert single_normalized.external_job_id == "adzuna-999"

    # Verify normalize_job directly on raw dict
    dict_payload = {
        "id": "adzuna-888",
        "title": "Senior Python Developer",
        "description": "Python expert required.",
        "company": {"display_name": "Innovate Inc"},
        "location": {"display_name": "Hyderabad"},
    }
    from_dict_job = adapter.normalize_job(dict_payload)
    assert isinstance(from_dict_job, NormalizedMarketJob)
    assert from_dict_job.external_job_id == "adzuna-888"
    assert from_dict_job.title == "Senior Python Developer"
    assert from_dict_job.company_name == "Innovate Inc"
    assert from_dict_job.location == "Hyderabad"


# ===========================================================================
# 9. Source Metadata Is Preserved
# ===========================================================================

def test_09_source_metadata_is_preserved():
    """TEST 9: Source identity, upstream external ID, and raw payload provenance are strictly preserved."""
    raw_payload = {
        "id": "adzuna-meta-42",
        "title": "Machine Learning Engineer",
        "description": "PyTorch, scikit-learn, and MLOps.",
        "category": {"label": "Data Science"},
        "custom_provider_field": "upstream-token-12345",
    }

    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[
            AdzunaJobItem(
                id=raw_payload["id"],
                title=raw_payload["title"],
                description=raw_payload["description"],
                category_label="Data Science",
                raw_data=raw_payload,
            )
        ],
        total_count=1,
        page=1,
        country="in",
        raw_response={"count": 1},
    )

    adapter = AdzunaAdapter(client=mock_client)
    jobs = adapter.fetch_and_normalize_jobs(queries=["ml engineer"])
    job = jobs[0]

    # Source identity must never be lost or replaced
    assert job.source == "adzuna"
    assert job.external_job_id == "adzuna-meta-42"
    assert job.deduplication_key == ("adzuna", "adzuna-meta-42")

    # Raw upstream provenance preserved in raw_data
    assert job.raw_data.get("custom_provider_field") == "upstream-token-12345"
    assert job.raw_data.get("id") == "adzuna-meta-42"


# ===========================================================================
# 10. Existing Adzuna Behavior Remains Compatible
# ===========================================================================

def test_10_existing_adzuna_behavior_remains_compatible():
    """TEST 10: Existing AdzunaIngestionService works seamlessly with AdzunaAdapter."""
    mock_client = MagicMock(spec=AdzunaClient)
    mock_client.search_jobs.return_value = AdzunaSearchResponse(
        results=[
            AdzunaJobItem(id="1", title="Engineer 1", description="Desc 1", raw_data={}),
            AdzunaJobItem(id="1", title="Engineer 1", description="Desc 1", raw_data={}),  # duplicate
            AdzunaJobItem(id="", title="Invalid No ID", description="Desc", raw_data={}),   # invalid
            AdzunaJobItem(id="2", title="", description="Invalid No Title", raw_data={}),   # invalid
            AdzunaJobItem(id="3", title="Engineer 2", description="Desc 2", raw_data={}),
        ],
        total_count=5,
        page=1,
        country="in",
        raw_response={},
    )

    ingestion_service = AdzunaIngestionService(client=mock_client)
    adapter = AdzunaAdapter(ingestion_service=ingestion_service)

    jobs = adapter.fetch_and_normalize_jobs(queries=["test query"])

    # Deduplication and cleaning behavior preserved: 2 unique valid jobs retained
    assert len(jobs) == 2
    assert [j.external_job_id for j in jobs] == ["1", "3"]

    # All jobs are NormalizedMarketJob instances with source "adzuna"
    for j in jobs:
        assert isinstance(j, NormalizedMarketJob)
        assert j.source == "adzuna"


# ===========================================================================
# 11. Registry Custom Registration
# ===========================================================================

def test_11_registry_custom_registration_and_isolation():
    """TEST 11: Registry allows registering mock/custom adapters and enforces type safety."""
    registry = MarketSourceRegistry(register_defaults=False)
    assert len(registry.get_supported_sources()) == 0

    class MockGreenhouseAdapter(MarketSourceAdapter):
        @property
        def source_type(self) -> MarketSourceType:
            return MarketSourceType.GREENHOUSE

        @property
        def is_configured(self) -> bool:
            return True

        def fetch_and_normalize_jobs(self, queries=None, **kwargs):
            return [
                NormalizedMarketJob(
                    source="greenhouse",
                    external_job_id="gh-101",
                    title="Platform Engineer",
                )
            ]

        def normalize_job(self, raw_job):
            return None

    # Register custom adapter
    registry.register_adapter(MarketSourceType.GREENHOUSE, MockGreenhouseAdapter())
    assert registry.is_supported(MarketSourceType.GREENHOUSE) is True

    adapter = registry.get_adapter("greenhouse")
    assert adapter.source_type == MarketSourceType.GREENHOUSE
    jobs = adapter.fetch_and_normalize_jobs()
    assert len(jobs) == 1
    assert jobs[0].source == "greenhouse"

    # Invalid registration rejected with TypeError
    with pytest.raises(TypeError):
        registry.register_adapter("not_enum", MockGreenhouseAdapter())  # type: ignore

    with pytest.raises(TypeError):
        registry.register_adapter(MarketSourceType.LEVER, "not_an_adapter")  # type: ignore
