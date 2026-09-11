"""
API routes for candidate user identity management.

Provides a minimal, secure lifecycle mechanism to register legitimate candidate identities
and verify existing candidate rows in PostgreSQL.

Enforces:
- Canonical user existence in the backend before user-scoped operations.
- Client cannot choose arbitrary UUIDs, ownership fields, or privileged roles.
- Normal authenticated endpoints continue to reject unknown X-User-Id headers.
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register/Establish Candidate User Identity",
    description=(
        "Explicitly creates a candidate User record in PostgreSQL and returns the canonical UUID. "
        "Server generates the UUID to prevent client spoofing or collisions."
    ),
)
def create_candidate_user(
    payload: Optional[UserCreate] = None,
    db: Session = Depends(get_db),
) -> UserRead:
    new_id = uuid.uuid4()
    if payload and payload.email and payload.email.strip():
        email = payload.email.strip().lower()
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return UserRead.model_validate(existing)
    else:
        email = f"candidate-{new_id}@skillforge.local"

    user = User(
        id=new_id,
        email=email,
        full_name=payload.full_name.strip() if payload and payload.full_name else None,
        target_role=payload.target_role.strip() if payload and payload.target_role else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserRead.model_validate(user)


@router.get(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Get Authenticated Candidate User",
    description="Retrieves the candidate User record corresponding to the provided X-User-Id header.",
)
def get_current_user(
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> UserRead:
    if not x_user_id or not x_user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: X-User-Id header missing.",
        )
    try:
        user_uuid = uuid.UUID(x_user_id.strip())
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
    return UserRead.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Verify Candidate User Exists by ID",
    description="Verifies whether a candidate user exists in PostgreSQL. Returns 404 if not found.",
)
def get_user_by_id(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> UserRead:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found.",
        )
    return UserRead.model_validate(user)
