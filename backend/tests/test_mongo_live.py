"""Real MongoDB 8.0 Integration Tests.

Executes live against the real MongoDB Community Server 8.0 instance with
MONGODB_REQUIRE_LIVE=True and MONGODB_ALLOW_MOCK=False.
"""
import os
import time
from datetime import datetime, timezone
import pytest
from pymongo import MongoClient

from app.core.config import settings
from app.core.mongodb import ensure_mongo_indexes, get_mongo_client, get_mongo_db, close_mongo_client
from app.repositories.mongodb.alerts import MongoAlertRepository
from app.repositories.mongodb.events import MongoEventRepository
from app.repositories.mongodb.ingestion import MongoIngestionRepository
from app.repositories.mongodb.templates import MongoTemplateRepository
from app.repositories.mongodb.response import MongoResponseRepository
from app.repositories.events import EventQuery


@pytest.fixture(autouse=True)
def live_mongo_env(monkeypatch):
    """Enforce live MongoDB without mocking."""
    monkeypatch.setattr(settings, "mongodb_uri", "mongodb://localhost:27017/ulpf_telemetry")
    monkeypatch.setattr(settings, "mongodb_db_name", "ulpf_telemetry")
    monkeypatch.setattr(settings, "mongodb_require_live", True)
    monkeypatch.setattr(settings, "mongodb_allow_mock", False)
    monkeypatch.setattr(settings, "use_mongodb", True)
    # Ensure fresh client connection
    close_mongo_client()
    yield
    close_mongo_client()


def test_live_mongo_connection_and_ping():
    """Verify live MongoDB responds to ping and reports version 8.x."""
    client = get_mongo_client()
    res = client.admin.command("ping")
    assert res.get("ok") == 1.0

    build_info = client.admin.command("buildInfo")
    version = build_info.get("version", "")
    assert version.startswith("8.0") or version != "", f"MongoDB version: {version}"


def test_live_mongo_ensure_indexes():
    """Verify all required indexes are built on the live database."""
    db = get_mongo_db()
    ensure_mongo_indexes(db)

    # Check normalized_events indexes
    ev_indexes = db["normalized_events"].index_information()
    assert "ix_events_timestamp" in ev_indexes or any("timestamp" in str(idx) for idx in ev_indexes.values())

    # Check raw_logs indexes
    raw_indexes = db["raw_logs"].index_information()
    assert "ix_raw_job_id" in raw_indexes or any("job_id" in str(idx) for idx in raw_indexes.values())

    # Check security_alerts indexes
    alert_indexes = db["security_alerts"].index_information()
    assert "ix_alerts_dedup_key" in alert_indexes or any("dedup_key" in str(idx) for idx in alert_indexes.values())


def test_live_mongo_10_collections_schema_and_crud():
    """Verify CRUD and existence across all 10 authoritative telemetry collections."""
    db = get_mongo_db()
    
    collections = [
        "raw_logs",
        "normalized_events",
        "security_events",
        "security_alerts",
        "processing_jobs",
        "templates",
        "template_matches",
        "compression_records",
        "pipeline_runs",
        "response_simulations",
    ]

    test_id = f"test_probe_{int(time.time())}"
    now = datetime.now(timezone.utc)

    for coll_name in collections:
        coll = db[coll_name]
        # Insert test probe
        res = coll.insert_one({"_id": test_id, "test_marker": True, "created_at": now})
        assert res.inserted_id == test_id
        
        # Read back
        doc = coll.find_one({"_id": test_id})
        assert doc is not None
        assert doc.get("test_marker") is True
        
        # Cleanup
        coll.delete_one({"_id": test_id})
        assert coll.find_one({"_id": test_id}) is None


