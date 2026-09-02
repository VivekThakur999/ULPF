"""Ingestion orchestration (Module 3): file bytes -> job -> raw logs -> pipeline
-> normalized events, with real per-record counters and progress.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.event import NormalizedEvent
from app.models.ingestion import (
    JOB_COMPLETED,
    JOB_FAILED,
    JOB_RUNNING,
    RAW_STATUS_DUPLICATE,
    RAW_STATUS_INVALID,
    RAW_STATUS_PROCESSED,
    RAW_STATUS_QUARANTINED,
    ProcessingJob,
    RawLog,
)
from app.models.privacy import PiiSetting
from app.models.security import SecurityEvent
from app.services.ingestion.reader import iter_records
from app.services.pipeline.context import (
    DISPOSITION_INVALID,
    DISPOSITION_QUARANTINED,
)
from app.services.pipeline.service import content_hash, run_record

log = get_logger("ingestion")

_COMMIT_EVERY = 200
_SAMPLE_LINES = 60


def _sample(data: bytes, filename: str, hint: str | None) -> str:
    out: list[str] = []
    for _, text, blank in iter_records(data, filename=filename, fmt_hint=hint):
        if blank:
            continue
        out.append(text)
        if len(out) >= _SAMPLE_LINES:
            break
    return "\n".join(out)


def process_job(db: Session, job: ProcessingJob, data: bytes) -> ProcessingJob:
    from app.services.detection.detector import detector

    pii_row = db.get(PiiSetting, "default")

    job.status = JOB_RUNNING
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    start = time.perf_counter()
    seen_hashes: set[str] = set()
    total = processed = invalid = duplicates = quarantined = blanks = 0
    security_events = 0

    try:
        det = detector.detect(_sample(data, job.filename, job.declared_format),
                              hint=job.declared_format)
        job.detected_format = det.format
        db.commit()

        pending: list = []
        for line_no, text, is_blank in iter_records(
            data, filename=job.filename, fmt_hint=job.declared_format
        ):
            if is_blank:
                blanks += 1
                continue
            total += 1
            chash = content_hash(text)

            raw = RawLog(
                job_id=job.id,
                source_name=job.source_name,
                line_number=line_no,
                content=text,
                content_hash=chash,
            )

            if chash in seen_hashes:
                raw.status = RAW_STATUS_DUPLICATE
                duplicates += 1
                db.add(raw)
                pending.append(raw)
                if len(pending) >= _COMMIT_EVERY:
                    db.commit()
                    pending.clear()
                continue
            seen_hashes.add(chash)

            ctx = run_record(
                text,
                line_number=line_no,
                source_name=job.source_name,
                source_category=(job.stats or {}).get("source_category", "generic"),
                declared_format=job.detected_format,
                pii_settings=pii_row,
            )
            raw.security_verdict = ctx.security_verdict
            raw.processing_errors = ctx.errors[:20]

            db.add(raw)
            db.flush()  # get raw.id

            if ctx.security_verdict in ("SUSPICIOUS", "WEAPONIZED_LOG"):
                db.add(SecurityEvent(
                    detection_type=",".join(sorted({i["type"] for i in ctx.security_indicators})),
                    source=job.source_name,
                    severity=_max_indicator_sev(ctx.security_indicators),
                    verdict=ctx.security_verdict,
                    raw_reference=raw.id,
                    job_id=job.id,
                    reason=_shield_summary(ctx.security_indicators),
                    indicators=ctx.security_indicators,
                ))
                security_events += 1

            if ctx.disposition == DISPOSITION_QUARANTINED:
                raw.status = RAW_STATUS_QUARANTINED
                quarantined += 1
            elif ctx.disposition == DISPOSITION_INVALID or ctx.event is None:
                raw.status = RAW_STATUS_INVALID
                invalid += 1
            else:
                raw.status = RAW_STATUS_PROCESSED
                processed += 1
                ev = ctx.event
                db.add(_to_model(ev, job_id=job.id, raw_log_id=raw.id))

            pending.append(raw)
            if len(pending) >= _COMMIT_EVERY:
                _flush_progress(db, job, total, processed, invalid, duplicates,
                                quarantined, start)
                pending.clear()

        elapsed = max(1e-6, time.perf_counter() - start)
        job.total_records = total
        job.processed_records = processed
        job.invalid_records = invalid
        job.duplicate_records = duplicates
        job.quarantined_records = quarantined
        job.processing_rate = round(total / elapsed, 2)
        job.status = JOB_COMPLETED
        job.finished_at = datetime.now(timezone.utc)
        job.stats = {
            **(job.stats or {}),
            "blank_lines": blanks,
            "security_events": security_events,
            "elapsed_seconds": round(elapsed, 3),
            "format_confidence": det.confidence,
            "format_candidates": det.candidates,
        }
        db.commit()
        log.info("job %s done: %d/%d processed, %d invalid, %d dup, %d quarantined (%.0f rec/s)",
                 job.id, processed, total, invalid, duplicates, quarantined, job.processing_rate)

        # Run deterministic detection over recently-ingested events (cross-job,
        # so multi-source correlation works). Never fail the job on detection error.
        try:
            from app.services.security.detection import run_detection

            new_alerts = run_detection(db)
            job.stats = {**(job.stats or {}), "alerts_after_run": len(new_alerts)}
            db.commit()
        except Exception:  # pragma: no cover - defensive
            db.rollback()
            log.exception("post-ingestion detection failed for job %s", job.id)
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        job.status = JOB_FAILED
        job.error = f"{type(exc).__name__}: {exc}"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        log.exception("ingestion job %s failed", job.id)

    return job


def _flush_progress(db, job, total, processed, invalid, duplicates, quarantined, start):
    elapsed = max(1e-6, time.perf_counter() - start)
    job.total_records = total
    job.processed_records = processed
    job.invalid_records = invalid
    job.duplicate_records = duplicates
    job.quarantined_records = quarantined
    job.processing_rate = round(total / elapsed, 2)
    db.commit()


def _to_model(ev, *, job_id: str, raw_log_id: str) -> NormalizedEvent:
    return NormalizedEvent(
        job_id=job_id,
        raw_log_id=raw_log_id,
        timestamp=ev.timestamp,
        ingested_at=ev.ingested_at,
        source=ev.source,
        host=ev.host,
        event_type=ev.event_type,
        severity=ev.severity,
        username=ev.username,
        email=ev.email,
        source_ip=ev.source_ip,
        destination_ip=ev.destination_ip,
        source_port=ev.source_port,
        destination_port=ev.destination_port,
        protocol=ev.protocol,
        action=ev.action,
        status=ev.status,
        process=ev.process,
        service=ev.service,
        url=ev.url,
        http_method=ev.http_method,
        response_code=ev.response_code,
        message=ev.message,
        extra=ev.extra,
        field_confidence=ev.field_confidence,
        raw_log=ev.raw_log,
        parser=ev.parser,
        parser_version=ev.parser_version,
        schema_version=ev.schema_version,
        pii_protected=ev.pii_protected,
        pii_mode=ev.pii_mode,
        processing_status=ev.processing_status,
        confidence=ev.confidence,
        template_id=ev.template_id,
    )


def _max_indicator_sev(indicators: list[dict]) -> str:
    rank = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    best = "info"
    for i in indicators:
        if rank.get(i.get("severity", "info"), 0) > rank[best]:
            best = i["severity"]
    return best


def _shield_summary(indicators: list[dict]) -> str:
    return "; ".join(f"{i['type']} ({i['severity']})" for i in indicators)[:500]
