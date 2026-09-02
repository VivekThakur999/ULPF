from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.models.event import NormalizedEvent
from app.models.ingestion import ProcessingJob, RawLog
from app.models.privacy import PiiSetting
from app.models.security import SecurityEvent
from app.models.user import User
from app.repositories.events import EventQuery, EventRepository
from app.schemas.event import EventOut
from app.schemas.logs import LogDetailResponse, LogSearchResponse, PipelineStageView
from app.services.correlation.engine import correlate
from app.services.privacy.pii import pseudonymize

router = APIRouter()

_IP_KINDS = {"source_ip", "destination_ip", "any_ip"}
_ID_KINDS = {"username": "username", "email": "email"}


def _maybe_pseudonymize(db: Session, field: str, value: str | None) -> tuple[str | None, str | None]:
    """If PII hashing is on and the user typed a raw identifier, hash it to match."""
    if not value:
        return value, None
    row = db.get(PiiSetting, "default")
    if not row or row.mode != "DETERMINISTIC_HASH":
        return value, None
    if value.startswith(("IP_", "EMAIL_", "USER_", "HOST_")):
        return value, None  # already a pseudonym
    kind = None
    if field in _IP_KINDS and _looks_like_ip(value):
        kind = "ip"
    elif field == "username":
        kind = "username"
    elif field == "email":
        kind = "email"
    elif field == "host":
        kind = "host"
    if not kind:
        return value, None
    token = pseudonymize(value, kind, scope=row.scope, token_length=row.token_length)
    return token, f"'{value}' pseudonymized to {token} for matching (PII mode DETERMINISTIC_HASH)"


def _looks_like_ip(v: str) -> bool:
    parts = v.split(".")
    return len(parts) == 4 and all(p.isdigit() for p in parts)


@router.get("", response_model=LogSearchResponse)
@router.get("/search", response_model=LogSearchResponse)
def search_logs(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    text: str | None = None,
    time_from: datetime | None = None,
    time_to: datetime | None = None,
    source: str | None = None,
    host: str | None = None,
    source_ip: str | None = None,
    destination_ip: str | None = None,
    username: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    action: str | None = None,
    status: str | None = None,
    parser: str | None = None,
    processing_status: str | None = None,
    job_id: str | None = None,
    template_id: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
    order: str = "desc",
):
    notes = []
    source_ip, n = _maybe_pseudonymize(db, "source_ip", source_ip)
    if n:
        notes.append(n)
    destination_ip, n = _maybe_pseudonymize(db, "destination_ip", destination_ip)
    if n:
        notes.append(n)
    username, n = _maybe_pseudonymize(db, "username", username)
    if n:
        notes.append(n)

    q = EventQuery(
        text=text, time_from=time_from, time_to=time_to, source=source, host=host,
        source_ip=source_ip, destination_ip=destination_ip, username=username,
        event_type=event_type, severity=severity, action=action, status=status,
        parser=parser, processing_status=processing_status, job_id=job_id,
        template_id=template_id, limit=limit, offset=offset, order=order,
    )
    page = EventRepository(db).search(q)
    return LogSearchResponse(
        total=page.total,
        items=[EventOut.model_validate(e) for e in page.items],
        limit=limit, offset=offset,
        note="; ".join(notes) or None,
    )


@router.get("/stats")
def log_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    repo = EventRepository(db)
    q = EventQuery(limit=1)
    total = repo.search(q).total
    facets = repo.facets(q, ["source", "event_type", "severity", "parser",
                             "processing_status", "host"])
    return {"total_events": total, "facets": facets,
            "timeseries": repo.timeseries(q, bucket="hour")}


@router.get("/facets")
def log_facets(
    fields: str = "source,event_type,severity,parser",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = EventRepository(db)
    return repo.facets(EventQuery(limit=1), [f.strip() for f in fields.split(",") if f.strip()])


@router.get("/pseudonymize")
def pseudonymize_value(
    value: str,
    kind: str = "ip",
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(PiiSetting, "default")
    if not row or row.mode != "DETERMINISTIC_HASH":
        return {"value": value, "pseudonym": value, "mode": row.mode if row else "OFF"}
    return {
        "value": value,
        "pseudonym": pseudonymize(value, kind, scope=row.scope, token_length=row.token_length),
        "mode": "DETERMINISTIC_HASH",
    }


@router.get("/{event_id}", response_model=LogDetailResponse)
def log_detail(event_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from app.services.pipeline.service import run_record

    event = db.get(NormalizedEvent, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    raw = db.get(RawLog, event.raw_log_id) if event.raw_log_id else None
    job = db.get(ProcessingJob, event.job_id) if event.job_id else None

    pii_row = db.get(PiiSetting, "default")
    ctx = run_record(event.raw_log, source_name=event.source, pii_settings=pii_row)
    pipeline = [
        PipelineStageView(
            stage=s.stage, status=s.status, summary=s.summary,
            fields={k: _js(v) for k, v in s.fields.items()},
            transformations=s.transformations, warnings=s.warnings, errors=s.errors,
        )
        for s in ctx.stages
    ]

    related = []
    if event.source_ip or event.username:
        corr = correlate(
            db,
            source_ip=event.source_ip if event.source_ip else None,
            username=event.username if event.username and not event.source_ip else None,
            center_time=event.timestamp, window_seconds=1800, max_events=25,
        )
        related = [
            EventOut.model_validate(e)
            for e in db.query(NormalizedEvent)
            .filter(NormalizedEvent.id.in_([i for i in corr.event_ids if i != event_id][:25]))
            .all()
        ]

    sec = db.query(SecurityEvent).filter(SecurityEvent.raw_reference == (raw.id if raw else "")).all()

    return LogDetailResponse(
        event=EventOut.model_validate(event),
        raw_log={
            "id": raw.id, "line_number": raw.line_number, "content": raw.content,
            "status": raw.status, "security_verdict": raw.security_verdict,
            "processing_errors": raw.processing_errors,
        } if raw else None,
        job={"id": job.id, "filename": job.filename, "detected_format": job.detected_format,
             "source_name": job.source_name} if job else None,
        pipeline=pipeline,
        pii_transformations=ctx.pii_transformations,
        related_events=related,
        security_events=[
            {"id": s.id, "detection_type": s.detection_type, "verdict": s.verdict,
             "severity": s.severity, "reason": s.reason, "indicators": s.indicators}
            for s in sec
        ],
    )


def _js(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)
