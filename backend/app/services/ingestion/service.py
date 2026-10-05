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
    RAW_STATUS_PENDING,
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


from app.core.config import settings


def process_job(db: Session, job: ProcessingJob, data: bytes) -> ProcessingJob:
    from app.services.detection.detector import detector

    pii_row = db.get(PiiSetting, "default")

    job.status = JOB_RUNNING
    job.started_at = datetime.now(timezone.utc)
    db.commit()

    mongo_ingest = None
    mongo_events = None
    mongo_alerts = None
    if settings.use_mongodb:
        try:
            from app.repositories.mongodb.alerts import MongoAlertRepository
            from app.repositories.mongodb.events import MongoEventRepository
            from app.repositories.mongodb.ingestion import MongoIngestionRepository

            mongo_ingest = MongoIngestionRepository()
            mongo_events = MongoEventRepository()
            mongo_alerts = MongoAlertRepository()

            mongo_ingest.create_job({
                "id": job.id,
                "source_id": job.source_id,
                "source_name": job.source_name,
                "filename": job.filename,
                "declared_format": job.declared_format,
                "detected_format": job.detected_format,
                "status": JOB_RUNNING,
                "started_at": job.started_at,
                "created_by": job.created_by,
            })
        except Exception as exc:
            log.warning("MongoDB job init note: %s", exc)

    start = time.perf_counter()
    seen_hashes: set[str] = set()
    total = processed = invalid = duplicates = quarantined = blanks = 0
    security_events = 0

    mongo_raw_pending: list[dict] = []
    mongo_event_pending: list[dict] = []
    mongo_sec_pending: list[dict] = []

    try:
        det = detector.detect(_sample(data, job.filename, job.declared_format),
                              hint=job.declared_format)
        job.detected_format = det.format
        db.commit()
        if mongo_ingest is not None:
            mongo_ingest.update_job(job.id, {"detected_format": det.format})

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
                if mongo_ingest is not None:
                    mongo_raw_pending.append({
                        "_id": raw.id,
                        "job_id": job.id,
                        "source_name": job.source_name,
                        "line_number": line_no,
                        "received_at": raw.received_at,
                        "content": text,
                        "content_hash": chash,
                        "status": RAW_STATUS_DUPLICATE,
                        "security_verdict": "SAFE",
                        "processing_errors": [],
                    })
                if len(pending) >= _COMMIT_EVERY:
                    db.commit()
                    if mongo_ingest is not None:
                        mongo_ingest.insert_raw_logs_bulk(mongo_raw_pending)
                        mongo_raw_pending.clear()
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

            if mongo_ingest is not None:
                mongo_raw_pending.append({
                    "_id": raw.id,
                    "job_id": job.id,
                    "source_name": job.source_name,
                    "line_number": line_no,
                    "received_at": raw.received_at,
                    "content": text,
                    "content_hash": chash,
                    "status": RAW_STATUS_PENDING,
                    "security_verdict": ctx.security_verdict,
                    "processing_errors": ctx.errors[:20],
                })

            if ctx.security_verdict in ("SUSPICIOUS", "WEAPONIZED_LOG"):
                sec_ev = SecurityEvent(
                    detection_type=",".join(sorted({i["type"] for i in ctx.security_indicators})),
                    source=job.source_name,
                    severity=_max_indicator_sev(ctx.security_indicators),
                    verdict=ctx.security_verdict,
                    raw_reference=raw.id,
                    job_id=job.id,
                    reason=_shield_summary(ctx.security_indicators),
                    indicators=ctx.security_indicators,
                )
                db.add(sec_ev)
                db.flush()
                security_events += 1
                if mongo_alerts is not None:
                    mongo_sec_pending.append({
                        "_id": sec_ev.id,
                        "detection_type": sec_ev.detection_type,
                        "source": sec_ev.source,
                        "severity": sec_ev.severity,
                        "verdict": sec_ev.verdict,
                        "raw_reference": raw.id,
                        "job_id": job.id,
                        "reason": sec_ev.reason,
                        "indicators": sec_ev.indicators,
                        "ts": sec_ev.ts,
                    })

            if ctx.disposition == DISPOSITION_QUARANTINED:
                raw.status = RAW_STATUS_QUARANTINED
                quarantined += 1
                if mongo_raw_pending:
                    mongo_raw_pending[-1]["status"] = RAW_STATUS_QUARANTINED
            elif ctx.disposition == DISPOSITION_INVALID or ctx.event is None:
                raw.status = RAW_STATUS_INVALID
                invalid += 1
                if mongo_raw_pending:
                    mongo_raw_pending[-1]["status"] = RAW_STATUS_INVALID
            else:
                raw.status = RAW_STATUS_PROCESSED
                processed += 1
                if mongo_raw_pending:
                    mongo_raw_pending[-1]["status"] = RAW_STATUS_PROCESSED
                ev = ctx.event
                ev_model = _to_model(ev, job_id=job.id, raw_log_id=raw.id)
                db.add(ev_model)
                db.flush()
                if mongo_events is not None:
                    mongo_event_pending.append({
                        "_id": ev_model.id,
                        "job_id": job.id,
                        "raw_log_id": raw.id,
                        "timestamp": ev.timestamp,
                        "ingested_at": ev.ingested_at or datetime.now(timezone.utc),
                        "source": ev.source,
                        "host": ev.host,
                        "event_type": ev.event_type,
                        "severity": ev.severity,
                        "username": ev.username,
                        "email": ev.email,
                        "source_ip": ev.source_ip,
                        "destination_ip": ev.destination_ip,
                        "source_port": ev.source_port,
                        "destination_port": ev.destination_port,
                        "protocol": ev.protocol,
                        "action": ev.action,
                        "status": ev.status,
                        "process": ev.process,
                        "service": ev.service,
                        "url": ev.url,
                        "http_method": ev.http_method,
                        "response_code": ev.response_code,
                        "message": ev.message,
                        "extra": ev.extra if isinstance(ev.extra, dict) else {},
                        "field_confidence": ev.field_confidence if isinstance(ev.field_confidence, dict) else {},
                        "raw_log": ev.raw_log,  # Deliberate denormalized copy for fast read performance
                        "parser": ev.parser,
                        "parser_version": ev.parser_version,
                        "schema_version": ev.schema_version,
                        "pii_protected": bool(ev.pii_protected),
                        "pii_mode": ev.pii_mode,
                        "processing_status": ev.processing_status,
                        "confidence": float(ev.confidence or 0.0),
                        "template_id": ev.template_id,
                    })

            pending.append(raw)
            if len(pending) >= _COMMIT_EVERY:
                _flush_progress(db, job, total, processed, invalid, duplicates,
                                quarantined, start)
                if mongo_ingest is not None and mongo_raw_pending:
                    mongo_ingest.insert_raw_logs_bulk(mongo_raw_pending)
                    mongo_raw_pending.clear()
                if mongo_events is not None and mongo_event_pending:
                    mongo_events.insert_bulk(mongo_event_pending)
                    mongo_event_pending.clear()
                if mongo_alerts is not None and mongo_sec_pending:
                    mongo_alerts.insert_security_events_bulk(mongo_sec_pending)
                    mongo_sec_pending.clear()
                pending.clear()

        # Flush any remaining items
        if mongo_ingest is not None and mongo_raw_pending:
            mongo_ingest.insert_raw_logs_bulk(mongo_raw_pending)
            mongo_raw_pending.clear()
        if mongo_events is not None and mongo_event_pending:
            mongo_events.insert_bulk(mongo_event_pending)
            mongo_event_pending.clear()
        if mongo_alerts is not None and mongo_sec_pending:
            mongo_alerts.insert_security_events_bulk(mongo_sec_pending)
            mongo_sec_pending.clear()

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

        if mongo_ingest is not None:
            mongo_ingest.update_job(job.id, {
                "total_records": total,
                "processed_records": processed,
                "invalid_records": invalid,
                "duplicate_records": duplicates,
                "quarantined_records": quarantined,
                "processing_rate": job.processing_rate,
                "status": JOB_COMPLETED,
                "finished_at": job.finished_at,
                "stats": job.stats,
            })

        log.info("job %s done: %d/%d processed, %d invalid, %d dup, %d quarantined (%.0f rec/s)",
                 job.id, processed, total, invalid, duplicates, quarantined, job.processing_rate)

        # Run deterministic detection over recently-ingested events (cross-job,
        # so multi-source correlation works). Never fail the job on detection error.
        try:
            from app.services.security.detection import run_detection

            new_alerts = run_detection(db)
            job.stats = {**(job.stats or {}), "alerts_after_run": len(new_alerts)}
            db.commit()
            if mongo_ingest is not None:
                mongo_ingest.update_job(job.id, {"stats": job.stats})
        except Exception:  # pragma: no cover - defensive
            db.rollback()
            log.exception("post-ingestion detection failed for job %s", job.id)
    except Exception as exc:  # pragma: no cover - defensive
        db.rollback()
        job.status = JOB_FAILED
        job.error = f"{type(exc).__name__}: {exc}"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        if mongo_ingest is not None:
            mongo_ingest.update_job(job.id, {
                "status": JOB_FAILED,
                "error": job.error,
                "finished_at": job.finished_at,
            })
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
