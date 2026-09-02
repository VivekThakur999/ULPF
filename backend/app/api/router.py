"""Top-level API router. Sub-routers are added phase by phase."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    auth,
    ingestion,
    pipeline,
    privacy,
    security,
    sources,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(privacy.router, prefix="/privacy", tags=["privacy"])
api_router.include_router(security.router, prefix="/security", tags=["security"])
