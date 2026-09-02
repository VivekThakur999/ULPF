"""Top-level API router. Sub-routers are added phase by phase."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
