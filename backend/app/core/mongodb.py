"""MongoDB client, connection management, and index initialization.

Provides high-throughput document storage for:
- raw_logs
- normalized_events
- processing_jobs
- security_events
- security_alerts
- templates
- template_matches
- compression_records
- pipeline_runs
- response_simulations

Supports both real MongoDB (production/Docker) and in-memory mongomock
(zero-infrastructure dev/testing) with automatic fallback and diagnostics.
"""
from __future__ import annotations

import threading
from typing import Any

import pymongo
from pymongo import ASCENDING, DESCENDING, IndexModel, MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("mongodb")

_client_lock = threading.Lock()
_mongo_client: MongoClient | None = None
_is_mock: bool = False


def create_mongo_client(
    uri: str | None = None,
    timeout_ms: int | None = None,
    force_mock: bool = False,
) -> tuple[MongoClient, bool]:
    """Create a MongoDB client.

    Returns (client, is_mock). If live connection fails or force_mock=True,
    gracefully initializes mongomock so the system remains fully operational.
    """
    if force_mock:
        import mongomock

        log.info("Using mongomock client (force_mock=True)")
        return mongomock.MongoClient(), True

    target_uri = uri or settings.mongodb_uri
    target_timeout = timeout_ms or settings.mongodb_timeout_ms

    try:
        client = MongoClient(
            target_uri,
            serverSelectionTimeoutMS=target_timeout,
            connectTimeoutMS=target_timeout,
            maxPoolSize=settings.mongodb_max_pool_size,
            minPoolSize=settings.mongodb_min_pool_size,
        )
        # Test server availability
        client.admin.command("ping")
        log.info("Connected to live MongoDB at %s", target_uri.split("@")[-1])
        return client, False
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as exc:
        if settings.mongodb_require_live or (settings.environment == "production" and not settings.mongodb_allow_mock):
            log.error("Live MongoDB connection failed at %s: %s (mongomock fallback disabled)", target_uri.split("@")[-1], exc)
            raise RuntimeError(
                f"Live MongoDB connection failed at {target_uri.split('@')[-1]}: {exc}. "
                "Fallback to mongomock is disabled in live/production mode."
            ) from exc

        log.warning(
            "Live MongoDB unavailable at %s (%s). Engaging mongomock for development/air-gapped zero-infra mode.",
            target_uri.split("@")[-1],
            exc,
        )
        import mongomock

        mock_client = mongomock.MongoClient()
        return mock_client, True


def get_mongo_client() -> MongoClient:
    """Singleton getter for the MongoDB client."""
    global _mongo_client, _is_mock
    if _mongo_client is None:
        with _client_lock:
            if _mongo_client is None:
                _mongo_client, _is_mock = create_mongo_client()
    return _mongo_client


def close_mongo_client() -> None:
    """Explicitly close the MongoDB client on shutdown."""
    global _mongo_client, _is_mock
    with _client_lock:
        if _mongo_client is not None:
            try:
                _mongo_client.close()
            except Exception:
                pass
            _mongo_client = None
            _is_mock = False


def get_mongo_db(name: str | None = None) -> Database:
    """Return the active MongoDB database instance."""
    client = get_mongo_client()
    db_name = name or settings.mongodb_db_name
    return client[db_name]


def is_mongo_mock() -> bool:
    """Return True if currently using mongomock."""
    global _is_mock
    get_mongo_client()  # ensure initialized
    return _is_mock


def set_mongo_client_for_testing(client: MongoClient, is_mock: bool = True) -> None:
    """Override client for isolated test sessions."""
    global _mongo_client, _is_mock
    with _client_lock:
        _mongo_client = client
        _is_mock = is_mock


