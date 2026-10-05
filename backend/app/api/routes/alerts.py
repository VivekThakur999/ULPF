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
    from app.core.config import settings

    if settings.use_mongodb:
        try:
            from app.repositories.mongodb.alerts import MongoAlertRepository

            mongo_alerts = MongoAlertRepository()
            total, items = mongo_alerts.list_alerts(status=status, severity=severity, limit=limit, offset=offset)
            return AlertListResponse(total=total, items=[AlertOut.model_validate(r) for r in items])
        except Exception:
            pass

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
    from app.core.config import settings
    from app.repositories.events import EventQuery, EventRepository

    alert_obj = None
    if settings.use_mongodb:
        try:
            from app.repositories.mongodb.alerts import MongoAlertRepository

            alert_obj = MongoAlertRepository().get_alert(alert_id)
        except Exception:
            pass

    if alert_obj is None:
        alert_obj = db.get(SecurityAlert, alert_id)
        if not alert_obj:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert_out = AlertOut.model_validate(alert_obj)
        entity = {k: v for k, v in (alert_obj.entity or {}).items() if k in ("source_ip", "username", "host")}
        center = None
        if alert_obj.entity and alert_obj.entity.get("incident_center"):
            try:
                center = datetime.fromisoformat(alert_obj.entity["incident_center"])
            except (TypeError, ValueError):
                center = None
        window = int((alert_obj.entity or {}).get("window_seconds") or 900) * 3
        rel_ids = (alert_obj.related_event_ids or [])[:200]
    else:
        alert_out = AlertOut.model_validate(alert_obj)
        entity_dict = alert_obj.get("entity") or {}
        entity = {k: v for k, v in entity_dict.items() if k in ("source_ip", "username", "host")}
        center = None
        if entity_dict.get("incident_center"):
            try:
                center = datetime.fromisoformat(entity_dict["incident_center"])
            except (TypeError, ValueError):
                center = None
        window = int(entity_dict.get("window_seconds") or 900) * 3
        rel_ids = (alert_obj.get("related_event_ids") or [])[:200]

    corr = {}
    if entity:
        corr = correlate(db, center_time=center, window_seconds=window, **entity).to_dict()

    event_repo = EventRepository(db)
    if rel_ids:
        rel_page = event_repo.search(EventQuery(fields_in={"id": rel_ids}, limit=len(rel_ids), order="asc"))
        related = rel_page.items
    else:
        related = []

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
        alert=alert_out,
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

    from app.core.config import settings

    if settings.use_mongodb:
        try:
            from app.repositories.mongodb.alerts import MongoAlertRepository

            mongo_alerts = MongoAlertRepository()
            mongo_alerts.update_alert(alert.id, {
                "status": alert.status,
                "acknowledged_by": alert.acknowledged_by,
                "resolution_note": alert.resolution_note,
                "updated_at": alert.updated_at,
            })
        except Exception as exc:
            pass

    audit.record(db, action="alert.update", actor=analyst, target_type="alert",
                 target_id=alert.id, detail=f"status={alert.status}",
                 ip_address=request.client.host if request.client else None)
    return AlertOut.model_validate(alert)
