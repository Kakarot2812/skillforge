"""
Google Gemini 2.5 Flash LangChain client for SkillForge AI.
Post-MVP Career Roadmap PDF Foundation (Phase 1).

Provides an isolated, generic client wrapping LangChain's ChatGoogleGenerativeAI.
Core architectural principles:
- "The LLM never decides what is true."
- Pure infrastructure client: zero roadmap/PDF domain logic, zero skills/gaps/priorities coupling.
- Bounded timeouts, robust connection failure handling, typed domain exceptions.
- Zero secret exposure: API keys are never printed, logged, or serialized.
- Strict compatibility with LangChain BaseChatModel abstractions.
"""

import logging
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.config import settings
from app.ai.gemini.exceptions import (
    GeminiAPIError,
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiConnectionError,
    GeminiError,
    GeminiResponseError,
    GeminiTimeoutError,
    sanitize_gemini_message,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    """
    Isolated LangChain client for Google Gemini 2.5 Flash.
    Provides safe invocation, structured output wrapping, and typed error handling.
    """

    DEFAULT_MODEL: str = "gemini-2.5-flash"
    DEFAULT_TEMPERATURE: float = 0.2
    DEFAULT_TIMEOUT_SECONDS: float = 30.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: int = 2,
        chat_model: Optional[ChatGoogleGenerativeAI] = None,
    ):
        # Resolve and validate API key
        resolved_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        if not resolved_key or not isinstance(resolved_key, str) or not resolved_key.strip():
            raise GeminiConfigurationError(
                "GEMINI_API_KEY must be configured in environment or settings to initialize GeminiClient."
            )
        self._api_key: str = resolved_key.strip()

        # Resolve and validate model
        resolved_model = model if model is not None else (settings.GEMINI_MODEL or self.DEFAULT_MODEL)
        if not resolved_model or not isinstance(resolved_model, str) or not resolved_model.strip():
            raise GeminiConfigurationError("Gemini model name must be a non-empty string.")
        self.model: str = resolved_model.strip()

        # Resolve and validate temperature
        resolved_temp = temperature if temperature is not None else self.DEFAULT_TEMPERATURE
        if resolved_temp < 0.0 or resolved_temp > 2.0:
            raise GeminiConfigurationError(
                f"Gemini temperature must be between 0.0 and 2.0, received: {resolved_temp}"
            )
        self.temperature: float = float(resolved_temp)

        # Resolve and validate timeout
        resolved_timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else (settings.GEMINI_TIMEOUT_SECONDS or self.DEFAULT_TIMEOUT_SECONDS)
        )
        if resolved_timeout <= 0:
            raise GeminiConfigurationError(
                f"Gemini timeout must be a positive number of seconds, received: {resolved_timeout}"
            )
        self.timeout_seconds: float = float(resolved_timeout)
        self.max_retries: int = max(0, int(max_retries))

        # Initialize or inject underlying ChatGoogleGenerativeAI
        self._chat_model: ChatGoogleGenerativeAI = chat_model or ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=self._api_key,
            temperature=self.temperature,
            timeout=self.timeout_seconds,
            max_retries=self.max_retries,
        )

    def __repr__(self) -> str:
        """Safe representation suppressing credentials."""
        return (
            f"<GeminiClient model={self.model!r} "
            f"temperature={self.temperature} "
            f"timeout_seconds={self.timeout_seconds}>"
        )

    def get_chat_model(self) -> ChatGoogleGenerativeAI:
        """Returns the underlying LangChain chat model for composition into chains."""
        return self._chat_model

    def _map_exception(self, exc: Exception) -> GeminiError:
        """Translates raw provider exceptions into SkillForge typed exceptions."""
        if isinstance(exc, GeminiError):
            return exc

        raw_msg = sanitize_gemini_message(str(exc), self._api_key)
        lower_msg = raw_msg.lower()

        # Authentication / Permission errors
        if any(
            k in lower_msg
            for k in [
                "api key not valid",
                "invalid api key",
                "unauthorized",
                "permission_denied",
                "permission denied",
                "forbidden",
                "401",
                "403",
                "invalid_argument",
            ]
        ) and "timeout" not in lower_msg:
            return GeminiAuthenticationError(
                f"Gemini authentication failed: {raw_msg}",
                api_key=self._api_key,
            )

        # Timeout errors
        if any(
            k in lower_msg
            for k in ["timeout", "timed out", "deadline_exceeded", "504"]
        ):
            return GeminiTimeoutError(
                f"Gemini communication timed out: {raw_msg}",
                api_key=self._api_key,
            )

        # Connection / Network errors
        if any(
            k in lower_msg
            for k in [
                "connection error",
                "connection refused",
                "connecterror",
                "failed to establish a new connection",
                "name resolution",
                "network unreachable",
            ]
        ):
            return GeminiConnectionError(
                f"Gemini connection failed: {raw_msg}",
                api_key=self._api_key,
            )

        # Response / Parsing errors
        if any(
            k in lower_msg
            for k in [
                "validation error",
                "invalid json",
                "failed to parse",
                "schema validation",
            ]
        ):
            return GeminiResponseError(
                f"Gemini response parsing error: {raw_msg}",
                api_key=self._api_key,
            )

        # General API error with optional status code
        status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        return GeminiAPIError(
            f"Gemini API invocation failure: {raw_msg}",
            status_code=status_code,
            api_key=self._api_key,
        )

    def invoke(
        self,
        messages: Union[str, List[BaseMessage], List[Dict[str, str]]],
        **kwargs: Any,
    ) -> BaseMessage:
        """
        Executes a standard LangChain chat completion invocation with typed error handling.
        """
        try:
            return self._chat_model.invoke(messages, **kwargs)
        except Exception as exc:
            mapped = self._map_exception(exc)
            logger.error("GeminiClient invocation error: %s", mapped.message)
            raise mapped from None

    def with_structured_output(
        self,
        schema: Union[Type[T], Dict[str, Any]],
        **kwargs: Any,
    ) -> Runnable:
        """
        Returns a LangChain Runnable configured to return structured output matching the schema.
        Foundation for Phase 3 RoadmapPDFPersonalizedNarrative generation.
        """
        try:
            underlying_runnable = self._chat_model.with_structured_output(schema, **kwargs)
        except Exception as exc:
            mapped = self._map_exception(exc)
            logger.error("GeminiClient with_structured_output configuration error: %s", mapped.message)
            raise mapped from None

        # Return a wrapped runnable that catches invocation exceptions
        client_ref = self

        class SafeStructuredRunnable(Runnable):
            def invoke(self, input: Any, config: Optional[Dict[str, Any]] = None, **run_kwargs: Any) -> Any:
                try:
                    return underlying_runnable.invoke(input, config=config, **run_kwargs)
                except Exception as exc:
                    mapped = client_ref._map_exception(exc)
                    logger.error("GeminiClient structured invocation error: %s", mapped.message)
                    raise mapped from None

        return SafeStructuredRunnable()
