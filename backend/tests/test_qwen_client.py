"""
Unit tests for Local Qwen 3 8B / Ollama client foundation (Post-MVP Checkpoint P2-A).

Verifies all 15 required specifications:
1. Configuration defaults
2. Custom Ollama base URL
3. Custom model name
4. Successful request
5. Successful response parsing
6. Connection failure
7. Timeout
8. HTTP error
9. Malformed response
10. Missing response field
11. Model-unavailable handling
12. Bounded timeout behavior
13. No credentials required
14. Client does not write to database
15. Client remains generic and contains no SkillForge business decision logic
"""

import json
from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.config import settings
from app.ai.qwen.client import QwenClient
from app.ai.qwen.exceptions import (
    QwenAPIError,
    QwenConfigurationError,
    QwenConnectionError,
    QwenError,
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
)
from app.ai.qwen.models import (
    QwenChatResponse,
    QwenGenerateResponse,
    QwenHealthStatus,
    QwenMessage,
)


# ===========================================================================
# 1. CONFIGURATION TESTS (1 - 3, 12)
# ===========================================================================

def test_1_configuration_defaults():
    """1. Verifies default configuration matches settings."""
    client = QwenClient()
    assert client.base_url == settings.OLLAMA_BASE_URL.rstrip("/")
    assert client.model == settings.OLLAMA_MODEL
    assert client.timeout_seconds == settings.OLLAMA_TIMEOUT_SECONDS
    assert client.base_url == "http://localhost:11434"
    assert client.model == "qwen3:8b"
    assert client.timeout_seconds == 60.0
    client.close()


def test_2_custom_ollama_base_url():
    """2. Verifies custom Ollama base URL is trimmed and configured."""
    client = QwenClient(base_url="http://192.168.1.50:11434/")
    assert client.base_url == "http://192.168.1.50:11434"
    client.close()


def test_3_custom_model_name():
    """3. Verifies custom model name is accepted."""
    client = QwenClient(model="custom-qwen3:8b-instruct")
    assert client.model == "custom-qwen3:8b-instruct"
    client.close()


def test_12_bounded_timeout_behavior():
    """12. Verifies bounded timeout behavior and rejection of invalid timeouts."""
    client = QwenClient(timeout_seconds=45.0)
    assert client.timeout_seconds == 45.0
    client.close()

    # Non-positive timeouts must be rejected
    with pytest.raises(QwenConfigurationError, match="positive number"):
        QwenClient(timeout_seconds=0)

    with pytest.raises(QwenConfigurationError, match="positive number"):
        QwenClient(timeout_seconds=-10.0)

    # Empty base URL must be rejected
    with pytest.raises(QwenConfigurationError, match="base URL"):
        QwenClient(base_url="")

    # Empty model must be rejected
    with pytest.raises(QwenConfigurationError, match="model name"):
        QwenClient(model="")


# ===========================================================================
# 2. REQUEST / RESPONSE TESTS (4, 5, 15)
# ===========================================================================

