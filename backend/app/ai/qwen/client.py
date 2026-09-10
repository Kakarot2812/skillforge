"""
Local Qwen 3 8B / Ollama HTTP client for SkillForge AI.
Post-MVP Phase 2, Checkpoint P2-A.

Provides an isolated, generic HTTP client for communicating with a local Ollama instance.
Core architectural principles:
- "The LLM never decides what is true."
- Pure infrastructure client: zero SkillForge domain logic, zero skills/gaps/priorities.
- Bounded timeouts, robust connection failure handling, typed exceptions.
- Local-first: communicates with local Ollama daemon (default http://localhost:11434).
- Never requires or handles external API keys or credentials.
- Zero database writes: purely stateless communication.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
import httpx

from app.config import settings
from app.ai.qwen.exceptions import (
    QwenAPIError,
    QwenConfigurationError,
    QwenConnectionError,
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

logger = logging.getLogger(__name__)


class QwenClient:
    """
    Isolated HTTP client for the local Ollama daemon running Qwen 3 8B.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        raw_url = base_url if base_url is not None else settings.OLLAMA_BASE_URL
        if not raw_url or not isinstance(raw_url, str) or not raw_url.strip():
            raise QwenConfigurationError("Ollama base URL must be a non-empty string.")

        self.base_url: str = raw_url.strip().rstrip("/")

        raw_model = model if model is not None else settings.OLLAMA_MODEL
        if not raw_model or not isinstance(raw_model, str) or not raw_model.strip():
            raise QwenConfigurationError("Ollama model name must be a non-empty string.")

        self.model: str = raw_model.strip()

        raw_timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.OLLAMA_TIMEOUT_SECONDS
        )
        if raw_timeout <= 0:
            raise QwenConfigurationError("Ollama timeout must be a positive number of seconds.")

        self.timeout_seconds: float = float(raw_timeout)

        self._owns_client: bool = http_client is None
        self._client: httpx.Client = http_client or httpx.Client(
            timeout=self.timeout_seconds
        )

    def __enter__(self) -> "QwenClient":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Closes the underlying HTTP client if owned by this instance."""
        if self._owns_client and hasattr(self._client, "close"):
            self._client.close()

    def chat(
        self,
        messages: List[Union[QwenMessage, Dict[str, str]]],
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> QwenChatResponse:
        """
        Executes a chat completion request against Ollama's /api/chat endpoint.

        Args:
            messages: Sequence of message objects or dicts (role, content).
            system: Optional system instruction prepended to messages.
            options: Optional runtime parameters (temperature, num_predict, etc.).

        Returns:
            QwenChatResponse containing the generated response and execution metrics.
        """
        if not messages:
            raise ValueError("At least one message must be provided for chat.")

        formatted_messages: List[Dict[str, str]] = []
        if system and system.strip():
            formatted_messages.append({"role": "system", "content": system.strip()})

        for msg in messages:
            if isinstance(msg, QwenMessage):
                formatted_messages.append(msg.to_dict())
            elif isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                formatted_messages.append({"role": str(role), "content": str(content)})
            else:
                raise ValueError(f"Unsupported message type: {type(msg)}")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "stream": False,
        }
        if options:
            payload["options"] = dict(options)

        url = f"{self.base_url}/api/chat"
        logger.debug("Sending chat request to Ollama endpoint: %s with model %s", url, self.model)

        resp_data = self._send_request(method="POST", url=url, json_payload=payload)

        # Validate response schema
        message_dict = resp_data.get("message")
        if not isinstance(message_dict, dict) or "content" not in message_dict:
            raise QwenResponseError(
                "Malformed response from Ollama: missing expected 'message.content' field.",
                response_body=json.dumps(resp_data),
            )

        resp_model = resp_data.get("model", self.model)
        role = message_dict.get("role", "assistant")
        content = message_dict.get("content", "")

        return QwenChatResponse(
            model=resp_model,
            message=QwenMessage(role=role, content=content),
            done=bool(resp_data.get("done", True)),
            done_reason=resp_data.get("done_reason"),
            total_duration=resp_data.get("total_duration"),
            load_duration=resp_data.get("load_duration"),
            prompt_eval_count=resp_data.get("prompt_eval_count"),
            eval_count=resp_data.get("eval_count"),
        )

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> QwenGenerateResponse:
        """
        Executes a raw text generation request against Ollama's /api/generate endpoint.

        Args:
            prompt: Text prompt to provide to the model.
            system: Optional system instruction.
            options: Optional runtime parameters.

        Returns:
            QwenGenerateResponse containing generated text and execution metrics.
        """
        if not prompt or not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt must be a non-empty string.")

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt.strip(),
            "stream": False,
        }
        if system and system.strip():
            payload["system"] = system.strip()
        if options:
            payload["options"] = dict(options)

        url = f"{self.base_url}/api/generate"
        logger.debug("Sending generate request to Ollama endpoint: %s with model %s", url, self.model)

        resp_data = self._send_request(method="POST", url=url, json_payload=payload)

        if "response" not in resp_data:
            raise QwenResponseError(
                "Malformed response from Ollama: missing expected 'response' field.",
                response_body=json.dumps(resp_data),
            )

        return QwenGenerateResponse(
            model=resp_data.get("model", self.model),
            response=str(resp_data.get("response", "")),
            done=bool(resp_data.get("done", True)),
            done_reason=resp_data.get("done_reason"),
            total_duration=resp_data.get("total_duration"),
            prompt_eval_count=resp_data.get("prompt_eval_count"),
            eval_count=resp_data.get("eval_count"),
        )

    def get_available_models(self) -> List[str]:
        """
        Fetches list of installed model tags from the local Ollama daemon.

        Returns:
            List of model names (e.g. ['qwen3:8b', ...]).
        """
        url = f"{self.base_url}/api/tags"
        resp_data = self._send_request(method="GET", url=url)

        models_list = resp_data.get("models")
        if not isinstance(models_list, list):
            raise QwenResponseError(
                "Malformed response from Ollama /api/tags: missing 'models' list.",
                response_body=json.dumps(resp_data),
            )

        names: List[str] = []
        for m in models_list:
            if isinstance(m, dict) and "name" in m:
                names.append(str(m["name"]))
        return names

    def check_health(self, raise_on_error: bool = False) -> QwenHealthStatus:
        """
        Verifies that Ollama is reachable and the configured model is installed.

        Args:
            raise_on_error: If True, raises QwenConnectionError, QwenTimeoutError,
                            or QwenModelNotFoundError on failure.

        Returns:
            QwenHealthStatus representing connectivity and model availability.
        """
        try:
            available_models = self.get_available_models()
        except QwenTimeoutError as te:
            if raise_on_error:
                raise
            return QwenHealthStatus(
                reachable=False,
                model_available=False,
                configured_model=self.model,
                available_models=[],
                details={"error": "timeout", "message": str(te)},
            )
        except (QwenConnectionError, QwenAPIError, QwenResponseError) as ce:
            if raise_on_error:
                raise
            return QwenHealthStatus(
                reachable=False,
                model_available=False,
                configured_model=self.model,
                available_models=[],
                details={"error": type(ce).__name__, "message": str(ce)},
            )
        except Exception as e:
            if raise_on_error:
                raise QwenConnectionError(f"Unexpected error connecting to Ollama: {e}") from e
            return QwenHealthStatus(
                reachable=False,
                model_available=False,
                configured_model=self.model,
                available_models=[],
                details={"error": "unexpected", "message": str(e)},
            )

        # Check if configured model is in available models
        # Normalizes tags: e.g. "qwen3:8b" matches "qwen3:8b" or "qwen3:8b:latest"
        model_available = False
        target_norm = self.model.lower().strip()
        for m in available_models:
            m_norm = m.lower().strip()
            if m_norm == target_norm or m_norm == f"{target_norm}:latest" or target_norm == f"{m_norm}:latest":
                model_available = True
                break

        if not model_available and raise_on_error:
            raise QwenModelNotFoundError(
                f"Configured model '{self.model}' is not installed in local Ollama. Available: {available_models}",
                model_name=self.model,
            )

        return QwenHealthStatus(
            reachable=True,
            model_available=model_available,
            configured_model=self.model,
            available_models=available_models,
            details={"models_count": len(available_models)},
        )

    def _send_request(
        self,
        method: str,
        url: str,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Internal request dispatcher handling transport, timeouts, and HTTP error translation.
        """
        try:
            resp = self._client.request(
                method=method,
                url=url,
                json=json_payload,
            )
        except httpx.TimeoutException as te:
            logger.error("Timeout connecting to Ollama at %s after %ss", url, self.timeout_seconds)
            raise QwenTimeoutError(
                f"Ollama request to '{url}' timed out after {self.timeout_seconds} seconds."
            ) from te
        except (httpx.ConnectError, httpx.NetworkError) as ce:
            logger.error("Connection error reaching Ollama at %s: %s", url, ce)
            raise QwenConnectionError(
                f"Failed to connect to local Ollama service at '{url}'. Ensure Ollama daemon is running."
            ) from ce
        except Exception as exc:
            logger.error("Transport error communicating with Ollama at %s: %s", url, exc)
            raise QwenConnectionError(f"Transport error communicating with Ollama: {exc}") from exc

        # Handle non-2xx status codes
        if resp.status_code >= 400:
            body_text = resp.text
            if resp.status_code == 404:
                # Check if model not found error
                if "not found" in body_text.lower():
                    raise QwenModelNotFoundError(
                        f"Model '{self.model}' not found in local Ollama instance.",
                        model_name=self.model,
                        status_code=resp.status_code,
                        response_body=body_text,
                    )
            raise QwenAPIError(
                f"Ollama API returned HTTP status {resp.status_code}.",
                status_code=resp.status_code,
                response_body=body_text,
            )

        # Parse JSON
        try:
            data = resp.json()
        except Exception as je:
            raise QwenResponseError(
                "Failed to decode Ollama response as valid JSON.",
                response_body=resp.text,
            ) from je

        if not isinstance(data, dict):
            raise QwenResponseError(
                "Ollama response root must be a JSON object.",
                response_body=resp.text,
            )

        return data
