from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.api.health import router as health_router
from app.api.v1.router import api_router

logger = logging.getLogger("skillforge.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Ensures static skill roadmaps catalog is seeded idempotently on startup if absent.
    Uses a cheap existence count check to prevent unnecessary database operations.
    """
    try:
        from app.db.database import SessionLocal
        from app.db.models import Roadmap
        from app.db.seed_roadmaps import seed_roadmaps

        db = SessionLocal()
        try:
            roadmap_count = db.query(Roadmap.id).count()
            if roadmap_count < 12:
                logger.info(
                    "Static roadmap catalog incomplete (%d/12 roadmaps found). Auto-initializing canonical roadmaps...",
                    roadmap_count,
                )
                seed_roadmaps(db, auto_commit=True, validate=True)
                logger.info("Static roadmap catalog auto-initialization complete.")
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Could not auto-initialize static roadmaps catalog on startup: %s", exc)

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SkillForge AI Backend API — Phase 2 Resume Intelligence",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS configuration
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Standardized Error Handlers conforming to docs/api/API_SPEC.md Section 2
HTTP_STATUS_CODE_MAP = {
    400: "BAD_REQUEST",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_SERVER_ERROR",
    502: "UPSTREAM_GATEWAY_ERROR",
    504: "GATEWAY_TIMEOUT",
}


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    error_code = HTTP_STATUS_CODE_MAP.get(exc.status_code, "ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": {
                "code": error_code,
                "message": str(exc.detail),
                "details": {},
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = jsonable_encoder(exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "detail": errors,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed.",
                "details": {"errors": errors},
            },
        },
    )


# Root-level health checks (matching both /health and /api/v1/health)
app.include_router(health_router)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", summary="Root Welcome")
def root_endpoint() -> dict:
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "docs": f"{settings.API_V1_STR}/docs",
    }
