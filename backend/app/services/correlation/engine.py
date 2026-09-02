"""Cross-source correlation engine (Module 14).

Given a focus entity (pseudonymized IP / username / host) and a time window,
gather every normalized event that touches that entity across all sources and
assemble a single ordered timeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.event import NormalizedEvent


@dataclass
class TimelineEntry:
    ts: datetime | None
    event_id: str
    source: str
    host: str | None
    event_type: str | None
    action: str | None
    status: str | None
    severity: str | None
    summary: str

    def to_dict(self) -> dict:
        return {
            "ts": self.ts.isoformat() if self.ts else None,
            "event_id": self.event_id,
            "source": self.source,
            "host": self.host,
            "event_type": self.event_type,
            "action": self.action,
            "status": self.status,
            "severity": self.severity,
            "summary": self.summary,
        }


@dataclass
class CorrelationResult:
    focus: dict
    window: dict
    timeline: list[TimelineEntry] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    usernames: list[str] = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    event_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "focus": self.focus,
            "window": self.window,
            "timeline": [t.to_dict() for t in self.timeline],
            "sources": self.sources,
            "hosts": self.hosts,
            "usernames": self.usernames,
            "counts": self.counts,
            "event_ids": self.event_ids,
        }


def _summary(e: NormalizedEvent) -> str:
    bits = []
    if e.event_type:
        bits.append(e.event_type.replace("_", " "))
    if e.username:
        bits.append(f"user {e.username}")
    if e.source_ip:
        bits.append(f"from {e.source_ip}")
    if e.destination_ip:
        bits.append(f"to {e.destination_ip}")
    if e.destination_port:
        bits.append(f"port {e.destination_port}")
    if e.response_code:
        bits.append(f"HTTP {e.response_code}")
    return " ".join(bits) or (e.message[:120] if e.message else "event")


def correlate(
    db: Session,
    *,
    source_ip: str | None = None,
    username: str | None = None,
    host: str | None = None,
    center_time: datetime | None = None,
    window_seconds: int = 600,
    max_events: int = 500,
) -> CorrelationResult:
    E = NormalizedEvent
    filters = []
    focus: dict = {}
    if source_ip:
        filters.append(or_(E.source_ip == source_ip, E.destination_ip == source_ip))
        focus["source_ip"] = source_ip
    if username:
        filters.append(E.username == username)
        focus["username"] = username
    if host:
        filters.append(E.host == host)
        focus["host"] = host
    if not filters:
        raise ValueError("correlate() needs at least one focus entity")

    stmt = select(E).where(or_(*filters))
    if center_time:
        lo = center_time - timedelta(seconds=window_seconds)
        hi = center_time + timedelta(seconds=window_seconds)
        stmt = stmt.where(or_(E.timestamp.is_(None), E.timestamp.between(lo, hi)))
        window = {"start": lo.isoformat(), "end": hi.isoformat(), "seconds": window_seconds}
    else:
        window = {"start": None, "end": None, "seconds": window_seconds}

    rows = db.execute(stmt.order_by(E.timestamp.asc().nulls_last()
                                    if db.bind and db.bind.dialect.name != "sqlite"
                                    else E.timestamp.asc()).limit(max_events)).scalars().all()

    timeline = [
        TimelineEntry(
            ts=e.timestamp, event_id=e.id, source=e.source, host=e.host,
            event_type=e.event_type, action=e.action, status=e.status,
            severity=e.severity, summary=_summary(e),
        )
        for e in rows
    ]

    sources = sorted({e.source for e in rows if e.source})
    hosts = sorted({e.host for e in rows if e.host})
    usernames = sorted({e.username for e in rows if e.username})

    auth_fail = sum(1 for e in rows if e.event_type == "authentication_failure")
    auth_ok = sum(1 for e in rows if e.event_type == "authentication_success")
    denied = sum(1 for e in rows if e.event_type == "connection_denied")
    ts_values = [e.timestamp for e in rows if e.timestamp]
    span = None
    if len(ts_values) >= 2:
        span = (max(ts_values) - min(ts_values)).total_seconds()

    counts = {
        "events": len(rows),
        "sources": len(sources),
        "hosts": len(hosts),
        "auth_failures": auth_fail,
        "auth_successes": auth_ok,
        "connections_denied": denied,
        "span_seconds": span,
    }

    return CorrelationResult(
        focus=focus, window=window, timeline=timeline, sources=sources,
        hosts=hosts, usernames=usernames, counts=counts,
        event_ids=[e.id for e in rows],
    )
