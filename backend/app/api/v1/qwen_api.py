"""
SkillForge AI (local Qwen via Ollama) endpoints.

    POST /api/v1/qwen/chat    -> grounded chat answer
    GET  /api/v1/qwen/health  -> local runtime/model readiness

Errors use the same envelope as app/main.py ({"detail", "error": {code, message,
details}}) with AI-specific codes. Internal details are logged, never returned.
"""
import logging
from functools import lru_cache
from typing import Dict, Optional, Tuple, Type, Union
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.qwen_ai.config import get_qwen_settings
from app.qwen_ai.context import MAX_EVIDENCE_ITEMS, SkillForgeContext
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
from app.rag.service import RagService, get_rag_service

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


def _resolve_user_id(x_user_id: Optional[str]) -> Optional[UUID]:
    """Same convention as app/api/v1/gaps.py's resolve_user_id: an optional
    X-User-Id header, no auth system behind it yet (MVP-stage, matches the
    rest of the project). Used only to scope which private RAG evidence
    (resumes/GitHub artifacts) this caller may see — never trusted for
    anything else.
    """
    if not x_user_id:
        return None
    try:
        return UUID(x_user_id.strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID format in X-User-Id header.",
        )


def _merge_rag_evidence(context: Optional[SkillForgeContext], rag_evidence: list) -> Optional[SkillForgeContext]:
    """Append retrieved evidence to any caller-supplied context, respecting
    SkillForgeContext's evidence cap. Caller-supplied evidence (already
    curated by another SkillForge module) takes priority; RAG only fills
    remaining slots. Never raises — worst case, RAG evidence is dropped.
    """
    if not rag_evidence:
        return context
    if context is None:
        return SkillForgeContext(evidence=rag_evidence[:MAX_EVIDENCE_ITEMS])

    existing = list(context.evidence)[:MAX_EVIDENCE_ITEMS]
    remaining_slots = MAX_EVIDENCE_ITEMS - len(existing)
    if remaining_slots > 0:
        context.evidence = existing + rag_evidence[:remaining_slots]
    return context


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask SkillForge AI (local Qwen)",
    responses={502: _ERROR_DOC, 503: _ERROR_DOC, 504: _ERROR_DOC},
)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    service: QwenService = Depends(get_qwen_service),
    rag_service: RagService = Depends(get_rag_service),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Answer a career/skill question, grounded in optional SkillForge context.

    Availability is checked implicitly: if Ollama is down the call fails fast
    (QWEN_CONNECT_TIMEOUT) and returns 503 rather than pre-checking every request.

    Before calling Qwen, retrieves supporting evidence via RAG and merges it
    into ``request.context.evidence`` — the frontend never calls RAG itself.
    RAG failures (Ollama down, embedding model missing, etc.) never fail this
    endpoint: retrieval degrades to an empty evidence list and chat proceeds
    ungrounded, exactly as it did before RAG existed.
    """
    user_id = _resolve_user_id(x_user_id)
    rag_evidence = await rag_service.retrieve_evidence(db, request.message, user_id=user_id)
    request.context = _merge_rag_evidence(request.context, rag_evidence)

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