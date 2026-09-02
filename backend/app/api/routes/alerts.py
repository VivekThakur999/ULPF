from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_analyst
from app.core.database import get_db
from app.models.event import NormalizedEvent
from app.models.security import ALERT_STATUSES, SecurityAlert
from app.models.user import User
from app.schemas.event import EventOut
from app.schemas.logs import AlertDetailResponse, AlertListResponse, AlertOut, AlertUpdate
from app.services import audit
from app.services.correlation.engine import correlate

router = APIRouter()


@router.get("", response_model=AlertListResponse)
def list_alerts(
    status: str | None = None,
    severity: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(SecurityAlert)
    if status:
        q = q.filter(SecurityAlert.status == status.upper())
    if severity:
        q = q.filter(SecurityAlert.severity == severity.lower())
    total = q.count()
    rows = q.order_by(desc(SecurityAlert.risk_score), desc(SecurityAlert.ts)).offset(offset).limit(limit).all()
    return AlertListResponse(total=total, items=[AlertOut.model_validate(r) for r in rows])


@router.get("/{alert_id}", response_model=AlertDetailResponse)
def alert_detail(alert_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    alert = db.get(SecurityAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    entity = {k: v for k, v in alert.entity.items() if k in ("source_ip", "username", "host")}
    center = None
    if alert.entity.get("incident_center"):
        try:
            center = datetime.fromisoformat(alert.entity["incident_center"])
        except (TypeError, ValueError):
            center = None
    window = int(alert.entity.get("window_seconds") or 900) * 3

    corr = {}
    if entity:
        corr = correlate(db, center_time=center, window_seconds=window, **entity).to_dict()

    related = db.query(NormalizedEvent).filter(
        NormalizedEvent.id.in_(alert.related_event_ids[:200])
    ).order_by(NormalizedEvent.timestamp.asc()).all()

    # Build the incident timeline directly from the correlated event set so it is
    # always consistent with related_events (independent of wall-clock skew).
    timeline = corr.get("timeline") or [
        {
            "ts": e.timestamp.isoformat() if e.timestamp else None,
            "event_id": e.id, "source": e.source, "host": e.host,
            "event_type": e.event_type, "action": e.action, "status": e.status,
            "severity": e.severity,
            "summary": _event_summary(e),
        }
        for e in related
    ]

    return AlertDetailResponse(
        alert=AlertOut.model_validate(alert),
        timeline=timeline,
        related_events=[EventOut.model_validate(e) for e in related],
        correlation=corr,
    )


def _event_summary(e: NormalizedEvent) -> str:
    bits = []
    if e.event_type:
        bits.append(e.event_type.replace("_", " "))
    if e.username:
        bits.append(f"user {e.username}")
    if e.source_ip:
        bits.append(f"from {e.source_ip}")
    if e.destination_port:
        bits.append(f"port {e.destination_port}")
    if e.response_code:
        bits.append(f"HTTP {e.response_code}")
    return " ".join(bits) or (e.message[:120] if e.message else "event")


@router.put("/{alert_id}", response_model=AlertOut)
def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst),
):
    alert = db.get(SecurityAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if payload.status is not None:
        if payload.status.upper() not in ALERT_STATUSES:
            raise HTTPException(status_code=422, detail=f"status must be one of {ALERT_STATUSES}")
        alert.status = payload.status.upper()
        alert.acknowledged_by = analyst.id
    if payload.resolution_note is not None:
        alert.resolution_note = payload.resolution_note
    alert.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    audit.record(db, action="alert.update", actor=analyst, target_type="alert",
                 target_id=alert.id, detail=f"status={alert.status}",
                 ip_address=request.client.host if request.client else None)
    return AlertOut.model_validate(alert)
