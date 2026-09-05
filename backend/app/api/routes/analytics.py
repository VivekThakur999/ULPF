from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.models.event import NormalizedEvent
from app.models.ingestion import (
    JOB_COMPLETED,
    RAW_STATUS_DUPLICATE,
    RAW_STATUS_INVALID,
    RAW_STATUS_PROCESSED,
    RAW_STATUS_QUARANTINED,
    ProcessingJob,
    RawLog,
)
from app.models.privacy import PiiSetting
from app.models.security import SecurityAlert, SecurityEvent
from app.models.source import LogSource
from app.models.user import User
from app.repositories.events import EventQuery, EventRepository

router = APIRouter()


def _count(db: Session, model, *conds) -> int:
    stmt = select(func.count()).select_from(model)
    for c in conds:
        stmt = stmt.where(c)
    return db.scalar(stmt) or 0


def _group_count(db: Session, column, *conds, limit: int = 15) -> list[dict]:
    stmt = select(column, func.count().label("n")).where(column.isnot(None))
    for c in conds:
        stmt = stmt.where(c)
    stmt = stmt.group_by(column).order_by(func.count().desc()).limit(limit)
    return [{"label": str(r[0]), "value": r[1]} for r in db.execute(stmt).all()]


@router.get("/overview")
def overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    total_raw = _count(db, RawLog)
    processed = _count(db, RawLog, RawLog.status == RAW_STATUS_PROCESSED)
    invalid = _count(db, RawLog, RawLog.status == RAW_STATUS_INVALID)
    duplicates = _count(db, RawLog, RawLog.status == RAW_STATUS_DUPLICATE)
    quarantined = _count(db, RawLog, RawLog.status == RAW_STATUS_QUARANTINED)
    events = _count(db, NormalizedEvent)
    alerts_total = _count(db, SecurityAlert)

    rate_rows = db.execute(
        select(ProcessingJob.processing_rate).where(
            ProcessingJob.status == JOB_COMPLETED, ProcessingJob.processing_rate > 0
        )
    ).scalars().all()
    avg_rate = round(sum(rate_rows) / len(rate_rows), 1) if rate_rows else 0.0
    peak_rate = round(max(rate_rows), 1) if rate_rows else 0.0

    pii_protected = _count(db, NormalizedEvent, NormalizedEvent.pii_protected.is_(True))

    # risk distribution by band
    alert_rows = db.execute(select(SecurityAlert.risk_score, SecurityAlert.severity)).all()
    bands = {"info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
    for score, _sev in alert_rows:
        b = ("critical" if score >= 85 else "high" if score >= 65 else "medium"
             if score >= 40 else "low" if score >= 15 else "info")
        bands[b] += 1

    success_rate = round(processed / total_raw * 100, 1) if total_raw else 0.0

    repo = EventRepository(db)
    timeseries = repo.timeseries(EventQuery(limit=1), bucket="hour")

    # source status: configured sources + de-facto sources seen in jobs
    configured = db.execute(select(LogSource)).scalars().all()
    seen = db.execute(
        select(NormalizedEvent.source, func.count().label("n"),
               func.max(NormalizedEvent.ingested_at).label("last"))
        .group_by(NormalizedEvent.source)
    ).all()
    seen_map = {r[0]: {"events": r[1], "last": r[2]} for r in seen}
    source_status = []
    covered = set()
    for s in configured:
        info = seen_map.get(s.name, {})
        covered.add(s.name)
        source_status.append({
            "name": s.name, "category": s.category, "adapter": s.adapter,
            "status": "RECEIVING" if info else s.connection_status,
            "events_processed": info.get("events", s.events_processed),
            "last_received": info["last"].isoformat() if info.get("last") else (
                s.last_received_at.isoformat() if s.last_received_at else None),
            "configured": True,
        })
    for name, info in seen_map.items():
        if name in covered:
            continue
        source_status.append({
            "name": name, "category": "uploaded", "adapter": "FILE",
            "status": "RECEIVING", "events_processed": info["events"],
            "last_received": info["last"].isoformat() if info["last"] else None,
            "configured": False,
        })

    return {
        "cards": {
            "total_logs": total_raw,
            "processed": processed,
            "invalid": invalid,
            "duplicates": duplicates,
            "quarantined": quarantined,
            "normalized_events": events,
            "alerts": alerts_total,
            "avg_processing_rate": avg_rate,
            "peak_processing_rate": peak_rate,
        },
        "charts": {
            "logs_by_source": _group_count(db, NormalizedEvent.source),
            "logs_by_format": _group_count(db, ProcessingJob.detected_format),
            "events_by_severity": _group_count(db, NormalizedEvent.severity),
            "events_by_type": _group_count(db, NormalizedEvent.event_type),
            "events_over_time": timeseries,
            "processing_outcomes": [
                {"label": "processed", "value": processed},
                {"label": "invalid", "value": invalid},
                {"label": "duplicate", "value": duplicates},
                {"label": "quarantined", "value": quarantined},
            ],
            "pii_transformations": [
                {"label": "protected", "value": pii_protected},
                {"label": "not protected", "value": max(0, events - pii_protected)},
            ],
            "alerts_by_severity": _group_count(db, SecurityAlert.severity),
            "risk_distribution": [{"label": k, "value": v} for k, v in bands.items()],
        },
        "processing_success_rate": success_rate,
        "shield_events": _count(db, SecurityEvent),
        "source_status": source_status,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/pipeline")
def pipeline_overview(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Real per-stage counts for the Dashboard's pipeline story.

    Every number here is a direct DB query against the same tables the rest of
    the API uses - there is no separate/derived "pipeline state" store.
    """
    total_raw = _count(db, RawLog)
    processed = _count(db, RawLog, RawLog.status == RAW_STATUS_PROCESSED)
    invalid = _count(db, RawLog, RawLog.status == RAW_STATUS_INVALID)
    quarantined = _count(db, RawLog, RawLog.status == RAW_STATUS_QUARANTINED)
    duplicates = _count(db, RawLog, RawLog.status == RAW_STATUS_DUPLICATE)

    shield_safe = total_raw - _count(
        db, RawLog, RawLog.security_verdict.in_(["SUSPICIOUS", "WEAPONIZED_LOG"])
    )
    shield_suspicious = _count(db, RawLog, RawLog.security_verdict == "SUSPICIOUS")
    shield_weaponized = _count(db, RawLog, RawLog.security_verdict == "WEAPONIZED_LOG")

    events = _count(db, NormalizedEvent)
    ok_events = _count(db, NormalizedEvent, NormalizedEvent.processing_status == "ok")
    partial_events = _count(db, NormalizedEvent, NormalizedEvent.processing_status == "partial")
    error_events = _count(db, NormalizedEvent, NormalizedEvent.processing_status == "error")
    pii_protected = _count(db, NormalizedEvent, NormalizedEvent.pii_protected.is_(True))
    pii_row = db.get(PiiSetting, "default")

    sources_count = _count(db, LogSource)
    jobs_running = _count(db, ProcessingJob, ProcessingJob.status == "RUNNING")

    alerts_total = _count(db, SecurityAlert)
    alerts_new = _count(db, SecurityAlert, SecurityAlert.status == "NEW")
    avg_risk_row = db.execute(select(func.avg(SecurityAlert.risk_score))).scalar()
    avg_risk = round(avg_risk_row, 1) if avg_risk_row else 0.0
    # "correlated" = an alert whose related_event_ids span more than one event;
    # counted in Python (portable across SQLite/Postgres JSON representations).
    correlated_alerts = sum(
        1 for (rel,) in db.execute(select(SecurityAlert.related_event_ids)).all()
        if rel and len(rel) > 1
    )

    parser_breakdown = _group_count(db, NormalizedEvent.parser)

    nodes = [
        {"key": "sources", "label": "Log Sources", "count": sources_count,
         "status": "ok" if sources_count or total_raw else "idle",
         "detail": {"configured_sources": sources_count}},
        {"key": "ingestion", "label": "Ingestion", "count": total_raw,
         "status": "running" if jobs_running else ("ok" if total_raw else "idle"),
         "detail": {"jobs_running": jobs_running, "total_records": total_raw}},
        {"key": "detection", "label": "Security Shield", "count": total_raw,
         "status": "warn" if (shield_suspicious or shield_weaponized) else ("ok" if total_raw else "idle"),
         "detail": {"safe": max(0, shield_safe), "suspicious": shield_suspicious,
                    "weaponized": shield_weaponized}},
        {"key": "parsing", "label": "Parsing", "count": processed,
         "status": "ok" if processed else "idle",
         "detail": {"by_parser": parser_breakdown[:6]}},
        {"key": "cleaning", "label": "Cleaning & Validation", "count": invalid + duplicates,
         "status": "warn" if invalid else ("ok" if total_raw else "idle"),
         "detail": {"invalid": invalid, "duplicates": duplicates, "quarantined": quarantined}},
        {"key": "pii", "label": "PII Protection", "count": pii_protected,
         "status": "ok" if pii_row and pii_row.mode != "OFF" else "warn",
         "detail": {"mode": pii_row.mode if pii_row else "OFF", "protected_events": pii_protected}},
        {"key": "normalization", "label": "Normalization", "count": events,
         "status": "ok" if events else "idle",
         "detail": {"schema_version": "1.0"}},
        {"key": "validation", "label": "Validation", "count": ok_events,
         "status": "warn" if error_events else ("ok" if events else "idle"),
         "detail": {"ok": ok_events, "partial": partial_events, "error": error_events}},
        {"key": "correlation", "label": "Correlation", "count": correlated_alerts,
         "status": "ok" if correlated_alerts else "idle",
         "detail": {"alerts_with_related_events": correlated_alerts}},
        {"key": "risk", "label": "Risk Scoring", "count": alerts_total,
         "status": "warn" if avg_risk >= 65 else ("ok" if alerts_total else "idle"),
         "detail": {"avg_risk_score": avg_risk}},
        {"key": "alert", "label": "Alerts", "count": alerts_new,
         "status": "critical" if alerts_new else ("ok" if alerts_total else "idle"),
         "detail": {"total": alerts_total, "new": alerts_new}},
    ]
    return {"nodes": nodes, "generated_at": datetime.now(timezone.utc).isoformat()}


@router.get("/timeline")
def timeline(
    bucket: str = "hour",
    hours: int = 168,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    repo = EventRepository(db)
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = EventQuery(limit=1, time_from=since)
    return {"bucket": bucket, "series": repo.timeseries(q, bucket=bucket)}
