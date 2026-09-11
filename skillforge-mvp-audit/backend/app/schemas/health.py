from typing import Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str = "ok"


class DbHealthResponse(BaseModel):
    status: str = "ok"
    database: str = "connected"
    pgvector_installed: bool
    database_version: Optional[str] = None
