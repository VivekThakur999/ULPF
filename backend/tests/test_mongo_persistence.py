"""Tests for MongoDB repositories, collections, and index initialization."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.mongodb import get_mongo_db, init_mongo_indexes
from app.repositories.events import EventQuery
from app.repositories.mongodb import (
    MongoAlertRepository,
    MongoEventRepository,
    MongoIngestionRepository,
    MongoPipelineRepository,
    MongoResponseRepository,
    MongoTemplateRepository,
)


@pytest.fixture
def mongo_db():
    db = get_mongo_db()
    init_mongo_indexes(db)
    return db


def test_mongo_indexes_initialization(mongo_db):
    indexes = init_mongo_indexes(mongo_db)
    assert "raw_logs" in indexes
    assert "normalized_events" in indexes
    assert "security_alerts" in indexes
    assert "templates" in indexes
    assert "template_matches" in indexes


def test_mongo_event_repository_crud(mongo_db):
    repo = MongoEventRepository(mongo_db)
    now = datetime.now(timezone.utc)

    event_id = repo.insert({
        "source": "firewall",
        "source_ip": "192.168.1.50",
        "destination_ip": "10.0.0.1",
        "event_type": "connection_denied",
        "severity": "high",
        "timestamp": now,
        "message": "DROP TCP 192.168.1.50:4444 -> 10.0.0.1:22",
        "raw_log": "DROP TCP 192.168.1.50:4444 -> 10.0.0.1:22",
    })

    assert event_id is not None
    fetched = repo.get(event_id)
    assert fetched is not None
    assert fetched.source_ip == "192.168.1.50"
    assert fetched.severity == "high"

    # Search
    page = repo.search(EventQuery(source_ip="192.168.1.50"))
    assert page.total >= 1
    assert any(e.id == event_id for e in page.items)

    # Facets
    facets = repo.facets(EventQuery(source_ip="192.168.1.50"), ["source", "severity", "event_type"])
    assert "source" in facets
    assert any(f["value"] == "firewall" for f in facets["source"])

    # Timeseries
    ts = repo.timeseries(EventQuery(source_ip="192.168.1.50"), bucket="hour")
    assert isinstance(ts, list)


def test_mongo_ingestion_repository(mongo_db):
    repo = MongoIngestionRepository(mongo_db)

    # Create job
    job_id = repo.create_job({
        "source_name": "test_source",
        "filename": "auth.log",
        "status": "RUNNING",
    })
    assert job_id is not None

    job = repo.get_job(job_id)
    assert job["status"] == "RUNNING"

    # Insert raw log
    raw_id = repo.insert_raw_log({
        "job_id": job_id,
        "source_name": "test_source",
        "line_number": 1,
        "content": "Accepted password for root from 192.168.1.100 port 22",
        "content_hash": "testhash123",
        "status": "PROCESSED",
        "security_verdict": "SAFE",
    })
    assert raw_id is not None

    raw = repo.get_raw_log(raw_id)
    assert raw["content_hash"] == "testhash123"

    # Update job
    repo.update_job(job_id, {"status": "COMPLETED", "processed_records": 1})
    updated_job = repo.get_job(job_id)
    assert updated_job["status"] == "COMPLETED"
    assert updated_job["processed_records"] == 1


def test_mongo_alerts_repository(mongo_db):
    repo = MongoAlertRepository(mongo_db)

    alert_doc = {
        "dedup_key": "source_ip=10.10.10.10",
        "title": "Multiple failed logins from 10.10.10.10",
        "severity": "high",
        "risk_score": 75.0,
        "status": "NEW",
        "rule_key": "RULE_1",
        "entity": {"source_ip": "10.10.10.10"},
        "related_event_ids": ["evt_1", "evt_2"],
    }

    # Upsert new
    res1 = repo.upsert_alert(alert_doc)
    assert res1["dedup_key"] == "source_ip=10.10.10.10"
    alert_id = res1["id"]

    # Upsert existing (dedup update)
    alert_doc["risk_score"] = 85.0
    res2 = repo.upsert_alert(alert_doc)
    assert res2["id"] == alert_id
    assert res2["risk_score"] == 85.0

    # List
    total, items = repo.list_alerts(status="NEW")
    assert total >= 1
    assert any(a["id"] == alert_id for a in items)


def test_mongo_template_repository(mongo_db):
    repo = MongoTemplateRepository(mongo_db)

    tpl_doc = {
        "template_key": "TPL-0099",
        "pattern": "User <*> logged in from <*>",
        "token_count": 5,
        "literal_tokens": ["User", None, "logged", "in", "from", None],
        "variable_types": [None, "username", None, None, None, "ip"],
        "separators": ["", " ", " ", " ", " ", " "],
        "trailing": "",
        "token_signature": "sig_abc_123",
        "occurrences": 10,
    }

    tpl = repo.upsert_template(tpl_doc)
    assert tpl["template_key"] == "TPL-0099"
    tpl_id = tpl["id"]

    # Template match
    repo.upsert_match({
        "template_id": tpl_id,
        "raw_log_id": "raw_log_test_1",
        "source": "linux",
        "variables": ["admin", "192.168.1.1"],
    })

    match = repo.get_match_by_raw_log_id("raw_log_test_1")
    assert match is not None
    assert match["variables"] == ["admin", "192.168.1.1"]
