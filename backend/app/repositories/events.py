"""Event repository - the single place normalized events are queried.

Backed by SQLAlchemy today. The public surface (EventQuery -> EventPage) is
deliberately storage-agnostic so an OpenSearch/Elasticsearch implementation can
replace this class without touching services or the API.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models.event import NormalizedEvent


@dataclass
class EventQuery:
    text: str | None = None
    time_from: datetime | None = None
    time_to: datetime | None = None
    source: str | None = None
    host: str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None
    username: str | None = None
    event_type: str | None = None
    severity: str | None = None
    action: str | None = None
    status: str | None = None
    parser: str | None = None
    processing_status: str | None = None
    job_id: str | None = None
    template_id: str | None = None
    # generic "any of these ip fields equals X" (used by correlation)
    any_ip: str | None = None
    limit: int = 50
    offset: int = 0
    order: str = "desc"  # by timestamp/ingested_at
    fields_in: dict[str, Sequence[Any]] = field(default_factory=dict)


@dataclass
class EventPage:
    total: int
    items: list[NormalizedEvent]


_TEXT_COLUMNS = (
    NormalizedEvent.message,
    NormalizedEvent.raw_log,
    NormalizedEvent.host,
    NormalizedEvent.username,
    NormalizedEvent.source_ip,
    NormalizedEvent.url,
    NormalizedEvent.process,
)


class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def _apply(self, stmt, q: EventQuery):
        E = NormalizedEvent
        conds = []
        if q.text:
            like = f"%{q.text}%"
            conds.append(or_(*[c.ilike(like) for c in _TEXT_COLUMNS]))
        if q.time_from:
            conds.append(E.timestamp >= q.time_from)
        if q.time_to:
            conds.append(E.timestamp <= q.time_to)
        for col, val in (
            (E.source, q.source), (E.host, q.host), (E.source_ip, q.source_ip),
            (E.destination_ip, q.destination_ip), (E.username, q.username),
            (E.event_type, q.event_type), (E.severity, q.severity),
            (E.action, q.action), (E.status, q.status), (E.parser, q.parser),
            (E.processing_status, q.processing_status), (E.job_id, q.job_id),
            (E.template_id, q.template_id),
        ):
            if val is not None:
                conds.append(col == val)
        if q.any_ip:
            conds.append(or_(E.source_ip == q.any_ip, E.destination_ip == q.any_ip))
        for fname, values in q.fields_in.items():
            col = getattr(E, fname, None)
            if col is not None and values:
                conds.append(col.in_(list(values)))
        if conds:
            stmt = stmt.where(and_(*conds))
        return stmt

    def search(self, q: EventQuery) -> EventPage:
        E = NormalizedEvent
        base = self._apply(select(E), q)
        total = self.db.scalar(select(func.count()).select_from(base.subquery())) or 0
        order_col = E.timestamp.desc() if q.order == "desc" else E.timestamp.asc()
        rows = self.db.execute(
            base.order_by(order_col, E.ingested_at.desc())
            .offset(max(0, q.offset)).limit(min(max(1, q.limit), 500))
        ).scalars().all()
        return EventPage(total=total, items=list(rows))

    def get(self, event_id: str) -> NormalizedEvent | None:
        return self.db.get(NormalizedEvent, event_id)

    def facets(self, q: EventQuery, fields: Sequence[str]) -> dict[str, list[dict]]:
        E = NormalizedEvent
        out: dict[str, list[dict]] = {}
        for fname in fields:
            col = getattr(E, fname, None)
            if col is None:
                continue
            base = self._apply(select(col, func.count().label("n")), q)
            rows = self.db.execute(
                base.where(col.isnot(None)).group_by(col).order_by(func.count().desc()).limit(20)
            ).all()
            out[fname] = [{"value": r[0], "count": r[1]} for r in rows]
        return out

    def timeseries(self, q: EventQuery, *, bucket: str = "hour") -> list[dict]:
        """Coarse event-count time series (dialect-aware bucketing)."""
        E = NormalizedEvent
        dialect = self.db.bind.dialect.name if self.db.bind else "sqlite"
        if dialect == "sqlite":
            fmt = {"minute": "%Y-%m-%dT%H:%M", "hour": "%Y-%m-%dT%H:00:00",
                   "day": "%Y-%m-%d"}.get(bucket, "%Y-%m-%dT%H:00:00")
            bkt = func.strftime(fmt, E.timestamp)
        else:  # postgresql and friends
            bkt = func.date_trunc(bucket, E.timestamp)
        bkt = bkt.label("bucket")
        base = self._apply(select(bkt, func.count().label("n")), q)
        rows = self.db.execute(
            base.where(E.timestamp.isnot(None)).group_by("bucket").order_by("bucket")
        ).all()
        return [{"bucket": str(r[0]), "count": r[1]} for r in rows]

    def distinct_values(self, field_name: str, q: EventQuery | None = None) -> list[str]:
        E = NormalizedEvent
        col = getattr(E, field_name, None)
        if col is None:
            return []
        stmt = select(col).where(col.isnot(None)).distinct()
        if q:
            stmt = self._apply(stmt, q)
        return [r[0] for r in self.db.execute(stmt.limit(200)).all()]
