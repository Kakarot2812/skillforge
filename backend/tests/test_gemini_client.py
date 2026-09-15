"""
Focused test suite for SkillForge AI Post-MVP Phase 1:
Google Gemini 2.5 Flash LangChain Integration Foundation.

Verifies:
1. Configuration reads GEMINI_API_KEY, GEMINI_MODEL, and GEMINI_TIMEOUT_SECONDS correctly.
2. Default model is 'gemini-2.5-flash'.
3. API key is never exposed in configuration repr or client repr.
4. GeminiClient initializes cleanly with valid configuration.
5. Missing, blank, or None API key raises GeminiConfigurationError.
6. Invalid model, temperature, or timeout raises GeminiConfigurationError.
7. Provider exceptions are safely mapped to typed GeminiError subclasses.
8. Messages and logs are scrubbed to prevent credential leakage.
9. with_structured_output foundation returns a safe runnable and handles structured extraction.
10. GeminiClient remains completely decoupled from roadmap and PDF domain modules.
11. Opt-in live integration test skips cleanly when real API key is absent.
"""

import os
import sys
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from app.config import Settings
from app.ai.gemini import (
    GeminiAPIError,
    GeminiAuthenticationError,
    GeminiClient,
    GeminiConfigurationError,
    GeminiConnectionError,
    GeminiError,
    GeminiResponseError,
    GeminiTimeoutError,
    sanitize_gemini_message,
)


# -----------------------------------------------------------------------------
# 1. Configuration Tests
# -----------------------------------------------------------------------------

def test_gemini_config_defaults():
    """Verifies default Gemini configuration settings."""
    cfg = Settings(
        GEMINI_API_KEY=None,
        _env_file=None,
    )
    assert cfg.GEMINI_MODEL == "gemini-2.5-flash"
    assert cfg.GEMINI_TIMEOUT_SECONDS == 30.0
    assert cfg.GEMINI_API_KEY is None


def test_gemini_config_reads_env_vars(monkeypatch):
    """Verifies that Settings correctly reads Gemini environment variables."""
    test_key = "AIzaSyFakeTestKeyForTesting1234567890"
    monkeypatch.setenv("GEMINI_API_KEY", test_key)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-custom")
    monkeypatch.setenv("GEMINI_TIMEOUT_SECONDS", "45.0")

    cfg = Settings(_env_file=None)
    assert cfg.GEMINI_API_KEY == test_key
    assert cfg.GEMINI_MODEL == "gemini-2.5-flash-custom"
    assert cfg.GEMINI_TIMEOUT_SECONDS == 45.0


def test_gemini_api_key_not_exposed_in_repr(monkeypatch):
    """Verifies that GEMINI_API_KEY is not leaked in Settings repr string."""
    secret_key = "AIzaSyUltraSecretKeyThatMustNeverAppearInLogs"
    monkeypatch.setenv("GEMINI_API_KEY", secret_key)

    cfg = Settings(_env_file=None)
    repr_str = repr(cfg)

    assert secret_key not in repr_str
    assert "GEMINI_MODEL='gemini-2.5-flash'" in repr_str or "gemini-2.5-flash" in repr_str


# -----------------------------------------------------------------------------
# 2. Client Initialization & Validation Tests
# -----------------------------------------------------------------------------

def test_gemini_client_initialization_with_explicit_key():
    """Verifies that GeminiClient initializes with explicit parameters."""
    client = GeminiClient(
        api_key="fake-test-key-for-init-9876543210",
        model="gemini-2.5-flash",
        temperature=0.2,
        timeout_seconds=25.0,
    )
    assert client.model == "gemini-2.5-flash"
    assert client.temperature == 0.2
    assert client.timeout_seconds == 25.0
    assert client.get_chat_model() is not None


def test_gemini_client_missing_api_key_raises():
    """Verifies that GeminiClient raises GeminiConfigurationError when no API key is available."""
    with patch("app.ai.gemini.client.settings.GEMINI_API_KEY", None):
        with pytest.raises(GeminiConfigurationError) as exc_info:
            GeminiClient(api_key=None)
        assert "GEMINI_API_KEY must be configured" in str(exc_info.value)


def test_gemini_client_empty_api_key_raises():
    """Verifies that a blank or whitespace API key raises GeminiConfigurationError."""
    with pytest.raises(GeminiConfigurationError) as exc_info:
        GeminiClient(api_key="   ")
    assert "GEMINI_API_KEY must be configured" in str(exc_info.value)


