import pytest
from pydantic import ValidationError

from app.qwen_ai import config as qwen_config
from app.qwen_ai.config import QwenSettings, get_qwen_settings
from app.qwen_ai.exceptions import QwenConfigurationError


@pytest.fixture(autouse=True)
def clear_cache():
    get_qwen_settings.cache_clear()
    yield
    get_qwen_settings.cache_clear()


def test_defaults_are_portable(monkeypatch):
    for var in ("QWEN_MODEL", "QWEN_BASE_URL", "QWEN_TIMEOUT", "QWEN_TEMPERATURE"):
        monkeypatch.delenv(var, raising=False)
    s = QwenSettings(_env_file=None)
    assert s.QWEN_MODEL == "qwen3:8b"
    assert s.QWEN_BASE_URL == "http://localhost:11434"
    assert s.QWEN_TIMEOUT == 120
    assert s.QWEN_TEMPERATURE == 0.6
    assert s.QWEN_THINK is False


def test_reads_environment_variables(monkeypatch):
    monkeypatch.setenv("QWEN_MODEL", "qwen3:4b")
    monkeypatch.setenv("QWEN_BASE_URL", "http://gpu-box:11434/")
    monkeypatch.setenv("QWEN_TIMEOUT", "30")
    monkeypatch.setenv("QWEN_TEMPERATURE", "0.2")
    s = QwenSettings(_env_file=None)
    assert s.QWEN_MODEL == "qwen3:4b"
    assert s.QWEN_BASE_URL == "http://gpu-box:11434"  # trailing slash stripped
    assert s.QWEN_TIMEOUT == 30
    assert s.QWEN_TEMPERATURE == 0.2


@pytest.mark.parametrize("url", ["localhost:11434", "ftp://host:11434", "http://localhost:11434/api"])
def test_rejects_bad_base_url(url):
    with pytest.raises(ValidationError):
        QwenSettings(_env_file=None, QWEN_BASE_URL=url)


@pytest.mark.parametrize("field,value", [("QWEN_TIMEOUT", 0), ("QWEN_TEMPERATURE", 3), ("QWEN_MODEL", "qwen 3")])
def test_rejects_out_of_range_values(field, value):
    with pytest.raises(ValidationError):
        QwenSettings(_env_file=None, **{field: value})


def test_get_settings_wraps_errors_in_configuration_error(monkeypatch):
    monkeypatch.setenv("QWEN_TIMEOUT", "-5")
    monkeypatch.setattr(qwen_config.QwenSettings, "model_config",
                        {**qwen_config.QwenSettings.model_config, "env_file": None})
    with pytest.raises(QwenConfigurationError) as info:
        get_qwen_settings()
    assert "QWEN_TIMEOUT" in (info.value.detail or "")
    assert "QWEN_TIMEOUT" not in info.value.public_message