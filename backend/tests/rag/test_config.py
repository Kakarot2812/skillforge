import pytest
from pydantic import ValidationError

from app.rag import config as rag_config
from app.rag.config import RagSettings, get_rag_settings
from app.rag.exceptions import RagConfigurationError


@pytest.fixture(autouse=True)
def clear_cache():
    get_rag_settings.cache_clear()
    yield
    get_rag_settings.cache_clear()


def test_defaults_are_portable(monkeypatch):
    for var in (
        "RAG_ENABLED", "RAG_EMBEDDING_MODEL", "RAG_OLLAMA_BASE_URL",
        "RAG_EMBEDDING_DIMENSIONS", "RAG_TOP_K", "RAG_CHUNK_SIZE",
    ):
        monkeypatch.delenv(var, raising=False)
    s = RagSettings(_env_file=None)
    assert s.RAG_ENABLED is True
    assert s.RAG_EMBEDDING_MODEL == "qwen3-embedding:8b"
    assert s.RAG_OLLAMA_BASE_URL == "http://localhost:11434"
    assert s.RAG_EMBEDDING_DIMENSIONS == 1024
    assert s.RAG_TOP_K == 8
    assert s.RAG_CANDIDATE_K == 20
    assert s.RAG_CHUNK_SIZE == 1600
    assert s.RAG_CHUNK_OVERLAP == 200


def test_reads_environment_variables(monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDING_MODEL", "qwen3-embedding:4b")
    monkeypatch.setenv("RAG_OLLAMA_BASE_URL", "http://gpu-box:11434/")
    monkeypatch.setenv("RAG_EMBEDDING_DIMENSIONS", "512")
    monkeypatch.setenv("RAG_TOP_K", "5")
    s = RagSettings(_env_file=None)
    assert s.RAG_EMBEDDING_MODEL == "qwen3-embedding:4b"
    assert s.RAG_OLLAMA_BASE_URL == "http://gpu-box:11434"  # trailing slash stripped
    assert s.RAG_EMBEDDING_DIMENSIONS == 512
    assert s.RAG_TOP_K == 5


@pytest.mark.parametrize("url", ["localhost:11434", "ftp://host:11434", "http://localhost:11434/api"])
def test_rejects_bad_base_url(url):
    with pytest.raises(ValidationError):
        RagSettings(_env_file=None, RAG_OLLAMA_BASE_URL=url)


@pytest.mark.parametrize(
    "field,value",
    [
        ("RAG_EMBEDDING_DIMENSIONS", 0),
        ("RAG_EMBEDDING_DIMENSIONS", 5000),
        ("RAG_TOP_K", 0),
        ("RAG_EMBEDDING_MODEL", "qwen embed"),
        ("RAG_EMBEDDING_TIMEOUT", 0),
    ],
)
def test_rejects_out_of_range_values(field, value):
    with pytest.raises(ValidationError):
        RagSettings(_env_file=None, **{field: value})


def test_rejects_overlap_not_smaller_than_chunk_size():
    with pytest.raises(ValidationError):
        RagSettings(_env_file=None, RAG_CHUNK_SIZE=500, RAG_CHUNK_OVERLAP=500)


def test_get_settings_wraps_errors_in_configuration_error(monkeypatch):
    monkeypatch.setenv("RAG_TOP_K", "0")
    monkeypatch.setattr(
        rag_config.RagSettings,
        "model_config",
        {**rag_config.RagSettings.model_config, "env_file": None},
    )
    with pytest.raises(RagConfigurationError) as info:
        get_rag_settings()
    assert "RAG_TOP_K" in (info.value.detail or "")
    assert "RAG_TOP_K" not in info.value.public_message
