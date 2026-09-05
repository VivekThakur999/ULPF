from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_analyst
from app.core.database import get_db
from app.models.response import ResponseSimulation
from app.models.security import SecurityAlert
from app.models.user import User
from app.schemas.response import (
    RecommendResponse,
    SimulateRequest,
    SimulateResponse,
    SimulationRecordOut,
)
from app.services import audit
from app.services.response.service import recommend_for_alert, run_simulation

router = APIRouter()


def _load_alert(db: Session, alert_id: str) -> SecurityAlert:
    alert = db.get(SecurityAlert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/recommend/{alert_id}", response_model=RecommendResponse)
def recommend_endpoint(
    alert_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    alert = _load_alert(db, alert_id)
    rec, ev = recommend_for_alert(db, alert)
    return RecommendResponse(
        alert=ev["alert"], recommendation=rec.to_dict(),
        evidence={"entity": ev["entity"], "rule_keys": ev["rule_keys"],
                  "counts": ev["counts"], "shield_verdicts": ev["shield_verdicts"]},
    )


@router.post("/simulate", response_model=SimulateResponse)
def simulate_endpoint(
    payload: SimulateRequest,
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst),
):
    alert = _load_alert(db, payload.alert_id)
    row = run_simulation(db, alert, analyst)

    audit.record(
        db, action="response.simulate", actor=analyst,
        target_type="alert", target_id=alert.id,
        detail=f"SIMULATION_ONLY category={row.recommendation.get('category')} "
               f"actions={[a['action'] for a in row.actions]}",
        ip_address=request.client.host if request.client else None,
    )

    return SimulateResponse(
        simulation=True,
        disclaimer=row.notes,
        audit_id=row.id,
        alert={
            "id": alert.id, "title": alert.title, "severity": alert.severity,
            "risk_score": alert.risk_score, "rule_key": alert.rule_key,
            "reason": alert.reason, "status": alert.status,
        },
        recommendation=row.recommendation,
        actions=row.actions,
        result=row.result,
        evidence=row.evidence,
    )


@router.get("/simulations", response_model=list[SimulationRecordOut])
def list_simulations(
    alert_id: str | None = None,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(ResponseSimulation).order_by(desc(ResponseSimulation.ts)).limit(limit)
    if alert_id:
        stmt = stmt.where(ResponseSimulation.alert_id == alert_id)
    return db.execute(stmt).scalars().all()
