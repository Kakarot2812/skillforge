"""
API router for Candidate User Profile.
Phase: Persistent Personalization Architecture (Checkpoint 4: User Profile Foundation).

Endpoints:
- POST   /api/v1/profile — Create candidate user profile (one-to-one)
- GET    /api/v1/profile — Retrieve authenticated candidate's user profile
- PATCH  /api/v1/profile — Partially update candidate user profile
- DELETE /api/v1/profile — Delete candidate user profile (preserves User record)

Security & Architecture:
- User identity is resolved strictly via trusted X-User-Id request header.
- user_id is forbidden in request body (extra="forbid").
- All database operations are delegated strictly to UserProfileService.
"""

import logging
from typing import Optional
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services.user_profile_service import (
    InvalidUserProfileError,
    UserNotFoundError,
    UserProfileAlreadyExistsError,
    UserProfileNotFoundError,
    user_profile_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["User Profile"])


# -----------------------------------------------------------------------------
# Authentication & Identity Resolution Dependency
# -----------------------------------------------------------------------------

def resolve_authenticated_user_id(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> UUID:
    """
    Resolves and verifies candidate user identity from the trusted X-User-Id header.
    Rejects missing header with 401.
    Rejects malformed UUID with 422.
    Rejects nonexistent user with 404.
    """
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-User-Id header missing.",
        )

    try:
        user_uuid = UUID(x_user_id.strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid user ID format in X-User-Id header.",
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_uuid}' not found.",
        )

    return user_uuid


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Candidate User Profile",
    description="Creates a new one-to-one user profile for the authenticated candidate. Rejects duplicate profiles.",
)
def create_profile(
    profile_data: UserProfileCreate,
    user_id: UUID = Depends(resolve_authenticated_user_id),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    try:
        profile = user_profile_service.create_profile(
            db=db,
            user_id=user_id,
            profile_data=profile_data,
        )
        return UserProfileResponse.model_validate(profile)
    except UserProfileAlreadyExistsError as exc:
        logger.warning("Attempted duplicate profile creation for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User profile already exists for this user.",
        )
    except InvalidUserProfileError as exc:
        logger.warning("Validation error in profile creation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except UserNotFoundError as exc:
        logger.warning("User not found during profile creation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Candidate User Profile",
    description="Retrieves the candidate user profile for the authenticated user.",
)
def get_profile(
    user_id: UUID = Depends(resolve_authenticated_user_id),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    try:
        profile = user_profile_service.get_profile(
            db=db,
            user_id=user_id,
        )
        return UserProfileResponse.model_validate(profile)
    except UserProfileNotFoundError as exc:
        logger.info("User profile not found for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.patch(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Candidate User Profile",
    description="Partially updates candidate user profile fields for the authenticated user.",
)
def update_profile(
    profile_data: UserProfileUpdate,
    user_id: UUID = Depends(resolve_authenticated_user_id),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    try:
        profile = user_profile_service.update_profile(
            db=db,
            user_id=user_id,
            profile_data=profile_data,
        )
        return UserProfileResponse.model_validate(profile)
    except UserProfileNotFoundError as exc:
        logger.info("User profile not found for update for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )
    except InvalidUserProfileError as exc:
        logger.warning("Validation error in profile update: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Candidate User Profile",
    description="Deletes the candidate user profile. The candidate User record remains intact.",
)
def delete_profile(
    user_id: UUID = Depends(resolve_authenticated_user_id),
    db: Session = Depends(get_db),
) -> None:
    try:
        user_profile_service.delete_profile(
            db=db,
            user_id=user_id,
        )
    except UserProfileNotFoundError as exc:
        logger.info("User profile not found for deletion for user %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )
    except UserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
