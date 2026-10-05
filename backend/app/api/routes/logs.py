import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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


def _event_to_ecs_dict(e: NormalizedEvent) -> dict[str, Any]:
    """Map normalized event to standard ECS 1.0 / ULPF machine-readable format for SIEM ingestion."""
    timestamp_str = e.timestamp.isoformat() if e.timestamp else (e.ingested_at.isoformat() if e.ingested_at else None)
    created_at_str = e.created_at.isoformat() if e.created_at else timestamp_str

    doc: dict[str, Any] = {
        "@timestamp": timestamp_str,
        "ecs": {"version": "1.12.0"},
        "event": {
            "id": e.id,
            "created": created_at_str,
            "kind": "event",
            "category": [e.event_type] if e.event_type else ["unknown"],
            "type": [e.action] if e.action else ["info"],
            "outcome": e.status or "unknown",
            "severity": e.severity,
            "reason": e.message,
        },
        "log": {
            "original": e.raw_log,
            "level": e.severity,
        },
        "message": e.message,
    }
    if e.host:
        doc["host"] = {"name": e.host}
    if e.source_ip or e.source_port:
        doc["source"] = {k: v for k, v in {"ip": e.source_ip, "port": e.source_port}.items() if v is not None}
    if e.destination_ip or e.destination_port:
        doc["destination"] = {k: v for k, v in {"ip": e.destination_ip, "port": e.destination_port}.items() if v is not None}
    if e.protocol:
        doc["network"] = {"protocol": e.protocol}
    if e.username or e.email:
        doc["user"] = {k: v for k, v in {"name": e.username, "email": e.email}.items() if v is not None}
    if e.http_method or e.url or e.response_code is not None:
        http_data = {}
        if e.http_method:
            http_data["request"] = {"method": e.http_method}
        if e.response_code is not None:
            http_data["response"] = {"status_code": e.response_code}
        if e.url:
            doc["url"] = {"original": e.url}
        if http_data:
            doc["http"] = http_data
    if e.process:
        doc["process"] = {"name": e.process}
    if e.service:
        doc["service"] = {"name": e.service}

    doc["ulpf"] = {
        "schema_version": e.schema_version or "1.0",
        "source": e.source,
        "parser": e.parser,
        "parser_version": e.parser_version,
        "pii_protected": e.pii_protected,
        "pii_mode": e.pii_mode,
        "confidence": e.confidence,
        "processing_status": e.processing_status,
        "template_id": e.template_id,
        "traceability": {
            "raw_log_id": e.raw_log_id,
            "job_id": e.job_id,
        },
        "extra": e.extra if isinstance(e.extra, dict) else {},
    }
    return doc


def _event_to_ml_record(e: NormalizedEvent) -> dict[str, Any]:
    """Extract numeric & categorical feature representation suitable for downstream ML/analytics."""
    ts = e.timestamp or e.ingested_at or datetime.now(timezone.utc)
    ts_epoch = ts.timestamp()
    hour = ts.hour
    dow = ts.weekday()

    severity_map = {
        "DEBUG": 0, "INFO": 1, "NOTICE": 1, "WARNING": 2,
        "WARN": 2, "ERROR": 3, "ERR": 3, "CRITICAL": 4,
        "FATAL": 4, "ALERT": 4, "EMERGENCY": 4,
    }
    sev_num = severity_map.get((e.severity or "").upper(), 1)
    is_error = 1 if sev_num >= 3 or (e.status and e.status.lower() in {"failure", "denied", "error", "blocked"}) else 0
    has_src_ip = 1 if e.source_ip else 0
    has_dst_ip = 1 if e.destination_ip else 0
    msg_len = len(e.message or "")
    raw_len = len(e.raw_log or "")
    pii_int = 1 if e.pii_protected else 0
    conf = float(e.confidence or 1.0)

    feature_vector = [
        round(ts_epoch, 2),
        hour,
        dow,
        sev_num,
        is_error,
        has_src_ip,
        has_dst_ip,
        e.source_port or 0,
        e.destination_port or 0,
        e.response_code or 0,
        msg_len,
        raw_len,
        pii_int,
        conf,
    ]

    return {
        "event_id": e.id,
        "timestamp_iso": ts.isoformat(),
        "timestamp_epoch": ts_epoch,
        "hour_of_day": hour,
        "day_of_week": dow,
        "source": e.source,
        "event_type": e.event_type or "unknown",
        "severity_label": e.severity or "INFO",
        "severity_numeric": sev_num,
        "action": e.action or "unknown",
        "status": e.status or "unknown",
        "protocol": e.protocol,
        "source_ip": e.source_ip,
        "destination_ip": e.destination_ip,
        "source_port": e.source_port,
        "destination_port": e.destination_port,
        "response_code": e.response_code,
        "message_length": msg_len,
        "raw_log_length": raw_len,
        "pii_protected": e.pii_protected,
        "confidence_score": conf,
        "template_id": e.template_id,
        "feature_vector": feature_vector,
    }


