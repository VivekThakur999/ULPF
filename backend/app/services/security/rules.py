"""Deterministic rule-based suspicious-activity detection (Module 15).

Each rule is a pure function over the recently-ingested normalized events. No
ML, no randomness - every hit is explainable and reproducible.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import NormalizedEvent
from app.models.security import SecurityEvent, SecurityRule


@dataclass
class RuleHit:
    rule_key: str
    rule_name: str
    severity: str
    entity: dict
    reason: str
    event_ids: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    usernames: list[str] = field(default_factory=list)
    center_time: datetime | None = None
    window_seconds: int = 300
    metrics: dict = field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        ent = ",".join(f"{k}={v}" for k, v in sorted(self.entity.items()))
        return f"{self.rule_key}|{ent}"


def _window_max_count(times: list[datetime], window: int) -> tuple[int, datetime | None]:
    """Largest number of timestamps falling within any `window`-second span."""
    if not times:
        return 0, None
    ts = sorted(times)
    best, best_center = 0, None
    j = 0
    for i in range(len(ts)):
        while (ts[i] - ts[j]).total_seconds() > window:
            j += 1
        count = i - j + 1
        if count > best:
            best = count
            best_center = ts[j] + (ts[i] - ts[j]) / 2
    return best, best_center


def _load_events(db: Session, since: datetime, job_id: str | None) -> list[NormalizedEvent]:
    stmt = select(NormalizedEvent).where(NormalizedEvent.ingested_at >= since)
    if job_id:
        stmt = stmt.where(NormalizedEvent.job_id == job_id)
    return list(db.execute(stmt).scalars().all())


# --- individual rules --------------------------------------------------------

def _rule_failed_from_source(events, rule: SecurityRule) -> list[RuleHit]:
    by_ip: dict[str, list[NormalizedEvent]] = defaultdict(list)
    for e in events:
        if e.event_type == "authentication_failure" and e.source_ip:
            by_ip[e.source_ip].append(e)
    hits = []
    for ip, evs in by_ip.items():
        times = [e.timestamp for e in evs if e.timestamp]
        count, center = _window_max_count(times, rule.window_seconds)
        count = max(count, len(evs) if not times else count)
        if count >= rule.threshold:
            hosts = sorted({e.host for e in evs if e.host})
            users = sorted({e.username for e in evs if e.username})
            hits.append(RuleHit(
                rule_key=rule.rule_key, rule_name=rule.name, severity=rule.severity,
                entity={"source_ip": ip},
                reason=(f"{count} failed authentication attempts from {ip} within "
                        f"{rule.window_seconds}s (threshold {rule.threshold})."),
                event_ids=[e.id for e in evs], hosts=hosts, usernames=users,
                center_time=center or (times[0] if times else None),
                window_seconds=rule.window_seconds,
                metrics={"failed_logins": len(evs), "window_peak": count},
            ))
    return hits


def _rule_bruteforce(events, rule: SecurityRule) -> list[RuleHit]:
    by_key: dict[tuple, list[NormalizedEvent]] = defaultdict(list)
    for e in events:
        if e.event_type == "authentication_failure" and e.source_ip:
            by_key[(e.source_ip, e.host or "?")].append(e)
    hits = []
    for (ip, host), evs in by_key.items():
        times = [e.timestamp for e in evs if e.timestamp]
        count, center = _window_max_count(times, rule.window_seconds)
        count = max(count, len(evs) if not times else count)
        if count >= rule.threshold:
            hits.append(RuleHit(
                rule_key=rule.rule_key, rule_name=rule.name, severity=rule.severity,
                entity={"source_ip": ip, "host": host},
                reason=(f"Sustained brute-force pattern: {count} failures from {ip} "
                        f"against {host} within {rule.window_seconds}s."),
                event_ids=[e.id for e in evs], hosts=[host],
                usernames=sorted({e.username for e in evs if e.username}),
                center_time=center, window_seconds=rule.window_seconds,
                metrics={"failed_logins": len(evs), "window_peak": count},
            ))
    return hits


def _rule_multi_host(events, rule: SecurityRule) -> list[RuleHit]:
    need = int((rule.params or {}).get("distinct_hosts", 3))
    by_ip: dict[str, list[NormalizedEvent]] = defaultdict(list)
    for e in events:
        if e.event_type == "authentication_failure" and e.source_ip and e.host:
            by_ip[e.source_ip].append(e)
    hits = []
    for ip, evs in by_ip.items():
        hosts = sorted({e.host for e in evs})
        if len(hosts) >= need:
            times = [e.timestamp for e in evs if e.timestamp]
            _, center = _window_max_count(times, rule.window_seconds)
            hits.append(RuleHit(
                rule_key=rule.rule_key, rule_name=rule.name, severity=rule.severity,
                entity={"source_ip": ip},
                reason=(f"{ip} produced authentication failures against {len(hosts)} "
                        f"distinct hosts ({', '.join(hosts)})."),
                event_ids=[e.id for e in evs], hosts=hosts,
                usernames=sorted({e.username for e in evs if e.username}),
                center_time=center or (times[0] if times else None),
                window_seconds=rule.window_seconds,
                metrics={"failed_logins": len(evs), "distinct_hosts": len(hosts)},
            ))
    return hits


def _rule_login_frequency(events, rule: SecurityRule) -> list[RuleHit]:
    by_user: dict[str, list[NormalizedEvent]] = defaultdict(list)
    for e in events:
        if e.event_type in ("authentication_failure", "authentication_success") and e.username:
            by_user[e.username].append(e)
    hits = []
    for user, evs in by_user.items():
        times = [e.timestamp for e in evs if e.timestamp]
        count, center = _window_max_count(times, rule.window_seconds)
        count = max(count, len(evs) if not times else count)
        if count >= rule.threshold:
            hits.append(RuleHit(
                rule_key=rule.rule_key, rule_name=rule.name, severity=rule.severity,
                entity={"username": user},
                reason=(f"Account '{user}' saw {count} authentication attempts within "
                        f"{rule.window_seconds}s (threshold {rule.threshold})."),
                event_ids=[e.id for e in evs],
                hosts=sorted({e.host for e in evs if e.host}),
                usernames=[user], center_time=center,
                window_seconds=rule.window_seconds,
                metrics={"attempts": len(evs), "window_peak": count},
            ))
    return hits


def _rule_conn_then_auth(events, rule: SecurityRule) -> list[RuleHit]:
    by_ip_denied: dict[str, list[datetime]] = defaultdict(list)
    by_ip_authfail: dict[str, list[NormalizedEvent]] = defaultdict(list)
    for e in events:
        if e.source_ip and e.timestamp:
            if e.event_type == "connection_denied":
                by_ip_denied[e.source_ip].append(e.timestamp)
            elif e.event_type == "authentication_failure":
                by_ip_authfail[e.source_ip].append(e)
    hits = []
    for ip, fails in by_ip_authfail.items():
        denials = by_ip_denied.get(ip)
        if not denials:
            continue
        d0 = min(denials)
        related = [e for e in fails if e.timestamp and
                   0 <= (e.timestamp - d0).total_seconds() <= rule.window_seconds * 4]
        if related:
            hits.append(RuleHit(
                rule_key=rule.rule_key, rule_name=rule.name, severity=rule.severity,
                entity={"source_ip": ip},
                reason=(f"{ip} was denied at the firewall and then produced "
                        f"{len(related)} authentication failure(s) shortly after."),
                event_ids=[e.id for e in related], hosts=sorted({e.host for e in related if e.host}),
                usernames=sorted({e.username for e in related if e.username}),
                center_time=d0, window_seconds=rule.window_seconds,
                metrics={"denials": len(denials), "followon_auth_failures": len(related)},
            ))
    return hits


def _rule_fail_then_success(events, rule: SecurityRule) -> list[RuleHit]:
    hits = []
    for key_field in ("source_ip", "username"):
        groups: dict[str, list[NormalizedEvent]] = defaultdict(list)
        for e in events:
            v = getattr(e, key_field)
            if v and e.event_type in ("authentication_failure", "authentication_success"):
                groups[v].append(e)
        for val, evs in groups.items():
            evs_t = sorted([e for e in evs if e.timestamp], key=lambda e: e.timestamp)
            fails, first_fail = 0, None
            for e in evs_t:
                if e.event_type == "authentication_failure":
                    fails += 1
                    first_fail = first_fail or e.timestamp
                elif e.event_type == "authentication_success" and fails >= rule.threshold:
                    hits.append(RuleHit(
                        rule_key=rule.rule_key, rule_name=rule.name, severity=rule.severity,
                        entity={key_field: val},
                        reason=(f"{fails} failed authentications for {key_field}={val} were "
                                f"followed by a SUCCESSFUL login - possible credential "
                                f"compromise."),
                        event_ids=[x.id for x in evs_t],
                        hosts=sorted({x.host for x in evs_t if x.host}),
                        usernames=sorted({x.username for x in evs_t if x.username}),
                        center_time=e.timestamp, window_seconds=rule.window_seconds,
                        metrics={"failures_before_success": fails,
                                 "success_after_failures": True},
                    ))
                    break
    return hits


def _rule_injection_payload(events, rule: SecurityRule, db: Session, since: datetime) -> list[RuleHit]:
    rows = db.execute(
        select(SecurityEvent).where(
            SecurityEvent.ts >= since,
            SecurityEvent.verdict.in_(["SUSPICIOUS", "WEAPONIZED_LOG"]),
        )
    ).scalars().all()
    if not rows:
        return []
    by_source: dict[str, list[SecurityEvent]] = defaultdict(list)
    for r in rows:
        by_source[r.source or "unknown"].append(r)
    hits = []
    for src, evs in by_source.items():
        weap = sum(1 for e in evs if e.verdict == "WEAPONIZED_LOG")
        sev = "critical" if weap else rule.severity
        hits.append(RuleHit(
            rule_key=rule.rule_key, rule_name=rule.name, severity=sev,
            entity={"source": src},
            reason=(f"Security Shield flagged {len(evs)} log record(s) from '{src}' "
                    f"({weap} weaponized) - "
                    f"{', '.join(sorted({e.detection_type for e in evs}))}."),
            event_ids=[e.raw_reference for e in evs if e.raw_reference],
            center_time=min(e.ts for e in evs),
            window_seconds=rule.window_seconds,
            metrics={"shield_events": len(evs), "weaponized": weap,
                     "shield_verdict": "WEAPONIZED_LOG" if weap else "SUSPICIOUS"},
        ))
    return hits


def _rule_event_burst(events, rule: SecurityRule) -> list[RuleHit]:
    by_source: dict[str, list[datetime]] = defaultdict(list)
    for e in events:
        if e.timestamp:
            by_source[e.source].append(e.timestamp)
    hits = []
    for src, times in by_source.items():
        count, center = _window_max_count(times, rule.window_seconds)
        if count >= rule.threshold:
            hits.append(RuleHit(
                rule_key=rule.rule_key, rule_name=rule.name, severity=rule.severity,
                entity={"source": src},
                reason=(f"Event burst: {count} events from '{src}' within "
                        f"{rule.window_seconds}s (threshold {rule.threshold})."),
                event_ids=[e.id for e in events if e.source == src][:500],
                center_time=center, window_seconds=rule.window_seconds,
                metrics={"burst_peak": count},
            ))
    return hits


_RULE_FUNCS = {
    "RULE_1": _rule_failed_from_source,
    "RULE_2": _rule_bruteforce,
    "RULE_3": _rule_multi_host,
    "RULE_4": _rule_login_frequency,
    "RULE_5": _rule_conn_then_auth,
    "RULE_6": _rule_fail_then_success,
    "RULE_8": _rule_event_burst,
}


def evaluate_rules(
    db: Session, *, since: datetime | None = None, job_id: str | None = None
) -> list[RuleHit]:
    since = since or (datetime.now(timezone.utc) - timedelta(hours=24))
    events = _load_events(db, since, job_id)
    rules = {r.rule_key: r for r in db.execute(select(SecurityRule)).scalars().all()}

    hits: list[RuleHit] = []
    for key, rule in rules.items():
        if not rule.enabled:
            continue
        if key == "RULE_7":
            hits.extend(_rule_injection_payload(events, rule, db, since))
        elif key in _RULE_FUNCS:
            hits.extend(_RULE_FUNCS[key](events, rule))
    return hits
