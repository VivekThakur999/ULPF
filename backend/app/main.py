"""ULPF backend application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import __version__
from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging, get_logger

configure_logging("DEBUG" if settings.debug else "INFO")
log = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verify database connectivity on boot (Phase 1 acceptance criterion).
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log.info("Database connection OK (%s)", "sqlite" if settings.is_sqlite else "postgresql")
    except Exception as exc:  # pragma: no cover - startup diagnostics
        log.error("Database connection FAILED: %s", exc)

    # Create tables + seed on startup when running without Alembic (dev/demo).
    try:
        from app.core.bootstrap import bootstrap

        bootstrap()
    except Exception as exc:  # pragma: no cover
        log.warning("Bootstrap skipped/failed: %s", exc)

    # Register declarative parser packs (disk + DB).
    try:
        from app.services.parsing.loader import load_all_parsers

        load_all_parsers()
    except Exception as exc:  # pragma: no cover
        log.warning("Parser pack loading failed: %s", exc)

    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Universal Log Pre-processing Framework - SIH26156 (NTRO)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
@app.get("/api/health", tags=["system"], include_in_schema=False)
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": __version__,
        "environment": settings.environment,
        "database": "connected" if db_ok else "unavailable",
    }


# --- Routers (added progressively per phase) ---
try:
    from app.api.router import api_router

    app.include_router(api_router, prefix=settings.api_prefix)
except Exception as exc:  # pragma: no cover
    log.warning("API router not loaded yet: %s", exc)
