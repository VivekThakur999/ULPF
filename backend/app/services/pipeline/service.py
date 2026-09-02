"""Pipeline assembly + single-record execution (used by ingestion and the debugger)."""
from __future__ import annotations

import hashlib
from typing import Any

from app.services.pipeline.base import Pipeline
from app.services.pipeline.context import PipelineContext
from app.services.pipeline.stages import PIPELINE_STAGES

STAGE_ORDER = [
    "security_shield",
    "format_detection",
    "parsing",
    "cleaning",
    "field_extraction",
    "pii_obfuscation",
    "normalization",
    "validation",
]


def build_pipeline() -> Pipeline:
    return Pipeline([cls() for cls in PIPELINE_STAGES])


_pipeline = build_pipeline()


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def run_record(
    raw_line: str,
    *,
    line_number: int = 0,
    source_name: str = "upload",
    source_category: str = "generic",
    declared_format: str | None = None,
    pii_settings: Any = None,
    pii_mode: str | None = None,
) -> PipelineContext:
    ctx = PipelineContext(
        raw_line=raw_line,
        line_number=line_number,
        source_name=source_name,
        source_category=source_category,
        declared_format=declared_format,
        pii_settings=pii_settings,
        pii_mode=pii_mode or (getattr(pii_settings, "mode", None) or "OFF"),
        content_hash=content_hash(raw_line),
    )
    return _pipeline.run(ctx)
