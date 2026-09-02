from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.database import get_db
from app.models.security import SecurityEvent
from app.models.user import User
from app.services.security.shield import screen_line

router = APIRouter()


class ShieldCheckRequest(BaseModel):
    line: str = Field(min_length=1, max_length=64_000)


@router.post("/shield/check")
def shield_check(payload: ShieldCheckRequest, _: User = Depends(get_current_user)):
    """Run the Security Shield on a single line without ingesting it."""
    return screen_line(payload.line).to_dict()


@router.get("/events")
def list_events(
    verdict: str | None = None,
    job_id: str | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(SecurityEvent)
    if verdict:
        q = q.filter(SecurityEvent.verdict == verdict.upper())
    if job_id:
        q = q.filter(SecurityEvent.job_id == job_id)
    total = q.count()
    rows = q.order_by(desc(SecurityEvent.ts)).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "ts": r.ts,
                "event_type": r.event_type,
                "detection_type": r.detection_type,
                "source": r.source,
                "severity": r.severity,
                "verdict": r.verdict,
                "raw_reference": r.raw_reference,
                "job_id": r.job_id,
                "reason": r.reason,
                "indicators": r.indicators,
            }
            for r in rows
        ],
    }