def test_gemini_client_invalid_model_raises():
    """Verifies that an empty model name raises GeminiConfigurationError."""
    with pytest.raises(GeminiConfigurationError) as exc_info:
        GeminiClient(api_key="valid-key", model="  ")
    assert "model name must be a non-empty string" in str(exc_info.value)


def test_gemini_client_invalid_temperature_raises():
    """Verifies that temperature outside [0.0, 2.0] raises GeminiConfigurationError."""
    with pytest.raises(GeminiConfigurationError) as exc_info:
        GeminiClient(api_key="valid-key", temperature=2.5)
    assert "temperature must be between 0.0 and 2.0" in str(exc_info.value)

    with pytest.raises(GeminiConfigurationError):
        GeminiClient(api_key="valid-key", temperature=-0.1)


def test_gemini_client_invalid_timeout_raises():
    """Verifies that zero or negative timeout raises GeminiConfigurationError."""
    with pytest.raises(GeminiConfigurationError) as exc_info:
        GeminiClient(api_key="valid-key", timeout_seconds=0)
    assert "timeout must be a positive number" in str(exc_info.value)

    with pytest.raises(GeminiConfigurationError):
        GeminiClient(api_key="valid-key", timeout_seconds=-5.0)


def test_gemini_client_repr_suppresses_secret():
    """Verifies that GeminiClient repr never contains the API key."""
    secret = "AIzaSySuperSecretKey12345"
    client = GeminiClient(api_key=secret, model="gemini-2.5-flash", temperature=0.2)
    client_repr = repr(client)

    assert secret not in client_repr
    assert "gemini-2.5-flash" in client_repr
    assert "temperature=0.2" in client_repr


# -----------------------------------------------------------------------------
# 3. Message Sanitization Tests
# -----------------------------------------------------------------------------

def test_sanitize_gemini_message_removes_explicit_key():
    """Verifies that sanitize_gemini_message scrubs the provided API key."""
    secret = "secret-key-xyz-789"
    msg = f"Failed connecting with key {secret} on endpoint https://api.google.com"
    sanitized = sanitize_gemini_message(msg, api_key=secret)

    assert secret not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_sanitize_gemini_message_removes_pattern_key():
    """Verifies that standard Google API key patterns are scrubbed automatically."""
    msg = "Error using key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q in request"
    sanitized = sanitize_gemini_message(msg)

    assert "AIzaSy" not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


# -----------------------------------------------------------------------------
# 4. Invocation & Provider Error Mapping Tests (Mocked)
# -----------------------------------------------------------------------------

def test_gemini_client_invoke_success_mocked():
    """Verifies standard chat completion invocation with mocked LangChain model."""
    mock_chat_model = MagicMock()
    mock_chat_model.invoke.return_value = AIMessage(content="Personalized roadmap explanation text.")

    client = GeminiClient(
        api_key="fake-key-for-mock",
        chat_model=mock_chat_model,
    )

    response = client.invoke("Explain roadmap phase 1")
    assert isinstance(response, AIMessage)
    assert response.content == "Personalized roadmap explanation text."
    mock_chat_model.invoke.assert_called_once_with("Explain roadmap phase 1")


def test_gemini_client_maps_auth_error():
    """Verifies that 401/403 or invalid API key errors map to GeminiAuthenticationError."""
    mock_chat_model = MagicMock()
    mock_chat_model.invoke.side_effect = Exception("API key not valid. Please pass a valid API key (INVALID_ARGUMENT 400).")

    client = GeminiClient(api_key="fake-key", chat_model=mock_chat_model)

    with pytest.raises(GeminiAuthenticationError) as exc_info:
        client.invoke("Hello")

    assert "authentication failed" in str(exc_info.value).lower()
    assert "fake-key" not in str(exc_info.value)


def test_gemini_client_maps_timeout_error():
    """Verifies that deadline exceeded or timeout errors map to GeminiTimeoutError."""
    mock_chat_model = MagicMock()
    mock_chat_model.invoke.side_effect = Exception("Deadline_exceeded: Request timed out after 30.0s")

    client = GeminiClient(api_key="fake-key", chat_model=mock_chat_model)

    with pytest.raises(GeminiTimeoutError) as exc_info:
        client.invoke("Hello")

    assert "timed out" in str(exc_info.value).lower()


