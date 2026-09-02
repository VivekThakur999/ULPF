from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_admin, require_analyst
from app.core.database import get_db
from app.models.security import SecurityRule
from app.models.user import User
from app.services import audit
from app.services.correlation.engine import correlate
from app.services.security.detection import run_detection

router = APIRouter()


class DetectionRunRequest(BaseModel):
    since_hours: int = 24
    job_id: str | None = None


@router.post("/run")
def run(
    body: DetectionRunRequest,
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst),
):
    since = datetime.now(timezone.utc) - timedelta(hours=max(1, min(body.since_hours, 720)))
    alerts = run_detection(db, since=since, job_id=body.job_id)
    audit.record(db, action="detection.run", actor=analyst,
                 detail=f"since_hours={body.since_hours} alerts={len(alerts)}",
                 ip_address=request.client.host if request.client else None)
    return {
        "alerts_created_or_updated": len(alerts),
        "alerts": [{"id": a.id, "title": a.title, "severity": a.severity,
                    "risk_score": a.risk_score, "status": a.status} for a in alerts],
    }


class RuleOut(BaseModel):
    rule_key: str
    name: str
    description: str
    severity: str
    threshold: int
    window_seconds: int
    enabled: bool
    params: dict

    class Config:
        from_attributes = True


class RuleUpdate(BaseModel):
    enabled: bool | None = None
    threshold: int | None = None
    window_seconds: int | None = None
    severity: str | None = None


@router.get("/rules", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.execute(select(SecurityRule).order_by(SecurityRule.rule_key)).scalars().all()


@router.put("/rules/{rule_key}", response_model=RuleOut)
def update_rule(
    rule_key: str,
    payload: RuleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    rule = db.execute(
        select(SecurityRule).where(SecurityRule.rule_key == rule_key)
    ).scalars().first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    audit.record(db, action="rule.update", actor=admin, target_type="security_rule",
                 target_id=rule_key, detail=payload.model_dump(exclude_unset=True).__repr__(),
                 ip_address=request.client.host if request.client else None)
    return rule


class CorrelateRequest(BaseModel):
    source_ip: str | None = None
    username: str | None = None
    host: str | None = None
    center_time: datetime | None = None
    window_seconds: int = 900


@router.post("/correlate")
def correlate_entity(
    body: CorrelateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not any([body.source_ip, body.username, body.host]):
        raise HTTPException(status_code=422, detail="provide source_ip, username or host")
    result = correlate(
        db, source_ip=body.source_ip, username=body.username, host=body.host,
        center_time=body.center_time, window_seconds=body.window_seconds,
    )
    return result.to_dict()