@router.get("/export/ndjson")
def export_logs_ndjson(
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
    limit: int = Query(1000, le=10000),
    offset: int = Query(0, ge=0),
    order: str = "desc",
):
    """Export normalized events in standard ECS-compatible NDJSON format for SIEM/Data Lake ingestion."""
    source_ip, _ = _maybe_pseudonymize(db, "source_ip", source_ip)
    destination_ip, _ = _maybe_pseudonymize(db, "destination_ip", destination_ip)
    username, _ = _maybe_pseudonymize(db, "username", username)

    q = EventQuery(
        text=text, time_from=time_from, time_to=time_to, source=source, host=host,
        source_ip=source_ip, destination_ip=destination_ip, username=username,
        event_type=event_type, severity=severity, action=action, status=status,
        parser=parser, processing_status=processing_status, job_id=job_id,
        template_id=template_id, limit=limit, offset=offset, order=order,
    )
    page = EventRepository(db).search(q)
    
    lines = [json.dumps(_event_to_ecs_dict(e), default=str) for e in page.items]
    payload = "\n".join(lines) + ("\n" if lines else "")
    
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Response(
        content=payload,
        media_type="application/x-ndjson",
        headers={
            "Content-Disposition": f'attachment; filename="ulpf_events_{ts_str}.ndjson"',
            "X-Total-Count": str(page.total),
            "X-Exported-Count": str(len(page.items)),
        },
    )


@router.get("/export/json")
def export_logs_json(
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
    limit: int = Query(1000, le=10000),
    offset: int = Query(0, ge=0),
    order: str = "desc",
):
    """Export normalized events in standard JSON format with schema version metadata."""
    source_ip, _ = _maybe_pseudonymize(db, "source_ip", source_ip)
    destination_ip, _ = _maybe_pseudonymize(db, "destination_ip", destination_ip)
    username, _ = _maybe_pseudonymize(db, "username", username)

    q = EventQuery(
        text=text, time_from=time_from, time_to=time_to, source=source, host=host,
        source_ip=source_ip, destination_ip=destination_ip, username=username,
        event_type=event_type, severity=severity, action=action, status=status,
        parser=parser, processing_status=processing_status, job_id=job_id,
        template_id=template_id, limit=limit, offset=offset, order=order,
    )
    page = EventRepository(db).search(q)
    
    data = {
        "schema_version": "1.0.0",
        "export_type": "siem_universal_events",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_available": page.total,
        "exported_count": len(page.items),
        "events": [_event_to_ecs_dict(e) for e in page.items],
    }
    payload = json.dumps(data, default=str, indent=2)
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="ulpf_events_{ts_str}.json"',
            "X-Total-Count": str(page.total),
            "X-Exported-Count": str(len(page.items)),
        },
    )


