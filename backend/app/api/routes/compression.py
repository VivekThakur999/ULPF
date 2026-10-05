from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_analyst
from app.core.database import get_db
from app.models.ingestion import RawLog
from app.models.template import CompressionRecord, Template, TemplateMatch
from app.models.user import User
from app.schemas.compression import (
    BenchmarkRequest,
    BenchmarkResponse,
    CompressRequest,
    CompressResponse,
    CompressionRecordOut,
    DecompressRequest,
    DecompressResponse,
)
from app.services import audit
from app.services.compression.engine import ReconstructionError, compress_scope, reconstruct, run_benchmark

router = APIRouter()


@router.post("/compress", response_model=CompressResponse)
def compress(
    payload: CompressRequest,
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst),
):
    result = compress_scope(db, job_id=payload.job_id, source=payload.source, limit=payload.limit)
    audit.record(db, action="compression.compress", actor=analyst,
                 detail=f"scope job={payload.job_id} source={payload.source} "
                        f"compressed={result.records_compressed}",
                 ip_address=request.client.host if request.client else None)
    return CompressResponse(**result.to_dict())


@router.post("/decompress", response_model=DecompressResponse)
def decompress(
    payload: DecompressRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.core.config import settings

    if settings.use_mongodb:
        try:
            from app.repositories.mongodb.ingestion import MongoIngestionRepository
            from app.repositories.mongodb.templates import MongoTemplateRepository

            mongo_ingest = MongoIngestionRepository()
            mongo_tpl = MongoTemplateRepository()

            raw_doc = mongo_ingest.get_raw_log(payload.raw_log_id)
            if raw_doc:
                match_doc = mongo_tpl.get_match_by_raw_log_id(payload.raw_log_id)
                if not match_doc:
                    return DecompressResponse(
                        raw_log_id=payload.raw_log_id, template_key=None, original=raw_doc["content"],
                        reconstructed=None, exact_match=False, variables=[],
                    )
                tpl_doc = mongo_tpl.get_template(match_doc["template_id"])
                if tpl_doc:
                    tpl_model = Template(
                        template_key=tpl_doc["template_key"],
                        pattern=tpl_doc["pattern"],
                        token_count=tpl_doc["token_count"],
                        literal_tokens=tpl_doc["literal_tokens"],
                        variable_types=tpl_doc["variable_types"],
                        separators=tpl_doc["separators"],
                        trailing=tpl_doc["trailing"],
                    )
                    match_model = TemplateMatch(
                        template_id=match_doc["template_id"],
                        raw_log_id=match_doc["raw_log_id"],
                        variables=match_doc["variables"],
                        separators=match_doc.get("separators"),
                        trailing=match_doc.get("trailing", ""),
                    )
                    try:
                        rebuilt = reconstruct(tpl_model, match_model)
                        exact = rebuilt == raw_doc["content"]
                    except ReconstructionError:
                        rebuilt, exact = None, False
                    return DecompressResponse(
                        raw_log_id=payload.raw_log_id,
                        template_key=tpl_doc["template_key"],
                        original=raw_doc["content"],
                        reconstructed=rebuilt,
                        exact_match=exact,
                        variables=match_doc["variables"],
                    )
        except Exception:
            pass

    raw = db.get(RawLog, payload.raw_log_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Raw log not found")
    match = db.execute(
        select(TemplateMatch).where(TemplateMatch.raw_log_id == raw.id)
    ).scalars().first()
    if not match:
        return DecompressResponse(
            raw_log_id=raw.id, template_key=None, original=raw.content,
            reconstructed=None, exact_match=False, variables=[],
        )
    template = db.get(Template, match.template_id)
    try:
        rebuilt = reconstruct(template, match)
        exact = rebuilt == raw.content
    except ReconstructionError:
        rebuilt, exact = None, False
    return DecompressResponse(
        raw_log_id=raw.id, template_key=template.template_key if template else None,
        original=raw.content, reconstructed=rebuilt, exact_match=exact,
        variables=match.variables,
    )


@router.post("/benchmark", response_model=BenchmarkResponse)
def benchmark(
    payload: BenchmarkRequest,
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst),
):
    result = run_benchmark(db, job_id=payload.job_id, source=payload.source, limit=payload.limit)
    audit.record(db, action="compression.benchmark", actor=analyst,
                 detail=f"scope={result.scope} records={result.record_count} "
                        f"reduction={result.reduction_pct:.1f}%",
                 ip_address=request.client.host if request.client else None)
    return BenchmarkResponse(**result.to_dict())


@router.get("/records", response_model=list[CompressionRecordOut])
def list_records(
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from app.core.config import settings

    if settings.use_mongodb:
        try:
            from app.repositories.mongodb.templates import MongoTemplateRepository

            mongo_tpl = MongoTemplateRepository()
            items = mongo_tpl.list_compression_records(limit=limit)
            return [CompressionRecordOut.model_validate(r) for r in items]
        except Exception:
            pass

    rows = db.execute(
        select(CompressionRecord).order_by(desc(CompressionRecord.ts)).limit(limit)
    ).scalars().all()
    return rows
