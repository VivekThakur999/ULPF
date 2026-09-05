"""Response-simulation orchestration: real alert evidence -> deterministic
recommendation -> in-memory simulation -> persisted SIMULATION_ONLY record.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.event import NormalizedEvent
from app.models.response import ResponseSimulation
from app.models.security import SecurityAlert, SecurityEvent
from app.models.user import User
from app.services.correlation.engine import correlate
from app.services.response.recommend import Recommendation, recommend
from app.services.response.simulate import DISCLAIMER, simulate_all

log = get_logger("response")


def _alert_projection(alert: SecurityAlert) -> dict[str, Any]:
    return {
        "id": alert.id,
        "title": alert.title,
        "severity": alert.severity,
        "risk_score": alert.risk_score,
        "risk_band": (alert.risk_breakdown or {}).get("band"),
        "rule_key": alert.rule_key,
        "reason": alert.reason,
        "status": alert.status,
        "entity": alert.entity,
        "affected_hosts": alert.affected_hosts,
        "ts": alert.ts.isoformat() if alert.ts else None,
    }


def build_evidence(db: Session, alert: SecurityAlert) -> dict[str, Any]:
    """Everything the recommendation engine needs - retrieved server-side only."""
    entity = {k: v for k, v in (alert.entity or {}).items()
              if k in ("source_ip", "username", "host")}
    rule_keys = []
    if alert.rule_key:
        rule_keys.append(alert.rule_key)
    # the alert description records every rule that contributed
    for token in (alert.description or "").replace(",", " ").split():
        if token.startswith("RULE_") and token.strip(".") not in rule_keys:
            rule_keys.append(token.strip("."))

    center = None
    if (alert.entity or {}).get("incident_center"):
        try:
            center = datetime.fromisoformat(alert.entity["incident_center"])
        except (TypeError, ValueError):
            center = None
    corr = {}
    if entity:
        corr = correlate(db, center_time=center, window_seconds=3600, **entity).to_dict()

    related = db.execute(
        select(NormalizedEvent).where(
            NormalizedEvent.id.in_((alert.related_event_ids or [])[:200])
        )
    ).scalars().all()
    dest_ports = Counter(str(e.destination_port) for e in related if e.destination_port)
    protocols = Counter(e.protocol for e in related if e.protocol)

    shield = db.execute(
        select(SecurityEvent.verdict).where(
            SecurityEvent.raw_reference.in_([e.raw_log_id for e in related if e.raw_log_id])
        )
    ).scalars().all()

    return {
        "alert": _alert_projection(alert),
        "entity": entity,
        "rule_keys": rule_keys,
        "correlation": {
            **corr,
            "dest_ports": dict(dest_ports),
            "protocols": {str(k): v for k, v in protocols.items()},
        },
        "counts": corr.get("counts", {}),
        "shield_verdicts": sorted(set(shield)),
    }


def recommend_for_alert(db: Session, alert: SecurityAlert) -> tuple[Recommendation, dict]:
    ev = build_evidence(db, alert)
    rec = recommend(
        rule_keys=ev["rule_keys"], entity=ev["entity"],
        correlation=ev["correlation"], counts=ev["counts"],
        shield_verdicts=ev["shield_verdicts"],
    )
    return rec, ev


def run_simulation(db: Session, alert: SecurityAlert, actor: User) -> ResponseSimulation:
    rec, ev = recommend_for_alert(db, alert)
    result = simulate_all(rec.actions)

    row = ResponseSimulation(
        ts=datetime.now(timezone.utc),
        actor_id=actor.id, actor_email=actor.email,
        alert_id=alert.id, alert_title=alert.title, alert_rule_key=alert.rule_key,
        alert_severity=alert.severity, alert_risk_score=alert.risk_score,
        recommendation=rec.to_dict(),
        actions=[a.to_dict() for a in rec.actions],
        result=result,
        evidence={"entity": ev["entity"], "rule_keys": ev["rule_keys"],
                  "counts": ev["counts"], "shield_verdicts": ev["shield_verdicts"]},
        notes=DISCLAIMER,
        simulation_only=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log.info("response simulation %s for alert %s by %s (%s) - SIMULATION ONLY",
             row.id, alert.id, actor.email, rec.category)
    return row
