"""
User Profile Service for SkillForge AI.
Phase: Persistent Personalization Architecture (Checkpoint 4: User Profile Foundation).

Provides application-level persistence operations for candidate user profiles:
- Create profile (one-to-one with user, cleanly rejects duplicates)
- Get profile (verifies user exists, returns 404 domain error if missing)
- Update profile (partial update semantics, updates updated_at)
- Delete profile (removes profile record while preserving user)

Strict architectural invariants:
- Profile belongs to the User, completely separate from Chat History.
- User identity is resolved strictly from trusted context (user_id).
- Follows ConversationService transaction/commit durability conventions.
"""

from datetime import datetime, timezone
import logging
from typing import Optional
import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import User, UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Domain Exceptions
# -----------------------------------------------------------------------------

class UserProfileError(Exception):
    """Base exception for user profile operations."""
    pass


class UserProfileNotFoundError(UserProfileError):
    """Raised when a user profile is not found."""
    pass


class UserProfileAlreadyExistsError(UserProfileError):
    """Raised when attempting to create a profile for a user who already has one."""
    pass


class UserProfileOwnershipError(UserProfileNotFoundError):
    """
    Raised when an unauthorized user attempts to access another user's profile.
    Subclasses UserProfileNotFoundError to avoid identity enumeration.
    """
    pass


class InvalidUserProfileError(UserProfileError, ValueError):
    """Raised when profile data violates domain constraints."""
    pass


class UserNotFoundError(UserProfileError):
    """Raised when the target candidate user does not exist in PostgreSQL."""
    pass


# -----------------------------------------------------------------------------
# Service Implementation
# -----------------------------------------------------------------------------

class UserProfileService:
    """Application service for candidate user profile persistence and lifecycle management."""

    def create_profile(
        self,
        db: Session,
        user_id: UUID,
        profile_data: UserProfileCreate,
    ) -> UserProfile:
        """
        Creates and persists a new one-to-one user profile for an existing user.
        Raises UserNotFoundError if user does not exist.
        Raises UserProfileAlreadyExistsError if a profile already exists for the user.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError(f"User with id '{user_id}' not found.")

        existing = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if existing:
            raise UserProfileAlreadyExistsError(
                f"User profile already exists for user '{user_id}'."
            )

        profile = UserProfile(
            id=uuid.uuid4(),
            user_id=user_id,
            name=profile_data.name,
            education=profile_data.education,
            college=profile_data.college,
            degree=profile_data.degree,
            branch=profile_data.branch,
            semester=profile_data.semester,
            target_role=profile_data.target_role,
            experience_level=profile_data.experience_level,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info("Created user profile %s for user %s", profile.id, user_id)
        return profile

    def get_profile(
        self,
        db: Session,
        user_id: UUID,
    ) -> UserProfile:
        """
        Retrieves the profile for the specified user.
        Raises UserNotFoundError if user does not exist.
        Raises UserProfileNotFoundError if profile does not exist.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError(f"User with id '{user_id}' not found.")

        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise UserProfileNotFoundError(
                f"User profile not found for user '{user_id}'."
            )
        return profile

    def update_profile(
        self,
        db: Session,
        user_id: UUID,
        profile_data: UserProfileUpdate,
    ) -> UserProfile:
        """
        Partially updates an existing user profile with supplied fields.
        Fields omitted in profile_data are preserved unchanged.
        Raises UserNotFoundError if user does not exist.
        Raises UserProfileNotFoundError if profile does not exist.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError(f"User with id '{user_id}' not found.")

        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise UserProfileNotFoundError(
                f"User profile not found for user '{user_id}'."
            )

        update_dict = profile_data.model_dump(exclude_unset=True)
        for key, val in update_dict.items():
            setattr(profile, key, val)

        profile.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(profile)
        logger.info("Updated user profile %s for user %s", profile.id, user_id)
        return profile

    def delete_profile(
        self,
        db: Session,
        user_id: UUID,
    ) -> None:
        """
        Deletes the user profile for the specified user.
        Does NOT delete the User record.
        Raises UserNotFoundError if user does not exist.
        Raises UserProfileNotFoundError if profile does not exist.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserNotFoundError(f"User with id '{user_id}' not found.")

        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise UserProfileNotFoundError(
                f"User profile not found for user '{user_id}'."
            )

        db.delete(profile)
        db.commit()
        logger.info("Deleted user profile %s for user %s", profile.id, user_id)


# Global singleton instance
user_profile_service = UserProfileService()
