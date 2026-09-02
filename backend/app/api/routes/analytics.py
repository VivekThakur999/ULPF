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
