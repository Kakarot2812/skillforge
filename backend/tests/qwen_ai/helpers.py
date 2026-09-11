"""Shared helpers for Qwen AI tests (mock Ollama responses, isolated settings)."""
import json
from typing import Callable

import httpx

from app.qwen_ai.config import QwenSettings
from app.qwen_ai.qwen_client import QwenClient


def make_settings(**overrides) -> QwenSettings:
    """Settings isolated from any developer .env file."""
    values = {"QWEN_BASE_URL": "http://ollama.test:11434", "QWEN_MODEL": "qwen3:8b"}
    values.update(overrides)
    return QwenSettings(_env_file=None, **values)


def ollama_chat_payload(content: str, **extra) -> dict:
    body = {
        "model": "qwen3:8b",
        "created_at": "2026-09-11T10:00:00Z",
        "message": {"role": "assistant", "content": content},
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 120,
        "eval_count": 40,
    }
    body.update(extra)
    return body


def make_client(handler: Callable[[httpx.Request], httpx.Response], **overrides) -> QwenClient:
    return QwenClient(make_settings(**overrides), transport=httpx.MockTransport(handler))


def request_json(request: httpx.Request) -> dict:
    return json.loads(request.content.decode())