"""Vercel Serverless Function entrypoint for ULPF FastAPI backend."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend and repo root are on Python search path
_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"

if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.main import app  # noqa: E402

# Export FastAPI app for Vercel Serverless Functions
handler = app