@router.get("/export/ml-ready")
def export_logs_ml_ready(
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
    limit: int = Query(1000, le=10000),
    offset: int = Query(0, ge=0),
    order: str = "desc",
):
    """Export normalized events as numerical & categorical feature vectors for downstream ML/analytics."""
    source_ip, _ = _maybe_pseudonymize(db, "source_ip", source_ip)
    destination_ip, _ = _maybe_pseudonymize(db, "destination_ip", destination_ip)
    username, _ = _maybe_pseudonymize(db, "username", username)

    q = EventQuery(
        text=text, time_from=time_from, time_to=time_to, source=source, host=host,
        source_ip=source_ip, destination_ip=destination_ip, username=username,
        event_type=event_type, severity=severity, action=action, status=status,
        parser=parser, processing_status=processing_status, job_id=job_id,
        template_id=template_id, limit=limit, offset=offset, order=order,
    )
    page = EventRepository(db).search(q)

    feature_names = [
        "timestamp_epoch", "hour_of_day", "day_of_week", "severity_numeric",
        "is_error", "has_source_ip", "has_dest_ip", "source_port",
        "destination_port", "response_code", "message_length",
        "raw_log_length", "pii_protected", "confidence_score",
    ]

    data = {
        "schema_version": "1.0.0",
        "export_type": "ml_feature_matrix",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_available": page.total,
        "exported_count": len(page.items),
        "feature_names": feature_names,
        "records": [_event_to_ml_record(e) for e in page.items],
    }
    payload = json.dumps(data, default=str, indent=2)
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="ulpf_ml_features_{ts_str}.json"',
            "X-Total-Count": str(page.total),
            "X-Exported-Count": str(len(page.items)),
        },
    )


@router.get("/{event_id}", response_model=LogDetailResponse)
def log_detail(event_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from app.core.config import settings
    from app.services.pipeline.service import run_record

    event_repo = EventRepository(db)
    event = event_repo.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    raw_dict = None
    job_dict = None
    sec_list = []

    if settings.use_mongodb:
        try:
            from app.repositories.mongodb.alerts import MongoAlertRepository
            from app.repositories.mongodb.ingestion import MongoIngestionRepository

            mongo_ingest = MongoIngestionRepository()
            mongo_alerts = MongoAlertRepository()

            if event.raw_log_id:
                raw_dict = mongo_ingest.get_raw_log(event.raw_log_id)
            if event.job_id:
                job_dict = mongo_ingest.get_job(event.job_id)
            if event.raw_log_id:
                sec_list = mongo_alerts.list_security_events(raw_reference=event.raw_log_id)
        except Exception:
            pass

    if raw_dict is None and event.raw_log_id:
        raw_model = db.get(RawLog, event.raw_log_id)
        if raw_model:
            raw_dict = {
                "id": raw_model.id, "line_number": raw_model.line_number,
                "content": raw_model.content, "status": raw_model.status,
                "security_verdict": raw_model.security_verdict,
                "processing_errors": raw_model.processing_errors,
            }
    if job_dict is None and event.job_id:
        job_model = db.get(ProcessingJob, event.job_id)
        if job_model:
            job_dict = {
                "id": job_model.id, "filename": job_model.filename,
                "detected_format": job_model.detected_format,
                "source_name": job_model.source_name,
            }
    if not sec_list and event.raw_log_id:
        sec_models = db.query(SecurityEvent).filter(SecurityEvent.raw_reference == event.raw_log_id).all()
        sec_list = [
            {"id": s.id, "detection_type": s.detection_type, "verdict": s.verdict,
             "severity": s.severity, "reason": s.reason, "indicators": s.indicators}
            for s in sec_models
        ]

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
        rel_ids = [i for i in corr.event_ids if i != event_id][:25]
        if rel_ids:
            rel_page = event_repo.search(EventQuery(fields_in={"id": rel_ids}, limit=25))
            related = [EventOut.model_validate(e) for e in rel_page.items]

    return LogDetailResponse(
        event=EventOut.model_validate(event),
        raw_log=raw_dict,
        job=job_dict,
        pipeline=pipeline,
        pii_transformations=ctx.pii_transformations,
        related_events=related,
        security_events=[
            {"id": s.get("id"), "detection_type": s.get("detection_type"), "verdict": s.get("verdict"),
             "severity": s.get("severity"), "reason": s.get("reason"), "indicators": s.get("indicators", [])}
            for s in sec_list
        ],
    )


def _js(v):
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    return str(v)
