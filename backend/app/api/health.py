import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.health import HealthResponse, DbHealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Service Health Check")
def health_check() -> HealthResponse:
    """Basic service health check to verify the API application is running."""
    return HealthResponse(status="ok")


@router.get(
    "/health/db",
    response_model=DbHealthResponse,
    summary="Database & pgvector Health Check",
)
def database_health_check(db: Session = Depends(get_db)) -> DbHealthResponse:
    """Verifies PostgreSQL connectivity and verifies that the pgvector extension is active."""
    try:
        # Check basic connectivity
        db.execute(text("SELECT 1"))

        # Query PostgreSQL version
        version_row = db.execute(text("SHOW server_version")).scalar()

        # Check for pgvector extension
        vector_ext = db.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
        pgvector_installed = vector_ext == "vector"

        return DbHealthResponse(
            status="ok",
            database="connected",
            pgvector_installed=pgvector_installed,
            database_version=str(version_row) if version_row else None,
        )
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}", exc_info=False)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable or connection failed.",
        )
