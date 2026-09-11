"""
SkillForge AI (local Qwen via Ollama) endpoints.

    POST /api/v1/qwen/chat    -> grounded chat answer
    GET  /api/v1/qwen/health  -> local runtime/model readiness

Errors use the same envelope as app/main.py ({"detail", "error": {code, message,
details}}) with AI-specific codes. Internal details are logged, never returned.
"""
import logging
from functools import lru_cache
from typing import Dict, Tuple, Type, Union

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.qwen_ai.config import get_qwen_settings
from app.qwen_ai.exceptions import (
    QwenConfigurationError,
    QwenError,
    QwenModelNotFoundError,
    QwenResponseError,
    QwenTimeoutError,
    QwenUnavailableError,
)
from app.qwen_ai.qwen_client import QwenClient
from app.qwen_ai.qwen_service import QwenService
from app.qwen_ai.schemas import ChatRequest, ChatResponse, QwenHealthData, QwenHealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["SkillForge AI (Qwen)"])

# Most specific classes first (QwenModelNotFoundError subclasses QwenUnavailableError).
ERROR_MAP: Tuple[Tuple[Type[QwenError], int, str], ...] = (
    (QwenModelNotFoundError, status.HTTP_503_SERVICE_UNAVAILABLE, "AI_MODEL_NOT_INSTALLED"),
    (QwenUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE, "AI_SERVICE_UNAVAILABLE"),
    (QwenTimeoutError, status.HTTP_504_GATEWAY_TIMEOUT, "AI_TIMEOUT"),
    (QwenResponseError, status.HTTP_502_BAD_GATEWAY, "AI_INVALID_RESPONSE"),
    (QwenConfigurationError, status.HTTP_500_INTERNAL_SERVER_ERROR, "AI_CONFIGURATION_ERROR"),
)

_ERROR_DOC = {"description": "Standard error envelope with an AI_* error code."}


def _error_response(status_code: int, code: str, message: str, details: Union[Dict, None] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": message, "error": {"code": code, "message": message, "details": details or {}}},
    )


def qwen_error_response(exc: QwenError) -> JSONResponse:
    for exc_type, status_code, code in ERROR_MAP:
        if isinstance(exc, exc_type):
            break
    else:
        status_code, code = status.HTTP_500_INTERNAL_SERVER_ERROR, "AI_ERROR"
    logger.warning("Qwen error %s: %s", code, exc.detail or exc.public_message)
    return _error_response(status_code, code, exc.public_message)


@lru_cache
def _build_service() -> QwenService:
    settings = get_qwen_settings()
    return QwenService(QwenClient(settings), settings)


def get_qwen_service() -> QwenService:
    """FastAPI dependency. Override in tests via app.dependency_overrides."""
    try:
        return _build_service()
    except QwenConfigurationError as exc:
        logger.error("Qwen configuration error: %s", exc.detail)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.public_message)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask SkillForge AI (local Qwen)",
    responses={502: _ERROR_DOC, 503: _ERROR_DOC, 504: _ERROR_DOC},
)
async def chat(request: ChatRequest, service: QwenService = Depends(get_qwen_service)):
    """Answer a career/skill question, grounded in optional SkillForge context.

    Availability is checked implicitly: if Ollama is down the call fails fast
    (QWEN_CONNECT_TIMEOUT) and returns 503 rather than pre-checking every request.
    """
    try:
        return await service.chat(request)
    except QwenError as exc:
        return qwen_error_response(exc)


@router.get(
    "/health",
    response_model=QwenHealthResponse,
    summary="Local Qwen runtime health",
    responses={503: _ERROR_DOC},
)
async def qwen_health(service: QwenService = Depends(get_qwen_service)):
    """Report whether the local Ollama runtime is reachable and the model is installed."""
    runtime = await service.health()
    if runtime.runtime_reachable and runtime.model_available:
        return QwenHealthResponse(data=QwenHealthData(
            status="ok", model=runtime.model, runtime_reachable=True, model_available=True,
        ))

    health = QwenHealthData(
        status="model_missing" if runtime.runtime_reachable else "unavailable",
        model=runtime.model,
        runtime_reachable=runtime.runtime_reachable,
        model_available=runtime.model_available,
    )
    exc: QwenError = QwenModelNotFoundError() if runtime.runtime_reachable else QwenUnavailableError()
    code = "AI_MODEL_NOT_INSTALLED" if runtime.runtime_reachable else "AI_SERVICE_UNAVAILABLE"
    return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, code, exc.public_message, health.model_dump())