def test_4_successful_chat_request():
    """4. Verifies successful chat request construction and delivery."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "model": "qwen3:8b",
            "message": {"role": "assistant", "content": "QWEN_OK"},
            "done": True,
            "done_reason": "stop",
            "total_duration": 1500000,
            "prompt_eval_count": 10,
            "eval_count": 5,
        },
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    mock_http.request.return_value = mock_resp

    client = QwenClient(http_client=mock_http)
    response = client.chat(
        messages=[QwenMessage(role="user", content="Ping")],
        system="You are a helpful assistant.",
    )

    # Verify request payload
    mock_http.request.assert_called_once()
    call_args = mock_http.request.call_args
    assert call_args.kwargs["method"] == "POST"
    assert call_args.kwargs["url"] == "http://localhost:11434/api/chat"
    payload = call_args.kwargs["json"]
    assert payload["model"] == "qwen3:8b"
    assert payload["stream"] is False
    assert len(payload["messages"]) == 2
    assert payload["messages"][0] == {"role": "system", "content": "You are a helpful assistant."}
    assert payload["messages"][1] == {"role": "user", "content": "Ping"}

    assert response.content == "QWEN_OK"
    assert response.message.role == "assistant"
    assert response.done is True


def test_5_successful_response_parsing():
    """5. Verifies thorough response parsing for both chat and generate."""
    mock_http = MagicMock(spec=httpx.Client)
    client = QwenClient(http_client=mock_http)

    # Chat response parsing
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        json={
            "model": "qwen3:8b",
            "message": {"role": "assistant", "content": "Acknowledged successfully."},
            "done": True,
            "done_reason": "stop",
            "total_duration": 42000000,
            "load_duration": 1200000,
            "prompt_eval_count": 25,
            "eval_count": 18,
        },
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    chat_res = client.chat(messages=[{"role": "user", "content": "Status?"}])
    assert isinstance(chat_res, QwenChatResponse)
    assert chat_res.content == "Acknowledged successfully."
    assert chat_res.eval_count == 18
    assert chat_res.prompt_eval_count == 25
    assert chat_res.total_duration == 42000000
    res_dict = chat_res.to_dict()
    assert res_dict["message"]["content"] == "Acknowledged successfully."

    # Generate response parsing
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        json={
            "model": "qwen3:8b",
            "response": "Generated text response.",
            "done": True,
            "done_reason": "stop",
            "total_duration": 30000000,
            "prompt_eval_count": 12,
            "eval_count": 10,
        },
        request=httpx.Request("POST", "http://localhost:11434/api/generate"),
    )

    gen_res = client.generate(prompt="Explain testing.")
    assert isinstance(gen_res, QwenGenerateResponse)
    assert gen_res.content == "Generated text response."
    assert gen_res.response == "Generated text response."
    assert gen_res.eval_count == 10
    gen_dict = gen_res.to_dict()
    assert gen_dict["response"] == "Generated text response."


def test_15_client_remains_generic_and_contains_no_business_logic():
    """15. Verifies client answers generic prompts without knowing domain entities."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        json={
            "model": "qwen3:8b",
            "message": {"role": "assistant", "content": "ACK"},
            "done": True,
        },
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )

    client = QwenClient(http_client=mock_http)
    res = client.chat(messages=[{"role": "user", "content": "Return a short acknowledgement."}])
    assert res.content == "ACK"

    # Confirm client has zero candidate/skill/gap/market methods
    client_attrs = dir(client)
    assert "extract_skills" not in client_attrs
    assert "compute_gaps" not in client_attrs
    assert "calculate_demand" not in client_attrs
    assert "prioritize" not in client_attrs
    assert "build_roadmap" not in client_attrs


# ===========================================================================
# 3. ERROR HANDLING TESTS (6 - 11)
# ===========================================================================

def test_6_connection_failure():
    """6. Verifies network / connection failures raise QwenConnectionError."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.request.side_effect = httpx.ConnectError("Connection refused by peer")

    client = QwenClient(http_client=mock_http)
    with pytest.raises(QwenConnectionError, match="Failed to connect to local Ollama"):
        client.chat(messages=[{"role": "user", "content": "Hello"}])


def test_7_timeout():
    """7. Verifies request timeout raises QwenTimeoutError."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.request.side_effect = httpx.TimeoutException("Read timed out")

    client = QwenClient(http_client=mock_http)
    with pytest.raises(QwenTimeoutError, match="timed out"):
        client.chat(messages=[{"role": "user", "content": "Hello"}])


def test_8_http_error():
    """8. Verifies non-2xx HTTP status codes raise QwenAPIError."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_resp = httpx.Response(
        status_code=500,
        text="Internal Server Error: model runner crashed",
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    mock_http.request.return_value = mock_resp

    client = QwenClient(http_client=mock_http)
    with pytest.raises(QwenAPIError) as exc_info:
        client.chat(messages=[{"role": "user", "content": "Hello"}])

    assert exc_info.value.status_code == 500
    assert "Internal Server Error" in exc_info.value.response_body


def test_9_malformed_response():
    """9. Verifies non-JSON response raises QwenResponseError."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_resp = httpx.Response(
        status_code=200,
        text="<html><body>Gateway Error</body></html>",
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    mock_http.request.return_value = mock_resp

    client = QwenClient(http_client=mock_http)
    with pytest.raises(QwenResponseError, match="Failed to decode"):
        client.chat(messages=[{"role": "user", "content": "Hello"}])


