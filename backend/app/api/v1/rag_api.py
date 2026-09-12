"""
RAG evidence-management endpoints.

    POST   /api/v1/rag/ingest              -> ingest one manual document, or
                                               sync one/all rows of a known source
    POST   /api/v1/rag/reindex             -> re-sync every document of a source type
    DELETE /api/v1/rag/documents/{id}      -> remove a document and its chunks
    GET    /api/v1/rag/health              -> local embedding runtime readiness

Internal/admin surface, not a public-facing feature: SkillForge has no
authentication layer yet (see app/api/v1/gaps.py's own comment on this),
so — consistent with the rest of the MVP — these routes rely on network-level
trust (e.g. not exposed past a reverse proxy) rather than inventing an auth
mechanism here. The chat-facing flow never calls these directly; Qwen's
``/qwen/chat`` endpoint uses ``RagService.retrieve_evidence`` internally so
the frontend never needs to call RAG itself (see app/api/v1/qwen_api.py).

Errors use the same envelope as app/main.py, mirroring app/api/v1/qwen_api.py.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.rag.exceptions import (
    RagConfigurationError,
    RagDisabledError,
    RagDocumentError,
    RagEmbeddingDimensionError,
    RagEmbeddingModelNotFoundError,
    RagEmbeddingResponseError,
    RagEmbeddingTimeoutError,
    RagEmbeddingUnavailableError,
    RagError,
    RagNotFoundError,
)
from app.rag.service import RagService, get_rag_service
from app.rag.sources import SOURCE_ADAPTERS
from app.rag.sources.manual import ManualSourceAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["RAG (Evidence Retrieval)"])

# Most specific classes first (RagEmbeddingModelNotFoundError subclasses RagEmbeddingUnavailableError).
ERROR_MAP: Tuple[Tuple[Type[RagError], int, str], ...] = (
    (RagNotFoundError, status.HTTP_404_NOT_FOUND, "RAG_NOT_FOUND"),
    (RagDocumentError, status.HTTP_422_UNPROCESSABLE_ENTITY, "RAG_INVALID_DOCUMENT"),
    (RagDisabledError, status.HTTP_503_SERVICE_UNAVAILABLE, "RAG_DISABLED"),
    (RagEmbeddingModelNotFoundError, status.HTTP_503_SERVICE_UNAVAILABLE, "RAG_MODEL_NOT_INSTALLED"),
    (RagEmbeddingUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE, "RAG_SERVICE_UNAVAILABLE"),
    (RagEmbeddingTimeoutError, status.HTTP_504_GATEWAY_TIMEOUT, "RAG_TIMEOUT"),
    (RagEmbeddingDimensionError, status.HTTP_502_BAD_GATEWAY, "RAG_INVALID_RESPONSE"),
    (RagEmbeddingResponseError, status.HTTP_502_BAD_GATEWAY, "RAG_INVALID_RESPONSE"),
    (RagConfigurationError, status.HTTP_500_INTERNAL_SERVER_ERROR, "RAG_CONFIGURATION_ERROR"),
)
_ERROR_DOC = {"description": "Standard error envelope with a RAG_* error code."}


def _error_response(status_code: int, code: str, message: str, details: Optional[Dict] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": message, "error": {"code": code, "message": message, "details": details or {}}},
    )


def rag_error_response(exc: RagError) -> JSONResponse:
    for exc_type, status_code, code in ERROR_MAP:
        if isinstance(exc, exc_type):
            break
    else:
        status_code, code = status.HTTP_500_INTERNAL_SERVER_ERROR, "RAG_ERROR"
    logger.warning("RAG error %s: %s", code, exc.detail or exc.public_message)
    return _error_response(status_code, code, exc.public_message)


class RagIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(description=f"One of: {sorted(SOURCE_ADAPTERS)}")
    source_id: Optional[str] = Field(
        None, description="Scope to one row (known sources) or a stable slug (manual). "
                           "Omit for a known source to sync every row."
    )
    title: Optional[str] = Field(None, max_length=255, description="Required when source_type=manual")
    text: Optional[str] = Field(None, min_length=1, description="Required when source_type=manual")
    user_id: Optional[UUID] = Field(None, description="manual only: owner scope, or omit for global/shared evidence")
    source_url: Optional[str] = Field(None, max_length=512)
    metadata: Optional[Dict[str, Any]] = None


class RagIngestResultItem(BaseModel):
    document_id: UUID
    source_type: str
    source_id: str
    version: int
    chunks_created: int
    chunks_reused: int
    changed: bool


class RagIngestResponse(BaseModel):
    data: List[RagIngestResultItem]


class RagReindexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(description=f"One of: {sorted(k for k in SOURCE_ADAPTERS if k != 'manual')}")


class RagHealthData(BaseModel):
    status: str
    embedding_model_available: bool


class RagHealthResponse(BaseModel):
    data: RagHealthData


def _validate_source_type(source_type: str, *, allow_manual: bool = True) -> None:
    valid = set(SOURCE_ADAPTERS) if allow_manual else set(SOURCE_ADAPTERS) - {"manual"}
    if source_type not in valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown source_type '{source_type}'. Valid values: {sorted(valid)}",
        )


@router.post(
    "/ingest",
    response_model=RagIngestResponse,
    summary="Ingest a manual document, or sync evidence from a known SkillForge source",
    responses={503: _ERROR_DOC},
)
async def ingest(
    request: RagIngestRequest,
    db: Session = Depends(get_db),
    service: RagService = Depends(get_rag_service),
) -> Union[RagIngestResponse, JSONResponse]:
    _validate_source_type(request.source_type)

    try:
        if request.source_type == "manual":
            if not request.title or not request.text:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="'title' and 'text' are required when source_type='manual'.",
                )
            if not request.source_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="'source_id' (a stable slug) is required when source_type='manual'.",
                )
            doc = ManualSourceAdapter.normalize(
                source_id=request.source_id, title=request.title, text=request.text,
                user_id=request.user_id, source_url=request.source_url, metadata=request.metadata,
            )
            result = await service.ingest_document(db, doc)
            results = [result]
        else:
            results = await service.ingest_source(db, request.source_type, source_id=request.source_id)
    except RagError as exc:
        return rag_error_response(exc)

    return RagIngestResponse(data=[RagIngestResultItem(**r.__dict__) for r in results])


@router.post(
    "/reindex",
    response_model=RagIngestResponse,
    summary="Re-sync every document of a known SkillForge source",
    responses={503: _ERROR_DOC},
)
async def reindex(
    request: RagReindexRequest,
    db: Session = Depends(get_db),
    service: RagService = Depends(get_rag_service),
) -> Union[RagIngestResponse, JSONResponse]:
    _validate_source_type(request.source_type, allow_manual=False)
    try:
        results = await service.ingest_source(db, request.source_type, source_id=None)
    except RagError as exc:
        return rag_error_response(exc)
    return RagIngestResponse(data=[RagIngestResultItem(**r.__dict__) for r in results])


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a RAG document and its chunks",
)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    service: RagService = Depends(get_rag_service),
) -> None:
    deleted = service.delete_document(db, document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RAG document '{document_id}' not found.",
        )


@router.get(
    "/health",
    response_model=RagHealthResponse,
    summary="Local RAG embedding runtime health",
)
async def rag_health(service: RagService = Depends(get_rag_service)) -> RagHealthResponse:
    if not service.enabled:
        return RagHealthResponse(data=RagHealthData(status="disabled", embedding_model_available=False))
    available = await service.check_health()
    return RagHealthResponse(
        data=RagHealthData(status="ok" if available else "unavailable", embedding_model_available=available)
    )
