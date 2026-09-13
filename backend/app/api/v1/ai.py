"""
API router for SkillForge AI generative explanation layer.
Post-MVP Phase 2, Checkpoint P2-C & Checkpoint 3: LangChain Integration.

Endpoint:
POST /api/v1/ai/chat — Evidence-grounded career chatbot over VerifiedContext.

Strict constraints:
- Consumes already-constructed and pre-validated VerifiedContext.
- Never constructs VerifiedContext from raw resume text, GitHub repos, or arbitrary client JSON.
- For persistent sessions (conversation_id provided), resolves candidate identity via X-User-Id header.
- Delegates all conversation and message persistence exclusively to ConversationService.
- Preserves full backward compatibility for stateless chats (conversation_id=None).
"""

import logging
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.chatbot import (
    CareerChatGenerationError,
    CareerChatRequest,
    CareerChatResponse,
    CareerChatService,
    CareerChatServiceUnavailableError,
    CareerChatTimeoutError,
    CareerChatValidationError,
)
from app.ai.context.exceptions import ContextValidationError
from app.db.database import get_db
from app.db.models import User
from app.rag import RAGService, get_shared_embedding_provider
from app.services.conversation_service import (
    ConversationNotFoundError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Career Intelligence"])


@router.post(
    "/chat",
    response_model=CareerChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Evidence-Grounded Career Chatbot",
    description=(
        "Generates natural-language reasoning and explanations grounded strictly in "
        "pre-verified SkillForge facts. Consumes a VerifiedContext; does not accept raw resumes "
        "or arbitrary unverified data. Supports persistent conversation history when conversation_id is supplied."
    ),
)
def career_chat(
    request: CareerChatRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> CareerChatResponse:
    """
    Evidence-grounded explanation endpoint.
    Orchestrates deterministic validation, evidence sufficiency checking, and local Qwen execution.
    Supports persistent conversation history via LangChain and ConversationService when conversation_id is supplied.
    """
    effective_user_id: Optional[uuid.UUID] = None

    if request.conversation_id is not None:
        if not x_user_id or not x_user_id.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required: X-User-Id header missing.",
            )
        try:
            effective_user_id = uuid.UUID(x_user_id.strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid user ID format in X-User-Id header.",
            )

        user = db.query(User).filter(User.id == effective_user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{effective_user_id}' not found.",
            )
    else:
        # Stateless mode: optional X-User-Id enables profile personalization
        if x_user_id and x_user_id.strip():
            try:
                effective_user_id = uuid.UUID(x_user_id.strip())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Invalid user ID format in X-User-Id header.",
                )
            user = db.query(User).filter(User.id == effective_user_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id '{effective_user_id}' not found.",
                )

    rag_service = RAGService(
        session=db,
        embedding_provider=get_shared_embedding_provider(),
    )
    service = CareerChatService(rag_service=rag_service)
    try:
        return service.chat(
            request=request,
            db=db if effective_user_id is not None else None,
            user_id=effective_user_id,
        )
    except (CareerChatValidationError, ContextValidationError) as exc:
        logger.warning("Validation error in career chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except (ConversationNotFoundError, UserNotFoundError) as exc:
        logger.warning("Conversation or user not found: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except CareerChatServiceUnavailableError as exc:
        logger.error("AI service unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except CareerChatTimeoutError as exc:
        logger.error("AI service timed out: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        )
    except CareerChatGenerationError as exc:
        logger.error("AI generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Unexpected error in career chat endpoint: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal career chatbot failure: {str(exc)}",
        )
    finally:
        service.close()

