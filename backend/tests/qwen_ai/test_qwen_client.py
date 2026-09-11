import asyncio

import httpx
import pytest

from app.qwen_ai.exceptions import (
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
    QwenUnavailableError,
)
from app.qwen_ai.qwen_client import QwenMessage, strip_thinking
from tests.qwen_ai.helpers import make_client, ollama_chat_payload, request_json

MESSAGES = [
    QwenMessage(role="system", content="You are SkillForge AI."),
    QwenMessage(role="user", content="What is Docker?"),
]


def run(coro):
    return asyncio.run(coro)


def test_successful_chat_sends_expected_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request_json(request)
        return httpx.Response(200, json=ollama_chat_payload("Docker packages apps into containers."))

    result = run(make_client(handler, QWEN_TEMPERATURE=0.3).chat(MESSAGES))

    assert captured["url"] == "http://ollama.test:11434/api/chat"
    body = captured["body"]
    assert body["model"] == "qwen3:8b"
    assert body["stream"] is False
    assert body["think"] is False
    assert body["options"]["temperature"] == 0.3
    assert body["options"]["num_ctx"] == 8192
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert result.content == "Docker packages apps into containers."
    assert result.model == "qwen3:8b"
    assert result.prompt_tokens == 120 and result.completion_tokens == 40
    assert result.truncated is False


def test_supports_assistant_messages_and_temperature_override():
    def handler(request):
        body = request_json(request)
        assert body["messages"][2]["role"] == "assistant"
        assert body["options"]["temperature"] == 0.0
        return httpx.Response(200, json=ollama_chat_payload("ok"))

    msgs = MESSAGES + [QwenMessage("assistant", "Earlier answer"), QwenMessage("user", "Follow-up")]
    assert run(make_client(handler).chat(msgs, temperature=0.0)).content == "ok"


def test_thinking_is_stripped_from_content():
    def handler(request):
        return httpx.Response(200, json=ollama_chat_payload("<think>internal reasoning</think>\n\nFinal answer."))

    assert run(make_client(handler).chat(MESSAGES)).content == "Final answer."


@pytest.mark.parametrize("raw,expected", [
    ("<think>a</think>b", "b"),
    ("<THINK>\nmulti\nline\n</THINK> answer", "answer"),
    ("<think>never closed", ""),
    ("no thinking here", "no thinking here"),
])
def test_strip_thinking(raw, expected):
    assert strip_thinking(raw) == expected


def test_length_done_reason_marks_truncated():
    handler = lambda r: httpx.Response(200, json=ollama_chat_payload("partial", done_reason="length"))
    assert run(make_client(handler).chat(MESSAGES)).truncated is True


def test_tool_calls_are_parsed():
    payload = ollama_chat_payload("")
    payload["message"]["tool_calls"] = [{"function": {"name": "get_skill_gaps", "arguments": {"role": "x"}}}]
    result = run(make_client(lambda r: httpx.Response(200, json=payload)).chat(MESSAGES, tools=[{"type": "function"}]))
    assert result.tool_calls[0].name == "get_skill_gaps"
    assert result.tool_calls[0].arguments == {"role": "x"}


def test_connection_failure_raises_unavailable():
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(QwenUnavailableError) as info:
        run(make_client(handler).chat(MESSAGES))
    assert "refused" not in info.value.public_message  # internal detail not leaked
    assert "refused" in info.value.detail


def test_connect_timeout_raises_unavailable():
    def handler(request):
        raise httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(QwenUnavailableError):
        run(make_client(handler).chat(MESSAGES))


def test_read_timeout_raises_timeout():
    def handler(request):
        raise httpx.ReadTimeout("read timed out", request=request)

    with pytest.raises(QwenTimeoutError):
        run(make_client(handler).chat(MESSAGES))


def test_model_not_pulled_raises_model_not_found():
    handler = lambda r: httpx.Response(404, json={"error": "model 'qwen3:8b' not found"})
    with pytest.raises(QwenModelNotFoundError):
        run(make_client(handler).chat(MESSAGES))


def test_runtime_server_error_raises_unavailable():
    handler = lambda r: httpx.Response(500, json={"error": "model requires more system memory"})
    with pytest.raises(QwenUnavailableError):
        run(make_client(handler).chat(MESSAGES))


def test_bad_request_raises_response_error():
    handler = lambda r: httpx.Response(400, json={"error": "invalid options"})
    with pytest.raises(QwenResponseError):
        run(make_client(handler).chat(MESSAGES))


@pytest.mark.parametrize("response", [
    httpx.Response(200, text="not json"),
    httpx.Response(200, json=["a", "list"]),
    httpx.Response(200, json={"model": "qwen3:8b", "done": True}),
    httpx.Response(200, json={"message": {"role": "assistant", "content": 42}}),
    httpx.Response(200, json={"message": {"role": "assistant", "content": "   "}}),
    httpx.Response(200, json={"message": {"role": "assistant", "content": "<think>only thoughts</think>"}}),
    httpx.Response(200, json={"error": "something broke"}),
])
def test_malformed_responses_raise_response_error(response):
    with pytest.raises(QwenResponseError):
        run(make_client(lambda r: response).chat(MESSAGES))


def test_empty_messages_rejected():
    with pytest.raises(ValueError):
        run(make_client(lambda r: httpx.Response(200)).chat([]))


def test_health_model_available():
    def handler(request):
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "qwen3:8b", "model": "qwen3:8b"}]})

    status = run(make_client(handler).check_health())
    assert status.runtime_reachable and status.model_available


def test_health_untagged_model_matches_latest():
    handler = lambda r: httpx.Response(200, json={"models": [{"name": "qwen3:latest"}]})
    assert run(make_client(handler, QWEN_MODEL="qwen3").check_health()).model_available


def test_health_model_missing():
    handler = lambda r: httpx.Response(200, json={"models": [{"name": "llama3:8b"}]})
    status = run(make_client(handler).check_health())
    assert status.runtime_reachable and not status.model_available


def test_health_runtime_down_does_not_raise():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    status = run(make_client(handler).check_health())
    assert not status.runtime_reachable and not status.model_available