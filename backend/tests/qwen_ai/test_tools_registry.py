"""
Optional end-to-end tests against a real local Ollama + Qwen.

Skipped unless QWEN_INTEGRATION=1. Run with:
    QWEN_INTEGRATION=1 pytest tests/qwen_ai -m qwen_integration
"""
import asyncio
import os

import pytest

from app.qwen_ai.config import QwenSettings
from app.qwen_ai.qwen_client import QwenClient
from app.qwen_ai.qwen_service import QwenService
from app.qwen_ai.schemas import ChatRequest

pytestmark = [
    pytest.mark.qwen_integration,
    pytest.mark.skipif(os.getenv("QWEN_INTEGRATION") != "1", reason="set QWEN_INTEGRATION=1 to run"),
]


def _service() -> QwenService:
    settings = QwenSettings()
    return QwenService(QwenClient(settings), settings)


def test_live_health():
    status = asyncio.run(_service().health())
    assert status.runtime_reachable, "Ollama is not reachable at QWEN_BASE_URL"
    assert status.model_available, "Model not pulled: run `ollama pull qwen3:8b`"


def test_live_grounded_chat():
    request = ChatRequest(
        message="What should I learn next? Answer in two sentences.",
        context={"target_role": "Backend Engineer", "current_skills": ["Python", "SQL", "REST"],
                 "missing_skills": ["Docker", "AWS", "Kubernetes"], "priority_skills": ["Docker", "AWS"]},
    )
    response = asyncio.run(_service().chat(request))
    assert response.data.answer
    assert "<think>" not in response.data.answer
    assert "docker" in response.data.answer.lower()