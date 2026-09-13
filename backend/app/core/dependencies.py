"""FastAPI dependencies for request authentication and user verification."""
from app.api.deps import get_current_active_user, get_optional_current_user

__all__ = ["get_current_active_user", "get_optional_current_user"]