def init_mongo_indexes(db: Database) -> dict[str, list[str]]:
    """Idempotently create required indexes across all telemetry collections.

    Indexes are derived from actual query patterns used by the Log Explorer,
    Command Center, Alerts, Correlation Engine, Templates, and Ingestion.
    """
    created: dict[str, list[str]] = {}

    # 1. raw_logs indexes
    raw_indexes = [
        IndexModel([("job_id", ASCENDING), ("line_number", ASCENDING)], name="ix_raw_job_line"),
        IndexModel([("job_id", ASCENDING), ("status", ASCENDING)], name="ix_raw_job_status"),
        IndexModel([("content_hash", ASCENDING)], name="ix_raw_content_hash"),
        IndexModel([("received_at", DESCENDING)], name="ix_raw_received_at"),
    ]
    try:
        created["raw_logs"] = db["raw_logs"].create_indexes(raw_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("raw_logs index creation note: %s", exc)

    # 2. normalized_events indexes
    event_indexes = [
        IndexModel([("timestamp", DESCENDING)], name="ix_evt_timestamp"),
        IndexModel([("source_ip", ASCENDING), ("timestamp", DESCENDING)], name="ix_evt_src_ip_ts"),
        IndexModel([("destination_ip", ASCENDING), ("timestamp", DESCENDING)], name="ix_evt_dst_ip_ts"),
        IndexModel([("username", ASCENDING), ("timestamp", DESCENDING)], name="ix_evt_user_ts"),
        IndexModel([("host", ASCENDING), ("timestamp", DESCENDING)], name="ix_evt_host_ts"),
        IndexModel([("event_type", ASCENDING), ("timestamp", DESCENDING)], name="ix_evt_type_ts"),
        IndexModel([("severity", ASCENDING), ("timestamp", DESCENDING)], name="ix_evt_sev_ts"),
        IndexModel([("source", ASCENDING), ("timestamp", DESCENDING)], name="ix_evt_source_ts"),
        IndexModel([("job_id", ASCENDING)], name="ix_evt_job_id"),
        IndexModel([("raw_log_id", ASCENDING)], name="ix_evt_raw_log_id"),
        IndexModel([("processing_status", ASCENDING)], name="ix_evt_proc_status"),
        IndexModel([("template_id", ASCENDING)], name="ix_evt_template_id"),
    ]
    try:
        created["normalized_events"] = db["normalized_events"].create_indexes(event_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("normalized_events index creation note: %s", exc)

    # 3. processing_jobs indexes
    job_indexes = [
        IndexModel([("status", ASCENDING)], name="ix_job_status"),
        IndexModel([("created_at", DESCENDING)], name="ix_job_created_at"),
        IndexModel([("source_name", ASCENDING)], name="ix_job_source_name"),
    ]
    try:
        created["processing_jobs"] = db["processing_jobs"].create_indexes(job_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("processing_jobs index creation note: %s", exc)

    # 4. security_alerts indexes
    alert_indexes = [
        IndexModel([("dedup_key", ASCENDING)], unique=True, name="ux_alert_dedup_key"),
        IndexModel([("status", ASCENDING), ("ts", DESCENDING)], name="ix_alert_status_ts"),
        IndexModel([("severity", ASCENDING), ("risk_score", DESCENDING)], name="ix_alert_sev_risk"),
        IndexModel([("rule_key", ASCENDING), ("ts", DESCENDING)], name="ix_alert_rule_ts"),
    ]
    try:
        created["security_alerts"] = db["security_alerts"].create_indexes(alert_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("security_alerts index creation note: %s", exc)

    # 5. security_events indexes
    sec_event_indexes = [
        IndexModel([("job_id", ASCENDING)], name="ix_secevt_job_id"),
        IndexModel([("verdict", ASCENDING), ("ts", DESCENDING)], name="ix_secevt_verdict_ts"),
        IndexModel([("raw_reference", ASCENDING)], name="ix_secevt_raw_ref"),
        IndexModel([("detection_type", ASCENDING)], name="ix_secevt_type"),
    ]
    try:
        created["security_events"] = db["security_events"].create_indexes(sec_event_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("security_events index creation note: %s", exc)

    # 6. templates indexes
    template_indexes = [
        IndexModel([("token_signature", ASCENDING)], unique=True, name="ux_tpl_token_sig"),
        IndexModel([("template_key", ASCENDING)], unique=True, name="ux_tpl_key"),
        IndexModel([("occurrences", DESCENDING)], name="ix_tpl_occurrences"),
        IndexModel([("first_seen", DESCENDING)], name="ix_tpl_first_seen"),
    ]
    try:
        created["templates"] = db["templates"].create_indexes(template_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("templates index creation note: %s", exc)

    # 7. template_matches indexes
    match_indexes = [
        IndexModel([("raw_log_id", ASCENDING)], unique=True, name="ux_match_raw_log_id"),
        IndexModel([("template_id", ASCENDING), ("ts", DESCENDING)], name="ix_match_tpl_ts"),
    ]
    try:
        created["template_matches"] = db["template_matches"].create_indexes(match_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("template_matches index creation note: %s", exc)

    # 8. compression_records indexes
    comp_indexes = [
        IndexModel([("job_id", ASCENDING)], name="ix_comp_job_id"),
        IndexModel([("ts", DESCENDING)], name="ix_comp_ts"),
    ]
    try:
        created["compression_records"] = db["compression_records"].create_indexes(comp_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("compression_records index creation note: %s", exc)

    # 9. pipeline_runs indexes
    pipe_indexes = [
        IndexModel([("ts", DESCENDING)], name="ix_pipe_ts"),
        IndexModel([("created_by", ASCENDING)], name="ix_pipe_created_by"),
    ]
    try:
        created["pipeline_runs"] = db["pipeline_runs"].create_indexes(pipe_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("pipeline_runs index creation note: %s", exc)

    # 10. response_simulations indexes
    resp_indexes = [
        IndexModel([("alert_id", ASCENDING)], name="ix_resp_alert_id"),
        IndexModel([("ts", DESCENDING)], name="ix_resp_ts"),
    ]
    try:
        created["response_simulations"] = db["response_simulations"].create_indexes(resp_indexes)
    except Exception as exc:  # pragma: no cover
        log.warning("response_simulations index creation note: %s", exc)

    log.info("Initialized MongoDB indexes across %d collections", len(created))
    return created


# Alias for backward compatibility
ensure_mongo_indexes = init_mongo_indexes


def check_mongo_health() -> dict[str, Any]:
    """Check MongoDB health and connectivity for system monitoring."""
    try:
        client = get_mongo_client()
        mock = is_mongo_mock()
        if not mock:
            client.admin.command("ping")
        return {
            "status": "connected",
            "driver": "pymongo",
            "mode": "mongomock (dev/fallback)" if mock else "live",
            "database": settings.mongodb_db_name,
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "driver": "pymongo",
            "error": str(exc),
            "database": settings.mongodb_db_name,
        }
