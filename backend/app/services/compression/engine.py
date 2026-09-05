"""Template-based micro-compression (Module 24).

A record is "compressed" by replacing its full text with a reference to a
mined Template plus the small set of variable values that differ from that
template - see docs/template-mining.md#compression for the exact byte
accounting and the reconstruction guarantee.

Nothing here is estimated: every byte count is measured on the actual
serialized representation, and every reconstruction is verified against the
original raw log before being reported as successful.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ingestion import ProcessingJob, RawLog
from app.models.template import CompressionRecord, Template, TemplateMatch
from app.services.templates.service import mine_templates

log = get_logger("compression")


class ReconstructionError(RuntimeError):
    pass


def reconstruct(template: Template, match: TemplateMatch) -> str:
    """template + this record's variables (+ separators if non-default) -> exact original text."""
    seps = match.separators if match.separators is not None else template.separators
    trailing = match.trailing if match.trailing else template.trailing
    if len(seps) != template.token_count:
        raise ReconstructionError(
            f"separator count {len(seps)} != token_count {template.token_count}"
        )
    variables = iter(match.variables)
    parts: list[str] = []
    try:
        for i, lit in enumerate(template.literal_tokens):
            parts.append(seps[i] if i < len(seps) else " ")
            parts.append(lit if lit is not None else next(variables))
    except StopIteration as exc:
        raise ReconstructionError("not enough stored variables to reconstruct") from exc
    parts.append(trailing)
    return "".join(parts)


def _compressed_payload_bytes(template: Template, match: TemplateMatch) -> int:
    payload = {"t": template.template_key, "v": match.variables}
    if match.separators is not None:
        payload["s"] = match.separators
    if match.trailing:
        payload["e"] = match.trailing
    return len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def _template_definition_bytes(template: Template) -> int:
    definition = {
        "pattern": template.pattern,
        "literals": template.literal_tokens,
        "types": template.variable_types,
        "separators": template.separators,
        "trailing": template.trailing,
    }
    return len(json.dumps(definition, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


@dataclass
class CompressResult:
    records_in_scope: int = 0
    records_compressed: int = 0
    templates_used: int = 0
    mining_summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "records_in_scope": self.records_in_scope,
            "records_compressed": self.records_compressed,
            "templates_used": self.templates_used,
            "mining_summary": self.mining_summary,
        }


def _scope_raw_logs(db: Session, *, job_id: str | None, source: str | None, limit: int | None):
    stmt = select(RawLog)
    if job_id:
        stmt = stmt.where(RawLog.job_id == job_id)
    if source:
        stmt = stmt.where(RawLog.source_name == source)
    stmt = stmt.order_by(RawLog.received_at.asc(), RawLog.id.asc())
    if limit:
        stmt = stmt.limit(limit)
    return db.execute(stmt).scalars().all()


def compress_scope(
    db: Session, *, job_id: str | None = None, source: str | None = None,
    limit: int | None = None,
) -> CompressResult:
    """Ensure every raw log in scope has a TemplateMatch (mining any that don't yet)."""
    time_from = time_to = None
    if job_id:
        job = db.get(ProcessingJob, job_id)
        if job and job.started_at:
            time_from = job.started_at
        if job and job.finished_at:
            time_to = job.finished_at

    summary = mine_templates(db, source=source, time_from=time_from, time_to=time_to,
                             limit=limit or 20_000)

    rows = _scope_raw_logs(db, job_id=job_id, source=source, limit=limit)
    row_ids = [r.id for r in rows]
    matched = 0
    templates_used: set[str] = set()
    if row_ids:
        matches = db.execute(
            select(TemplateMatch).where(TemplateMatch.raw_log_id.in_(row_ids))
        ).scalars().all()
        matched = len(matches)
        templates_used = {m.template_id for m in matches}

    return CompressResult(
        records_in_scope=len(rows), records_compressed=matched,
        templates_used=len(templates_used), mining_summary=summary.to_dict(),
    )


@dataclass
class BenchmarkResult:
    scope: str
    record_count: int = 0
    reconstructable_count: int = 0
    template_count: int = 0
    original_bytes: int = 0
    compressed_bytes: int = 0
    metadata_bytes: int = 0
    total_compressed_bytes: int = 0
    savings_bytes: int = 0
    reduction_pct: float = 0.0
    processing_seconds: float = 0.0
    events_per_sec: float = 0.0
    mismatches: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scope": self.scope,
            "record_count": self.record_count,
            "reconstructable_count": self.reconstructable_count,
            "template_count": self.template_count,
            "original_bytes": self.original_bytes,
            "compressed_bytes": self.compressed_bytes,
            "metadata_bytes": self.metadata_bytes,
            "total_compressed_bytes": self.total_compressed_bytes,
            "savings_bytes": self.savings_bytes,
            "reduction_pct": round(self.reduction_pct, 2),
            "processing_seconds": round(self.processing_seconds, 3),
            "events_per_sec": round(self.events_per_sec, 1),
            "mismatches": self.mismatches[:10],
        }


