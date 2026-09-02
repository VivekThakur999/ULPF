from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_analyst
from app.core.database import get_db
from app.models.privacy import PiiSetting
from app.models.user import User
from app.schemas.ingestion import DetectRequest, DetectResponse
from app.services.detection.detector import detector
from app.services.pipeline.service import STAGE_ORDER, run_record

router = APIRouter()


class PipelineTestRequest(BaseModel):
    raw: str = Field(min_length=1, max_length=64_000)
    declared_format: str | None = None
    pii_mode: str | None = None  # OFF | MASK | DETERMINISTIC_HASH; None -> configured default
    source_name: str = "debugger"


@router.post("/detect", response_model=DetectResponse)
def detect_format(payload: DetectRequest, _: User = Depends(get_current_user)):
    res = detector.detect(payload.sample, hint=payload.hint)
    return DetectResponse(**res.to_dict())


@router.post("/test")
def pipeline_test(
    payload: PipelineTestRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_analyst),
):
    """Run the full pipeline on one raw line and return every stage's I/O.

    This is the backend for the Live Pipeline Debugger (Module 19). It does not
    persist anything.
    """
    pii_row = db.get(PiiSetting, "default")
    ctx = run_record(
        payload.raw.rstrip("\n"),
        line_number=1,
        source_name=payload.source_name,
        declared_format=payload.declared_format,
        pii_settings=pii_row,
        pii_mode=payload.pii_mode,
    )
    return {
        "raw": payload.raw,
        "stage_order": STAGE_ORDER,
        "stages": ctx.stage_dicts(),
        "security_verdict": ctx.security_verdict,
        "detected_format": ctx.detected_format,
        "format_confidence": ctx.format_confidence,
        "parser": {"name": ctx.parser_name, "version": ctx.parser_version},
        "match_spans": ctx.parse_match_spans,
        "pii_transformations": ctx.pii_transformations,
        "disposition": ctx.disposition,
        "event": ctx.event.model_dump(mode="json") if ctx.event else None,
        "errors": ctx.errors,
        "warnings": ctx.warnings,
    }
