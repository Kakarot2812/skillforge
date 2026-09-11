"""
Low-level async client for a local Qwen model served by Ollama.

Responsibilities: send chat messages to ``POST {QWEN_BASE_URL}/api/chat``,
check runtime/model availability via ``GET {QWEN_BASE_URL}/api/tags``, and turn
transport or payload problems into clean ``QwenError`` subclasses.

This module deliberately contains no SkillForge business logic (no prompts,
no skill-gap or roadmap handling) so it can be reused by any backend feature.
Ollama API reference: https://github.com/ollama/ollama/blob/main/docs/api.md
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence

import httpx

from app.qwen_ai.config import QwenSettings
from app.qwen_ai.exceptions import (
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
    QwenUnavailableError,
)

logger = logging.getLogger(__name__)

QwenRole = Literal["system", "user", "assistant", "tool"]

# Qwen 3 may emit reasoning inside <think>...</think> when the runtime does not
# separate it (older Ollama versions). It must never reach API users.
_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_UNCLOSED_THINK = re.compile(r"^\s*<think>.*", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class QwenMessage:
    role: QwenRole
    content: str

    def to_payload(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class QwenToolCall:
    name: str
    arguments: Dict[str, Any]


@dataclass(frozen=True)
class QwenChatResult:
    content: str
    model: str
    done_reason: Optional[str] = None
    tool_calls: List[QwenToolCall] = field(default_factory=list)
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None

    @property
    def truncated(self) -> bool:
        """True when generation stopped because it hit the token limit."""
        return self.done_reason == "length"


@dataclass(frozen=True)
class QwenRuntimeStatus:
    runtime_reachable: bool
    model_available: bool
    model: str


def strip_thinking(text: str) -> str:
    """Remove Qwen <think> blocks (closed or unclosed) from model output."""
    cleaned = _THINK_BLOCK.sub("", text)
    cleaned = _UNCLOSED_THINK.sub("", cleaned)
    return cleaned.strip()


def _normalise_tag(name: str) -> str:
    """Ollama treats an untagged model name as ':latest'."""
    return name if ":" in name else f"{name}:latest"


class QwenClient:
    """Async HTTP client for the local Ollama runtime."""

    def __init__(self, settings: QwenSettings, transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self._settings = settings
        # ``transport`` is injectable so tests can use httpx.MockTransport.
        self._transport = transport

    @property
    def model(self) -> str:
        return self._settings.QWEN_MODEL

    def _http(self, total_timeout: float) -> httpx.AsyncClient:
        timeout = httpx.Timeout(total_timeout, connect=self._settings.QWEN_CONNECT_TIMEOUT)
        return httpx.AsyncClient(
            base_url=self._settings.QWEN_BASE_URL,
            timeout=timeout,
            transport=self._transport,
        )

    async def chat(
        self,
        messages: Sequence[QwenMessage],
        *,
        temperature: Optional[float] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> QwenChatResult:
        """Send a non-streaming chat request and return the parsed assistant reply."""
        if not messages:
            raise ValueError("At least one message is required.")

        payload: Dict[str, Any] = {
            "model": self._settings.QWEN_MODEL,
            "messages": [m.to_payload() for m in messages],
            "stream": False,
            "think": self._settings.QWEN_THINK,
            "keep_alive": self._settings.QWEN_KEEP_ALIVE,
            "options": {
                "temperature": self._settings.QWEN_TEMPERATURE if temperature is None else temperature,
                "num_ctx": self._settings.QWEN_NUM_CTX,
            },
        }
        if tools:
            payload["tools"] = tools

        data = await self._request_json("POST", "/api/chat", json=payload, timeout=self._settings.QWEN_TIMEOUT)
        return self._parse_chat(data)

    async def check_health(self) -> QwenRuntimeStatus:
        """Check that Ollama is reachable and the configured model is pulled.

        Uses /api/tags, which lists local models without loading one into memory.
        Never raises for "unavailable"; returns a status object instead.
        """
        model = self._settings.QWEN_MODEL
        try:
            data = await self._request_json("GET", "/api/tags", timeout=self._settings.QWEN_CONNECT_TIMEOUT * 2)
        except (QwenUnavailableError, QwenTimeoutError, QwenResponseError) as exc:
            logger.info("Qwen health check failed: %s", exc.detail or exc.public_message)
            return QwenRuntimeStatus(runtime_reachable=False, model_available=False, model=model)

        wanted = _normalise_tag(model)
        installed = set()
        for entry in data.get("models") or []:
            if isinstance(entry, dict):
                for key in ("name", "model"):
                    if isinstance(entry.get(key), str):
                        installed.add(_normalise_tag(entry[key]))
        return QwenRuntimeStatus(runtime_reachable=True, model_available=wanted in installed, model=model)

    async def _request_json(self, method: str, path: str, *, timeout: float, json: Any = None) -> Dict[str, Any]:
        try:
            async with self._http(timeout) as http:
                response = await http.request(method, path, json=json)
        except httpx.ConnectTimeout as exc:
            raise QwenUnavailableError(detail=f"Connect timeout to Ollama: {exc!r}") from exc
        except httpx.TimeoutException as exc:
            raise QwenTimeoutError(detail=f"Ollama request timed out: {exc!r}") from exc
        except httpx.TransportError as exc:
            raise QwenUnavailableError(detail=f"Cannot reach Ollama: {exc!r}") from exc

        if response.status_code >= 400:
            self._raise_for_status(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise QwenResponseError(detail="Ollama returned non-JSON body") from exc
        if not isinstance(data, dict):
            raise QwenResponseError(detail=f"Ollama returned JSON of type {type(data).__name__}")
        return data

    def _raise_for_status(self, response: httpx.Response) -> None:
        error_text = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                error_text = str(body.get("error", ""))
        except ValueError:
            error_text = response.text[:200]
        detail = f"Ollama HTTP {response.status_code}: {error_text}"

        if response.status_code == 404 and "not found" in error_text.lower():
            raise QwenModelNotFoundError(detail=detail)
        if response.status_code >= 500:
            # e.g. the model failed to load (insufficient memory) or runner crashed.
            raise QwenUnavailableError(detail=detail)
        raise QwenResponseError(detail=detail)

    def _parse_chat(self, data: Dict[str, Any]) -> QwenChatResult:
        if data.get("error"):
            raise QwenResponseError(detail=f"Ollama error payload: {data.get('error')}")

        message = data.get("message")
        if not isinstance(message, dict):
            raise QwenResponseError(detail="Ollama response is missing 'message'")

        raw_content = message.get("content", "")
        if not isinstance(raw_content, str):
            raise QwenResponseError(detail="Ollama 'message.content' is not a string")

        tool_calls = self._parse_tool_calls(message.get("tool_calls"))
        content = strip_thinking(raw_content)
        if not content and not tool_calls:
            raise QwenResponseError(detail="Ollama returned an empty assistant message")

        return QwenChatResult(
            content=content,
            model=str(data.get("model") or self._settings.QWEN_MODEL),
            done_reason=data.get("done_reason") if isinstance(data.get("done_reason"), str) else None,
            tool_calls=tool_calls,
            prompt_tokens=data.get("prompt_eval_count") if isinstance(data.get("prompt_eval_count"), int) else None,
            completion_tokens=data.get("eval_count") if isinstance(data.get("eval_count"), int) else None,
        )

    @staticmethod
    def _parse_tool_calls(raw: Any) -> List[QwenToolCall]:
        calls: List[QwenToolCall] = []
        if not isinstance(raw, list):
            return calls
        for item in raw:
            function = item.get("function") if isinstance(item, dict) else None
            if isinstance(function, dict) and isinstance(function.get("name"), str):
                args = function.get("arguments")
                calls.append(QwenToolCall(name=function["name"], arguments=args if isinstance(args, dict) else {}))
        return calls