"""
API router for SkillForge AI generative explanation layer.
Post-MVP Phase 2, Checkpoint P2-C.

Endpoint:
POST /api/v1/ai/chat — Evidence-grounded career chatbot over VerifiedContext.

Strict constraints:
- Consumes already-constructed and pre-validated VerifiedContext.
- Never constructs VerifiedContext from raw resume text, GitHub repos, or arbitrary client JSON.
- Never queries the database or persists conversations.
"""

import logging
from fastapi import APIRouter, HTTPException, status

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
        "or arbitrary unverified data."
    ),
)
def career_chat(request: CareerChatRequest) -> CareerChatResponse:
    """
    Evidence-grounded explanation endpoint.
    Orchestrates deterministic validation, evidence sufficiency checking, and local Qwen execution.
    """
    service = CareerChatService()
    try:
        return service.chat(request)
    except (CareerChatValidationError, ContextValidationError) as exc:
        logger.warning("Validation error in career chat: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
