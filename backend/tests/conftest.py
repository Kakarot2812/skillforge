import uuid
from typing import Optional
import pytest
from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from app.main import app
from app.config import settings
from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_active_user, get_optional_current_user


def resolve_test_user(
    request: Request,
    db: Session,
    required: bool = True,
) -> Optional[User]:
    """
    Test-only identity resolver.
    Enables existing legacy tests to run seamlessly without weakening production security.
    """
    # 1. If explicit anonymous test header is passed, reject with 401
    if request.headers.get("X-Test-Anonymous") == "true":
        if required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required: session cookie missing.",
            )
        return None

    # 2. Auth routes always use real production logic
    if request.url.path.startswith("/api/v1/auth/"):
        return (
            get_current_active_user(request=request, db=db)
            if required
            else get_optional_current_user(request=request, db=db)
        )

    # 3. If real session cookie is present, use real production logic
    if settings.SESSION_COOKIE_NAME in request.cookies:
        return (
            get_current_active_user(request=request, db=db)
            if required
            else get_optional_current_user(request=request, db=db)
        )

    # 4. Check X-User-Id header
    x_user_id = request.headers.get("X-User-Id")
    query_user_id = request.query_params.get("user_id")

    if x_user_id and x_user_id.strip():
        try:
            header_uuid = uuid.UUID(x_user_id.strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid user ID format in X-User-Id header.",
            )

        if query_user_id and query_user_id.strip():
            try:
                q_uuid = uuid.UUID(query_user_id.strip())
                if q_uuid != header_uuid:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cross-user access denied: target user_id does not match authenticated user context.",
                    )
            except ValueError:
                pass

        user = db.query(User).filter(User.id == header_uuid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{header_uuid}' not found.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive.",
            )
        return user

    # 5. Check query_params user_id (for legacy tests that pass ?user_id=... without X-User-Id)
    if query_user_id and query_user_id.strip():
        try:
            q_uuid = uuid.UUID(query_user_id.strip())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid user ID format in query parameter.",
            )
        user = db.query(User).filter(User.id == q_uuid).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id '{q_uuid}' not found.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive.",
            )
        return user

    # 6. If optional auth (required=False), unauthenticated requests resolve to None
    if not required:
        return None

    # 7. Fallback for legacy tests on endpoints that ran unauthenticated before Phase 4
    if request.url.path.startswith(("/api/v1/github", "/api/v1/evidence", "/api/v1/resumes", "/api/v1/skills/claimed")):
        default_user = db.query(User).filter(User.email == "legacy-test-runner@skillforge.test").first()
        if not default_user:
            default_user = User(
                id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
                email="legacy-test-runner@skillforge.test",
                full_name="Legacy Test Runner",
                hashed_password="hash",
                is_active=True,
            )
            db.add(default_user)
            try:
                db.commit()
            except Exception:
                db.rollback()
                default_user = db.query(User).filter(User.email == "legacy-test-runner@skillforge.test").first()
        return default_user

    # 8. Neither cookie, header, nor query user_id provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: session cookie missing.",
    )


def test_get_current_active_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    return resolve_test_user(request=request, db=db, required=True)


def test_get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    return resolve_test_user(request=request, db=db, required=False)


@pytest.fixture(autouse=True)
def setup_test_auth_override():
    """Applies the test dependency overrides by default across tests."""
    app.dependency_overrides[get_current_active_user] = test_get_current_active_user
    app.dependency_overrides[get_optional_current_user] = test_get_optional_current_user
    yield
    app.dependency_overrides[get_current_active_user] = test_get_current_active_user
    app.dependency_overrides[get_optional_current_user] = test_get_optional_current_user
