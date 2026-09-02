from __future__ import annotations

import os
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_analyst
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.logging import get_logger
from app.models.ingestion import ProcessingJob, RawLog
from app.models.source import LogSource
from app.models.user import User
from app.schemas.ingestion import JobListOut, JobOut, RawLogOut
from app.services import audit
from app.services.ingestion.adapters import get_adapter
from app.services.ingestion.service import process_job

router = APIRouter()
log = get_logger("api.ingestion")

# repo-root/sample_logs
_SAMPLE_ROOT = Path(__file__).resolve().parents[4] / "sample_logs"


def _run_job(job_id: str, data: bytes) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if job:
            process_job(db, job, data)
    finally:
        db.close()


def _validate_upload(filename: str, size: int) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {settings.allowed_upload_extensions}",
        )
    if size > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_bytes} bytes")
    return ext


def _create_and_dispatch(
    db: Session, bg: BackgroundTasks, *, data: bytes, filename: str,
    source_name: str, declared_format: str | None, user: User,
    source_id: str | None = None, category: str = "generic",
) -> ProcessingJob:
    job = ProcessingJob(
        source_id=source_id,
        source_name=source_name,
        filename=filename,
        declared_format=declared_format or None,
        created_by=user.id,
        stats={"source_category": category, "bytes": len(data)},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    audit.record(db, action="ingestion.job_created", actor=user, target_type="job",
                 target_id=job.id, detail=f"file={filename} bytes={len(data)}")
    bg.add_task(_run_job, job.id, data)
    return job


@router.post("/upload", response_model=JobOut, status_code=202)
async def upload(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    source_name: str = Form("upload"),
    declared_format: str | None = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    data = await file.read()
    _validate_upload(file.filename or "upload.log", len(data))
    if not data.strip():
        raise HTTPException(status_code=422, detail="File is empty")
    job = _create_and_dispatch(
        db, background, data=data, filename=file.filename or "upload.log",
        source_name=source_name, declared_format=declared_format, user=user,
    )
    return job


@router.get("/samples")
def list_samples(_: User = Depends(get_current_user)):
    if not _SAMPLE_ROOT.exists():
        return {"root": str(_SAMPLE_ROOT), "samples": []}
    items = []
    for p in sorted(_SAMPLE_ROOT.rglob("*")):
        if p.is_file() and p.suffix.lower() in settings.allowed_upload_extensions:
            items.append({
                "path": str(p.relative_to(_SAMPLE_ROOT)).replace("\\", "/"),
                "category": p.relative_to(_SAMPLE_ROOT).parts[0],
                "bytes": p.stat().st_size,
            })
    return {"root": str(_SAMPLE_ROOT), "samples": items}


@router.post("/import-sample", response_model=JobOut, status_code=202)
def import_sample(
    background: BackgroundTasks,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    rel = (body or {}).get("path", "")
    if not rel:
        raise HTTPException(status_code=422, detail="'path' is required")
    target = (_SAMPLE_ROOT / rel).resolve()
    if not str(target).startswith(str(_SAMPLE_ROOT.resolve())) or not target.is_file():
        raise HTTPException(status_code=404, detail="Sample not found")
    data = target.read_bytes()
    source_name = (body or {}).get("source_name") or target.parent.name
    job = _create_and_dispatch(
        db, background, data=data, filename=target.name, source_name=source_name,
        declared_format=(body or {}).get("declared_format"), user=user,
        category=target.relative_to(_SAMPLE_ROOT).parts[0],
    )
    return job


@router.post("/simulate", response_model=JobOut, status_code=202)
def simulate_stream(
    background: BackgroundTasks,
    body: dict | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_analyst),
):
    body = body or {}
    source_id = body.get("source_id")
    count = int(body.get("count", 30))
    src = db.get(LogSource, source_id) if source_id else None
    adapter = get_adapter("SIMULATED", {"count": count})
    data = adapter.fetch()
    job = _create_and_dispatch(
        db, background, data=data, filename="simulated-stream.log",
        source_name=src.name if src else "simulated",
        declared_format=None, user=user,
        source_id=src.id if src else None,
        category=src.category if src else "generic",
    )
    return job


@router.get("/jobs", response_model=JobListOut)
def list_jobs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ProcessingJob)
    total = q.count()
    rows = q.order_by(desc(ProcessingJob.created_at)).offset(offset).limit(min(limit, 200)).all()
    return JobListOut(total=total, items=[JobOut.model_validate(r) for r in rows])


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/records", response_model=list[RawLogOut])
def job_records(
    job_id: str,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not db.get(ProcessingJob, job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    q = db.query(RawLog).filter(RawLog.job_id == job_id)
    if status:
        q = q.filter(RawLog.status == status.upper())
    rows = q.order_by(RawLog.line_number).offset(offset).limit(min(limit, 500)).all()
    return rows
