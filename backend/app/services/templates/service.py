"""Mining orchestration: RawLog rows -> Template + TemplateMatch rows.

Each call to mine_templates() is a fresh, deterministic clustering pass over
the rows matched by its filters. Re-running with the same filters over
unchanged data reassigns the same template_key to the same shape (matched by
token_signature) rather than creating duplicates - see
docs/template-mining.md for the full algorithm and the idempotency contract.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ingestion import RawLog
from app.models.template import Template, TemplateMatch
from app.services.templates.classify import separators_for, tokenize
from app.services.templates.mining import MinedCluster, RecordRef, mine_lines

log = get_logger("templates")

DEFAULT_SCAN_LIMIT = 20_000  # safety cap; documented, not a silent truncation
MAX_EXAMPLES_STORED = 8


@dataclass
class MiningSummary:
    records_scanned: int = 0
    records_matched: int = 0
    templates_total: int = 0
    templates_created: int = 0
    templates_updated: int = 0
    duration_seconds: float = 0.0
    scan_limit_hit: bool = False
    template_keys: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "records_scanned": self.records_scanned,
            "records_matched": self.records_matched,
            "templates_total": self.templates_total,
            "templates_created": self.templates_created,
            "templates_updated": self.templates_updated,
            "duration_seconds": round(self.duration_seconds, 3),
            "scan_limit_hit": self.scan_limit_hit,
            "template_keys": self.template_keys,
        }


def _next_template_key(db: Session) -> str:
    # Highest existing numeric suffix + 1 - stable even if rows are ever removed.
    keys = db.execute(select(Template.template_key)).scalars().all()
    best = 0
    for k in keys:
        try:
            n = int(k.split("-", 1)[1])
            best = max(best, n)
        except (IndexError, ValueError):
            continue
    return f"TPL-{best + 1:04d}"


def _load_records(
    db: Session, *, source: str | None, time_from: datetime | None,
    time_to: datetime | None, limit: int,
) -> tuple[list[RecordRef], bool]:
    stmt = select(RawLog).order_by(RawLog.received_at.asc(), RawLog.id.asc())
    if source:
        stmt = stmt.where(RawLog.source_name == source)
    if time_from:
        stmt = stmt.where(RawLog.received_at >= time_from)
    if time_to:
        stmt = stmt.where(RawLog.received_at <= time_to)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(stmt.limit(limit)).scalars().all()
    records = [
        RecordRef(ref_id=r.id, source=r.source_name, ts=r.received_at, raw=r.content)
        for r in rows
        if r.content and r.content.strip()
    ]
    return records, total > len(rows)


def _upsert_template(db: Session, cluster: MinedCluster) -> tuple[Template, bool]:
    signature = cluster.token_signature()
    existing = db.execute(
        select(Template).where(Template.token_signature == signature)
    ).scalars().first()

    source_dist: dict[str, int] = {}
    for m in cluster.members:
        source_dist[m.source] = source_dist.get(m.source, 0) + 1

    timestamps = [m.ts for m in cluster.members if m.ts]
    first_seen = min(timestamps) if timestamps else datetime.now(timezone.utc)
    last_seen = max(timestamps) if timestamps else datetime.now(timezone.utc)

    examples = [
        {"raw_log_id": m.ref_id, "source": m.source,
         "ts": m.ts.isoformat() if m.ts else None, "raw": m.raw[:500]}
        for m in cluster.members[:MAX_EXAMPLES_STORED]
    ]

    created = existing is None
    row = existing or Template(template_key=_next_template_key(db))
    row.pattern = cluster.pattern_text()
    row.token_count = cluster.token_count
    row.literal_tokens = cluster.literals
    row.variable_types = cluster.var_types
    row.separators = cluster.separators
    row.trailing = cluster.trailing
    row.token_signature = signature
    row.occurrences = cluster.occurrences
    row.variable_count = cluster.variable_count
    row.source_distribution = source_dist
    row.examples = examples
    row.example = examples[0]["raw"] if examples else ""
    row.first_seen = first_seen
    row.last_seen = last_seen
    if created:
        db.add(row)
    return row, created


def mine_templates(
    db: Session,
    *,
    source: str | None = None,
    time_from: datetime | None = None,
    time_to: datetime | None = None,
    limit: int = DEFAULT_SCAN_LIMIT,
) -> MiningSummary:
    start = time.perf_counter()
    records, limit_hit = _load_records(db, source=source, time_from=time_from,
                                       time_to=time_to, limit=limit)
    summary = MiningSummary(records_scanned=len(records), scan_limit_hit=limit_hit)
    if not records:
        summary.duration_seconds = time.perf_counter() - start
        return summary

    clusters = mine_lines(records)
    for cluster in clusters:
        template, created = _upsert_template(db, cluster)
        db.flush()  # need template.id for TemplateMatch FK

        for member in cluster.members:
            spans = tokenize(member.raw)
            tokens = [s.text for s in spans]
            variables = cluster.extract_variables(tokens)
            seps, trailing = separators_for(member.raw, spans)
            store_seps = None if seps == cluster.separators else seps
            store_trailing = "" if trailing == cluster.trailing else trailing

            match = db.execute(
                select(TemplateMatch).where(TemplateMatch.raw_log_id == member.ref_id)
            ).scalars().first()
            if not match:
                match = TemplateMatch(raw_log_id=member.ref_id)
                db.add(match)
            match.template_id = template.id
            match.source = member.source
            match.ts = member.ts or datetime.now(timezone.utc)
            match.variables = variables
            match.separators = store_seps
            match.trailing = store_trailing

        summary.records_matched += cluster.occurrences
        summary.template_keys.append(template.template_key)
        if created:
            summary.templates_created += 1
        else:
            summary.templates_updated += 1

    db.commit()
    summary.templates_total = summary.templates_created + summary.templates_updated
    summary.duration_seconds = time.perf_counter() - start
    log.info("mined %d template(s) from %d record(s) in %.3fs",
             summary.templates_total, summary.records_scanned, summary.duration_seconds)
    return summary
