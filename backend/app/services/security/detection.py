"""Detection orchestration: RuleHits -> correlated, risk-scored SecurityAlerts."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.event import NormalizedEvent
from app.models.security import ALERT_NEW, SecurityAlert
from app.services.analytics.risk import RiskContext, compute_risk
from app.services.correlation.engine import correlate
from app.services.security.rules import RuleHit, evaluate_rules

log = get_logger("detection")

_SEV_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _entity_group_key(hit: RuleHit) -> tuple[str, str]:
    for field in ("source_ip", "username", "host", "source"):
        if field in hit.entity:
            return field, str(hit.entity[field])
    k, v = next(iter(hit.entity.items()))
    return k, str(v)


def _recommended_response(entity_field: str, entity_value: str, band: str) -> dict:
    if entity_field == "source_ip":
        action = "block_source_ip"
        label = f"Block source IP {entity_value} at the perimeter firewall"
    elif entity_field == "username":
        action = "disable_account"
        label = f"Temporarily disable account {entity_value} and force credential reset"
    elif entity_field == "host":
        action = "isolate_host"
        label = f"Isolate host {entity_value} for investigation"
    else:
        action = "review_source"
        label = f"Review the '{entity_value}' log source configuration and upstream device"
    return {
        "action": action,
        "label": label,
        "target": {entity_field: entity_value},
        "auto_execute": False,
        "note": "MVP only recommends/simulates. Requires SOC approval; no live enforcement.",
        "urgency": band,
    }


def _max_event_severity(db: Session, event_ids: list[str]) -> str | None:
    if not event_ids:
        return None
    rows = db.execute(
        select(NormalizedEvent.severity).where(NormalizedEvent.id.in_(event_ids[:500]))
    ).scalars().all()
    best = None
    for s in rows:
        if s and (best is None or _SEV_RANK.get(s, 0) > _SEV_RANK.get(best, 0)):
            best = s
    return best


def run_detection(
    db: Session,
    *,
    since: datetime | None = None,
    job_id: str | None = None,
) -> list[SecurityAlert]:
    hits = evaluate_rules(db, since=since, job_id=job_id)
    if not hits:
        return []

    raw_groups: dict[tuple[str, str], list[RuleHit]] = {}
    for h in hits:
        raw_groups.setdefault(_entity_group_key(h), []).append(h)

    # Merge groups that describe the same incident (heavy event overlap) into the
    # highest-priority entity, so one attack yields one consolidated alert.
    _PRIORITY = {"source_ip": 0, "host": 1, "username": 2, "source": 3}
    ordered = sorted(raw_groups.items(),
                     key=lambda kv: _PRIORITY.get(kv[0][0], 9))
    groups: dict[tuple[str, str], list[RuleHit]] = {}
    claimed: list[set[str]] = []
    for key, group in ordered:
        ev = {eid for h in group for eid in h.event_ids if eid}
        merged = False
        for i, (gkey) in enumerate(list(groups.keys())):
            prev = claimed[i]
            if ev and prev and len(ev & prev) / len(ev) >= 0.6:
                groups[gkey].extend(group)
                claimed[i] |= ev
                merged = True
                break
        if not merged:
            groups[key] = list(group)
            claimed.append(ev)

    alerts: list[SecurityAlert] = []
    for (entity_field, entity_value), group in groups.items():
        lead = max(group, key=lambda h: _SEV_RANK.get(h.severity, 0))
        centers = [h.center_time for h in group if h.center_time]
        center = min(centers) if centers else datetime.now(timezone.utc)
        max_window = max((h.window_seconds for h in group), default=300)

        corr_kwargs = {entity_field: entity_value} if entity_field in (
            "source_ip", "username", "host") else {}
        if corr_kwargs:
            corr = correlate(db, center_time=center, window_seconds=max_window * 3,
                             **corr_kwargs)
            corr_dict = corr.to_dict()
            all_event_ids = corr.event_ids
            hosts = corr.hosts
        else:
            corr_dict = {"focus": {entity_field: entity_value}, "timeline": [],
                         "sources": [], "hosts": [], "counts": {}}
            all_event_ids = sorted({eid for h in group for eid in h.event_ids})
            hosts = sorted({hh for h in group for hh in h.hosts})

        counts = corr_dict.get("counts", {})
        success_after = any(h.metrics.get("success_after_failures") for h in group)
        shield_verdict = next(
            (h.metrics.get("shield_verdict") for h in group if h.metrics.get("shield_verdict")),
            None,
        )
        rctx = RiskContext(
            failed_logins=max((h.metrics.get("failed_logins", 0) for h in group), default=0)
            or counts.get("auth_failures", 0),
            successful_logins=counts.get("auth_successes", 0),
            affected_hosts=len(hosts),
            distinct_sources=counts.get("sources", 0) or len(corr_dict.get("sources", [])),
            distinct_usernames=len({u for h in group for u in h.usernames}),
            span_seconds=counts.get("span_seconds"),
            total_events=counts.get("events", len(all_event_ids)),
            max_event_severity=_max_event_severity(db, all_event_ids),
            shield_verdict=shield_verdict,
            success_after_failures=success_after,
            connections_denied=counts.get("connections_denied", 0),
            rule_severity=lead.severity,
        )
        risk = compute_risk(rctx)

        rule_keys = sorted({h.rule_key for h in group})
        # dedup on the entity alone so re-runs update (not duplicate) the alert
        dedup_key = f"{entity_field}={entity_value}"
        title = _title(lead, entity_field, entity_value)
        reason = " ".join(h.reason for h in sorted(group, key=lambda x: x.rule_key))

        existing = db.execute(
            select(SecurityAlert).where(SecurityAlert.dedup_key == dedup_key)
        ).scalars().first()

        payload = dict(
            title=title,
            severity=_blend_severity(lead.severity, risk.band),
            risk_score=risk.score,
            source="correlation-engine",
            rule_key=lead.rule_key,
            description=(f"Triggered rules: {', '.join(rule_keys)}. "
                         f"Entity {entity_field}={entity_value}."),
            reason=reason,
            risk_breakdown=risk.to_dict(),
            entity={entity_field: entity_value, "type": entity_field,
                    "incident_center": center.isoformat() if center else None,
                    "window_seconds": max_window},
            related_event_ids=all_event_ids[:500],
            affected_hosts=hosts,
            recommended_response=_recommended_response(entity_field, entity_value, risk.band),
        )

        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
            existing.updated_at = datetime.now(timezone.utc)
            alerts.append(existing)
        else:
            alert = SecurityAlert(dedup_key=dedup_key, status=ALERT_NEW, **payload)
            db.add(alert)
            alerts.append(alert)

    db.commit()
    for a in alerts:
        db.refresh(a)
    log.info("detection produced %d alert(s) from %d hit(s)", len(alerts), len(hits))
    return alerts


def _title(lead: RuleHit, field: str, value: str) -> str:
    base = {
        "RULE_1": "Multiple failed logins",
        "RULE_2": "Possible brute-force activity",
        "RULE_3": "Credential spraying across hosts",
        "RULE_4": "Unusual authentication frequency",
        "RULE_5": "Suspicious connection-then-auth sequence",
        "RULE_6": "Successful login after repeated failures",
        "RULE_7": "Weaponized / injection log payload detected",
        "RULE_8": "Abnormal event burst",
    }.get(lead.rule_key, lead.rule_name)
    if field in ("source_ip", "username", "host"):
        return f"{base} ({field.replace('_', ' ')} {value})"
    return f"{base} (source {value})"


def _blend_severity(rule_sev: str, risk_band: str) -> str:
    return rule_sev if _SEV_RANK.get(rule_sev, 0) >= _SEV_RANK.get(risk_band, 0) else risk_band