def run_benchmark(
    db: Session, *, job_id: str | None = None, source: str | None = None,
    limit: int | None = None, persist: bool = True,
) -> BenchmarkResult:
    start = time.perf_counter()
    compress_scope(db, job_id=job_id, source=source, limit=limit)

    rows = _scope_raw_logs(db, job_id=job_id, source=source, limit=limit)
    scope = f"job:{job_id}" if job_id else (f"source:{source}" if source else "all")
    result = BenchmarkResult(scope=scope)
    if not rows:
        result.processing_seconds = time.perf_counter() - start
        return result

    row_ids = [r.id for r in rows]
    matches = {
        m.raw_log_id: m
        for m in db.execute(
            select(TemplateMatch).where(TemplateMatch.raw_log_id.in_(row_ids))
        ).scalars().all()
    }
    template_ids = {m.template_id for m in matches.values()}
    templates = {
        t.id: t
        for t in db.execute(select(Template).where(Template.id.in_(template_ids))).scalars().all()
    }

    metadata_bytes = sum(_template_definition_bytes(t) for t in templates.values())
    original_bytes = 0
    compressed_bytes = 0
    reconstructable = 0

    for row in rows:
        original_bytes += len(row.content.encode("utf-8"))
        match = matches.get(row.id)
        if not match:
            continue  # no template found for this line (e.g. unique one-off) - not compressed
        template = templates.get(match.template_id)
        if not template:
            continue
        compressed_bytes += _compressed_payload_bytes(template, match)
        try:
            rebuilt = reconstruct(template, match)
            ok = rebuilt == row.content
        except ReconstructionError:
            ok = False
            rebuilt = None
        if ok:
            reconstructable += 1
        elif len(result.mismatches) < 10:
            result.mismatches.append({
                "raw_log_id": row.id,
                "original_preview": row.content[:120],
                "reconstructed_preview": (rebuilt or "")[:120],
            })

    total_compressed = compressed_bytes + metadata_bytes
    savings = original_bytes - total_compressed
    reduction_pct = (savings / original_bytes * 100) if original_bytes else 0.0
    elapsed = time.perf_counter() - start

    result.record_count = len(rows)
    result.reconstructable_count = reconstructable
    result.template_count = len(templates)
    result.original_bytes = original_bytes
    result.compressed_bytes = compressed_bytes
    result.metadata_bytes = metadata_bytes
    result.total_compressed_bytes = total_compressed
    result.savings_bytes = savings
    result.reduction_pct = reduction_pct
    result.processing_seconds = elapsed
    result.events_per_sec = (len(rows) / elapsed) if elapsed > 0 else float(len(rows))

    if persist:
        db.add(CompressionRecord(
            ts=datetime.now(timezone.utc), job_id=job_id, scope=scope,
            original_bytes=original_bytes, compressed_bytes=compressed_bytes,
            metadata_bytes=metadata_bytes, total_compressed_bytes=total_compressed,
            reduction_pct=reduction_pct, record_count=result.record_count,
            reconstructable_count=reconstructable, template_count=result.template_count,
            processing_seconds=elapsed, events_per_sec=result.events_per_sec,
            method="template+varsub",
            detail={"mismatches": result.mismatches},
        ))
        db.commit()

    log.info("benchmark scope=%s records=%d original=%dB compressed=%dB (%.1f%%) recon=%d/%d",
             scope, result.record_count, original_bytes, total_compressed, reduction_pct,
             reconstructable, result.record_count)
    return result