def test_10_missing_response_field():
    """10. Verifies missing required fields in response raises QwenResponseError."""
    mock_http = MagicMock(spec=httpx.Client)
    client = QwenClient(http_client=mock_http)

    # Chat missing 'message'
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "done": True},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    with pytest.raises(QwenResponseError, match="missing expected 'message.content'"):
        client.chat(messages=[{"role": "user", "content": "Hello"}])

    # Generate missing 'response'
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "done": True},
        request=httpx.Request("POST", "http://localhost:11434/api/generate"),
    )
    with pytest.raises(QwenResponseError, match="missing expected 'response'"):
        client.generate(prompt="Hello")


def test_11_model_unavailable_handling():
    """11. Verifies model not found raises QwenModelNotFoundError."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_resp = httpx.Response(
        status_code=404,
        json={"error": "model 'qwen3:8b' not found, try pulling it first"},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    mock_http.request.return_value = mock_resp

    client = QwenClient(model="qwen3:8b", http_client=mock_http)
    with pytest.raises(QwenModelNotFoundError) as exc_info:
        client.chat(messages=[{"role": "user", "content": "Hello"}])

    assert exc_info.value.model_name == "qwen3:8b"
    assert exc_info.value.status_code == 404


# ===========================================================================
# 4. HEALTH & CONNECTIVITY TESTS
# ===========================================================================

def test_health_check_success():
    """Verifies health check when Ollama is reachable and model is installed."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        json={"models": [{"name": "qwen3:8b"}, {"name": "llama3:latest"}]},
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )

    client = QwenClient(model="qwen3:8b", http_client=mock_http)
    status = client.check_health()
    assert status.reachable is True
    assert status.model_available is True
    assert status.is_healthy is True
    assert "qwen3:8b" in status.available_models
    assert status.configured_model == "qwen3:8b"


def test_health_check_ollama_offline():
    """Verifies health check when Ollama is offline does not raise exception unless asked."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.request.side_effect = httpx.ConnectError("Connection refused")

    client = QwenClient(http_client=mock_http)
    # Default: returns health status object without crashing
    status = client.check_health(raise_on_error=False)
    assert status.reachable is False
    assert status.model_available is False
    assert status.is_healthy is False

    # raise_on_error=True raises QwenConnectionError
    with pytest.raises(QwenConnectionError):
        client.check_health(raise_on_error=True)


def test_health_check_model_missing():
    """Verifies health check when Ollama is online but configured model is missing."""
    mock_http = MagicMock(spec=httpx.Client)
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        json={"models": [{"name": "llama3:8b"}, {"name": "mistral:7b"}]},
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )

    client = QwenClient(model="qwen3:8b", http_client=mock_http)
    status = client.check_health(raise_on_error=False)
    assert status.reachable is True
    assert status.model_available is False
    assert status.is_healthy is False

    with pytest.raises(QwenModelNotFoundError):
        client.check_health(raise_on_error=True)


# ===========================================================================
# 5. SECURITY & ISOLATION TESTS (13, 14)
# ===========================================================================

def test_13_no_credentials_required():
    """13. Verifies no API keys, bearer tokens, or secrets are used or required."""
    client = QwenClient()
    assert not hasattr(client, "api_key")
    assert not hasattr(client, "app_key")
    assert not hasattr(client, "token")

    mock_http = MagicMock(spec=httpx.Client)
    mock_http.request.return_value = httpx.Response(
        status_code=200,
        json={"model": "qwen3:8b", "message": {"role": "assistant", "content": "OK"}},
        request=httpx.Request("POST", "http://localhost:11434/api/chat"),
    )
    client._client = mock_http
    client.chat(messages=[{"role": "user", "content": "test"}])

    call_args = mock_http.request.call_args
    headers = call_args.kwargs.get("headers") or {}
    for h in headers.keys():
        assert h.lower() != "authorization"
        assert h.lower() != "x-api-key"


def test_14_client_does_not_write_to_database():
    """14. Verifies QwenClient is completely stateless and has zero database interactions."""
    import inspect
    from app.ai.qwen import client as client_module

    source_code = inspect.getsource(client_module)
    assert "Session" not in source_code
    assert "get_db" not in source_code
    assert "commit" not in source_code
    assert "rollback" not in source_code
    assert "delete" not in source_code
    assert "insert" not in source_code
    assert "update" not in source_code