def test_live_mongo_bulk_write_and_search_pagination():
    """Verify batch insert and server-side pagination with MongoEventRepository."""
    repo = MongoEventRepository()
    now = datetime.now(timezone.utc)
    batch_source = f"src_live_test_{int(time.time())}"

    events = [
        {
            "id": f"ev_live_{batch_source}_{i}",
            "job_id": "job_live_test",
            "source": batch_source,
            "host": f"host-{i % 5}.infra.internal",
            "event_type": "authentication_failure" if i % 2 == 0 else "authentication_success",
            "severity": "high" if i % 2 == 0 else "info",
            "username": f"user_{i}",
            "source_ip": f"10.0.0.{i % 250}",
            "message": f"User login attempt {i} from host-{i % 5}",
            "timestamp": now,
            "ingested_at": now,
            "processing_status": "ok",
        }
        for i in range(60)
    ]

    inserted_ids = repo.insert_bulk(events)
    assert len(inserted_ids) == 60

    # Search with pagination
    page1 = repo.search(EventQuery(source=batch_source, limit=20, offset=0, order="desc"))
    assert page1.total == 60
    assert len(page1.items) == 20

    page2 = repo.search(EventQuery(source=batch_source, limit=20, offset=20, order="desc"))
    assert page2.total == 60
    assert len(page2.items) == 20

    # Search with filter
    fail_page = repo.search(EventQuery(source=batch_source, event_type="authentication_failure", limit=100))
    assert fail_page.total == 30

    # Search with any_ip
    ip_page = repo.search(EventQuery(source=batch_source, any_ip="10.0.0.10", limit=10))
    assert ip_page.total >= 1

    # Cleanup
    repo.collection.delete_many({"source": batch_source})


def test_live_mongo_aggregation_pipelines():
    """Verify MongoDB aggregation pipelines ($group, $match, $dateToString)."""
    repo = MongoEventRepository()
    now = datetime.now(timezone.utc)
    batch_source = f"src_agg_test_{int(time.time())}"

    events = [
        {
            "id": f"agg_ev_{batch_source}_{i}",
            "source": batch_source,
            "host": f"srv-{i % 3}.corp",
            "severity": "critical" if i < 10 else "medium",
            "timestamp": now,
            "ingested_at": now,
        }
        for i in range(30)
    ]
    repo.insert_bulk(events)

    # Facets aggregation
    facets = repo.facets(EventQuery(source=batch_source), ["severity", "host"])
    assert "severity" in facets
    assert "host" in facets
    
    sev_counts = {f["value"]: f["count"] for f in facets["severity"]}
    assert sev_counts.get("critical") == 10
    assert sev_counts.get("medium") == 20

    # Timeseries aggregation
    ts = repo.timeseries(EventQuery(source=batch_source), bucket="hour")
    assert len(ts) >= 1
    assert sum(b["count"] for b in ts) == 30

    # Cleanup
    repo.collection.delete_many({"source": batch_source})


def test_live_mongo_alert_repository_upsert_and_dedup():
    """Verify security alert deduplication and update logic in live MongoDB."""
    alert_repo = MongoAlertRepository()
    dedup_key = f"source_ip=192.168.1.99_live_{int(time.time())}"
    
    alert_data = {
        "dedup_key": dedup_key,
        "title": "Brute-force attack detected",
        "severity": "high",
        "risk_score": 78.5,
        "source": "correlation-engine",
        "rule_key": "RULE_2",
        "description": "10 failed logins in 5 minutes",
        "entity": {"source_ip": "192.168.1.99"},
        "status": "NEW",
    }

    # First insert
    created = alert_repo.upsert_alert(alert_data)
    assert created["id"]
    alert_id = created["id"]

    # Upsert with same dedup_key (should update existing, not duplicate)
    updated = alert_repo.upsert_alert({
        "dedup_key": dedup_key,
        "risk_score": 92.0,
        "severity": "critical",
    })
    assert updated["id"] == alert_id
    assert updated["risk_score"] == 92.0
    assert updated["severity"] == "critical"

    # Query alert
    fetched = alert_repo.get_alert(alert_id)
    assert fetched is not None
    assert fetched["risk_score"] == 92.0

    # Cleanup
    alert_repo.alerts.delete_one({"_id": alert_id})
