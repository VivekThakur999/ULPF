"""Top-level API router. Sub-routers are added phase by phase."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    ai,
    alerts,
    analytics,
    auth,
    compression,
    detection,
    ingestion,
    logs,
    parsers,
    pipeline,
    privacy,
    response,
    security,
    sources,
    templates,
    users,
    wasm,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
api_router.include_router(privacy.router, prefix="/privacy", tags=["privacy"])
api_router.include_router(security.router, prefix="/security", tags=["security"])
api_router.include_router(detection.router, prefix="/detection", tags=["detection"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(parsers.router, prefix="/parsers", tags=["parsers"])
api_router.include_router(wasm.router, prefix="/wasm", tags=["wasm"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(compression.router, prefix="/compression", tags=["compression"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(response.router, prefix="/response", tags=["response"])
