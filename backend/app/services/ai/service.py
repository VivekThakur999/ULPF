"""AI explanation orchestration: provider selection + server-side evidence retrieval.

The API only accepts record identifiers. All security-relevant fields are
retrieved here from the database / pipeline - never trusted from the client -
so an AI explanation can never be seeded with fabricated evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.event import NormalizedEvent
from app.models.ingestion import RawLog
from app.models.security import SecurityAlert, SecurityEvent
from app.services.ai.base import AIProvider, ExplainContext, Explanation, ProviderUnavailable
from app.services.ai.offline import LightweightOfflineProvider
from app.services.correlation.engine import correlate

log = get_logger("ai")

_OFFLINE = LightweightOfflineProvider()


def _ollama():
    from app.services.ai.ollama import OllamaProvider

    return OllamaProvider()


def provider_status() -> dict[str, Any]:
    configured = settings.ai_provider
    if configured == "ollama":
        try:
            oll = _ollama()
            if oll.available():
                return {"provider": oll.name, "offline": True, "model": oll.model,
                        "available": True, "fallback_active": False,
                        "note": "Local Ollama inference. No cloud, no internet."}
        except Exception as exc:  # pragma: no cover
            log.warning("ollama status check failed: %s", exc)
        return {"provider": _OFFLINE.name, "offline": True, "model": None,
                "available": True, "fallback_active": True,
                "note": "Ollama configured but unavailable - using the local offline explainer."}
    if configured == "disabled":
        return {"provider": "disabled", "offline": True, "model": None,
                "available": False, "fallback_active": False,
                "note": "AI explanations are turned off (AI_PROVIDER=disabled)."}
    return {"provider": _OFFLINE.name, "offline": True, "model": None,
            "available": True, "fallback_active": False,
            "note": "Deterministic local offline explainer. No model, no network."}


def select_provider() -> tuple[AIProvider, str | None]:
    """Return (provider, fallback_from). Never raises."""
    if settings.ai_provider == "ollama":
        try:
            oll = _ollama()
            if oll.available():
                return oll, None
            return _OFFLINE, oll.name
        except Exception as exc:  # pragma: no cover
            log.warning("ollama selection failed: %s", exc)
            return _OFFLINE, "OLLAMA LOCAL"
    return _OFFLINE, None


# --- context building ------------------------------------------------------


def _event_evidence(db: Session, event: NormalizedEvent) -> dict[str, Any]:
    raw = db.get(RawLog, event.raw_log_id) if event.raw_log_id else None
    sec = []
    if raw:
        sec = db.execute(
            select(SecurityEvent).where(SecurityEvent.raw_reference == raw.id)
        ).scalars().all()
    # small table; membership check in Python keeps this portable across
    # SQLite / Postgres JSON representations.
    linked_alerts = [
        a.title for a in db.execute(select(SecurityAlert)).scalars().all()
        if event.id in (a.related_event_ids or [])
    ]

    ev_dict = _event_to_dict(event)
    return {
        "event": ev_dict,
        "raw_log": raw.content if raw else None,
        "security_verdict": raw.security_verdict if raw else None,
        "security_events": [
            {"detection_type": s.detection_type, "severity": s.severity,
             "verdict": s.verdict, "reason": s.reason}
            for s in sec
        ],
        "linked_alerts": linked_alerts,
        "parser": {"name": event.parser, "version": event.parser_version,
                   "schema_version": event.schema_version,
                   "confidence": event.confidence},
    }


def _event_to_dict(e: NormalizedEvent) -> dict[str, Any]:
    return {
        "id": e.id,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "ingested_at": e.ingested_at.isoformat() if e.ingested_at else None,
        "source": e.source, "host": e.host, "event_type": e.event_type,
        "severity": e.severity, "username": e.username, "email": e.email,
        "source_ip": e.source_ip, "destination_ip": e.destination_ip,
        "source_port": e.source_port, "destination_port": e.destination_port,
        "protocol": e.protocol, "action": e.action, "status": e.status,
        "process": e.process, "service": e.service, "url": e.url,
        "http_method": e.http_method, "response_code": e.response_code,
        "message": e.message, "parser": e.parser, "parser_version": e.parser_version,
        "schema_version": e.schema_version, "pii_mode": e.pii_mode,
        "confidence": e.confidence,
    }


def build_event_context(db: Session, event_id: str) -> ExplainContext | None:
    event = db.get(NormalizedEvent, event_id)
    if not event:
        return None
    evidence = _event_evidence(db, event)
    corr = {}
    if event.source_ip or event.username:
        corr = correlate(
            db,
            source_ip=event.source_ip or None,
            username=event.username if event.username and not event.source_ip else None,
            center_time=event.timestamp, window_seconds=1800, max_events=25,
        ).to_dict()
    return ExplainContext(
        kind="event", evidence=evidence, event=evidence["event"],
        correlation=corr, parser=evidence["parser"],
    )


def build_alert_context(db: Session, alert_id: str) -> ExplainContext | None:
    alert = db.get(SecurityAlert, alert_id)
    if not alert:
        return None
    entity = {k: v for k, v in (alert.entity or {}).items()
              if k in ("source_ip", "username", "host")}
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
        select(NormalizedEvent)
        .where(NormalizedEvent.id.in_((alert.related_event_ids or [])[:20]))
        .order_by(NormalizedEvent.timestamp)
    ).scalars().all()

    alert_dict = {
        "id": alert.id, "title": alert.title, "severity": alert.severity,
        "risk_score": alert.risk_score, "rule_key": alert.rule_key,
        "description": alert.description, "reason": alert.reason,
        "risk_breakdown": alert.risk_breakdown, "entity": alert.entity,
        "related_event_ids": alert.related_event_ids, "affected_hosts": alert.affected_hosts,
        "recommended_response": alert.recommended_response, "status": alert.status,
        "ts": alert.ts.isoformat() if alert.ts else None,
    }
    return ExplainContext(
        kind="alert", evidence={"alert": alert_dict, "correlation": corr},
        alert=alert_dict, correlation=corr,
        related_events=[
            {"ts": e.timestamp.isoformat() if e.timestamp else None,
             "source": e.source, "host": e.host, "event_type": e.event_type,
             "action": e.action, "status": e.status, "severity": e.severity}
            for e in related
        ],
    )


def build_raw_context(db: Session, text: str) -> ExplainContext:
    from app.models.privacy import PiiSetting
    from app.services.pipeline.service import run_record

    pii_row = db.get(PiiSetting, "default")
    ctx = run_record(text.rstrip("\n"), source_name="ai-explain", pii_settings=pii_row)
    ev_dict = ctx.event.model_dump(mode="json") if ctx.event else {}
    evidence = {
        "event": ev_dict,
        "raw_log": text,
        "security_verdict": ctx.security_verdict,
        "security_events": [
            {"detection_type": ",".join(sorted({i["type"] for i in ctx.security_indicators})),
             "severity": "n/a", "verdict": ctx.security_verdict,
             "reason": "; ".join(i["type"] for i in ctx.security_indicators)}
        ] if ctx.security_indicators else [],
        "linked_alerts": [],
        "parser": {"name": ctx.parser_name, "version": ctx.parser_version},
        "disposition": ctx.disposition,
    }
    return ExplainContext(
        kind="raw", evidence=evidence, event=ev_dict or None,
        parser=evidence["parser"], raw_untrusted=True,
    )


# --- top-level ------------------------------------------------------------


def explain(ctx: ExplainContext) -> Explanation:
    if settings.ai_provider == "disabled":
        raise ProviderUnavailable("AI explanations are disabled")
    provider, fallback_from = select_provider()
    try:
        result = provider.explain(ctx)
    except ProviderUnavailable as exc:
        log.warning("provider %s unavailable mid-call (%s); falling back to offline",
                    provider.name, exc)
        result = _OFFLINE.explain(ctx)
        result.fallback_from = provider.name
        return result
    if fallback_from:
        result.fallback_from = fallback_from
    return result