def test_gemini_client_maps_connection_error():
    """Verifies that network errors map to GeminiConnectionError."""
    mock_chat_model = MagicMock()
    mock_chat_model.invoke.side_effect = Exception("Failed to establish a new connection: Name resolution error")

    client = GeminiClient(api_key="fake-key", chat_model=mock_chat_model)

    with pytest.raises(GeminiConnectionError) as exc_info:
        client.invoke("Hello")

    assert "connection failed" in str(exc_info.value).lower()


def test_gemini_client_maps_generic_api_error():
    """Verifies that arbitrary upstream provider errors map to GeminiAPIError."""
    mock_chat_model = MagicMock()
    err = Exception("Internal 500 error from upstream Google server")
    setattr(err, "status_code", 500)
    mock_chat_model.invoke.side_effect = err

    client = GeminiClient(api_key="fake-key", chat_model=mock_chat_model)

    with pytest.raises(GeminiAPIError) as exc_info:
        client.invoke("Hello")

    assert "invocation failure" in str(exc_info.value).lower()
    assert exc_info.value.status_code == 500


# -----------------------------------------------------------------------------
# 5. Structured Output Foundation Tests (Mocked)
# -----------------------------------------------------------------------------

class MinimalTestSchema(BaseModel):
    """Test schema ensuring with_structured_output works cleanly without domain coupling."""
    category: str
    confidence: float


def test_gemini_client_with_structured_output_returns_runnable():
    """Verifies that with_structured_output returns a safe runnable sequence."""
    client = GeminiClient(api_key="fake-test-key-for-init")
    structured_runnable = client.with_structured_output(MinimalTestSchema)

    assert hasattr(structured_runnable, "invoke")


def test_gemini_client_with_structured_output_invocation_mocked():
    """Verifies that structured invocation executes and catches errors safely."""
    mock_chat_model = MagicMock()
    mock_runnable = MagicMock()
    expected_output = MinimalTestSchema(category="Backend Architecture", confidence=0.95)
    mock_runnable.invoke.return_value = expected_output
    mock_chat_model.with_structured_output.return_value = mock_runnable

    client = GeminiClient(api_key="fake-key", chat_model=mock_chat_model)
    structured_runnable = client.with_structured_output(MinimalTestSchema)

    result = structured_runnable.invoke("Extract competency")
    assert result == expected_output
    assert result.category == "Backend Architecture"
    assert result.confidence == 0.95


def test_gemini_client_with_structured_output_maps_invocation_error():
    """Verifies that structured invocation errors are converted to GeminiError."""
    mock_chat_model = MagicMock()
    mock_runnable = MagicMock()
    mock_runnable.invoke.side_effect = Exception("Validation error parsing model response into schema")
    mock_chat_model.with_structured_output.return_value = mock_runnable

    client = GeminiClient(api_key="fake-key", chat_model=mock_chat_model)
    structured_runnable = client.with_structured_output(MinimalTestSchema)

    with pytest.raises(GeminiResponseError) as exc_info:
        structured_runnable.invoke("Extract competency")

    assert "parsing error" in str(exc_info.value).lower()


# -----------------------------------------------------------------------------
# 6. Independence & Decoupling Verification
# -----------------------------------------------------------------------------

def test_gemini_client_is_independent_of_roadmap_and_pdf():
    """
    Verifies that app.ai.gemini modules do NOT import ReportLab,
    do NOT import CandidateRoadmap, and do NOT import roadmap rendering logic.
    """
    import app.ai.gemini.client as gemini_module
    import app.ai.gemini.exceptions as exc_module

    for mod in [gemini_module, exc_module]:
        source = open(mod.__file__).read()
        assert "reportlab" not in source.lower()
        assert "candidateroadmap" not in source.lower()
        assert "roadmappdfdocument" not in source.lower()
        assert "render" not in source.lower() or "renderer" not in source.lower()


# -----------------------------------------------------------------------------
# 7. Opt-in Live Integration Test (Skipped by default)
# -----------------------------------------------------------------------------

@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_GEMINI_TEST") != "1" or not os.environ.get("GEMINI_API_KEY"),
    reason="Explicit opt-in live test: requires RUN_LIVE_GEMINI_TEST=1 and a valid GEMINI_API_KEY.",
)
def test_gemini_live_integration_opt_in():
    """
    Live test against Google Gemini API.
    Only runs when RUN_LIVE_GEMINI_TEST=1 and real GEMINI_API_KEY is in environment.
    Never prints or logs the API key.
    """
    client = GeminiClient()
    response = client.invoke("Reply with the single word 'VERIFIED' and nothing else.")
    assert response is not None
    assert len(response.content.strip()) > 0
