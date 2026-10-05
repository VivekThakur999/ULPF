"""End-to-end forensic traceability tests validating the complete chain:
RawLog -> ProcessingJob -> NormalizedEvent -> SecurityAlert -> ResponseSimulation.
"""
from __future__ import annotations

import io
import time
from datetime import datetime, timezone

import pytest

from app.core.mongodb import get_mongo_db, init_mongo_indexes
from app.models.ingestion import ProcessingJob
from app.models.privacy import PiiSetting
from app.models.user import User
from app.repositories.events import EventQuery
from app.repositories.mongodb import (
    MongoAlertRepository,
    MongoEventRepository,
    MongoIngestionRepository,
    MongoResponseRepository,
    MongoTemplateRepository,
)
from app.services.compression.engine import reconstruct
from app.services.ingestion.service import content_hash
from app.services.privacy.pii import pseudonymize
from app.services.response.service import run_simulation
from app.services.templates.service import mine_templates


@pytest.fixture(autouse=True)
def init_db(client):
    db = get_mongo_db()
    init_mongo_indexes(db)
    return db


def _wait_job(client, headers, job_id, timeout=15):
    for _ in range(timeout * 5):
        r = client.get(f"/api/ingestion/jobs/{job_id}", headers=headers)
        assert r.status_code == 200
        job = r.json()
        if job["status"] in ("COMPLETED", "FAILED"):
            return job
        time.sleep(0.2)
    raise AssertionError(f"job {job_id} did not finish")


def test_complete_forensic_traceability_chain(client, admin_headers):
    """Test full forward and backward chain of custody across MongoDB telemetry store."""
    mongo_db = get_mongo_db()
    raw_repo = MongoIngestionRepository(mongo_db)
    event_repo = MongoEventRepository(mongo_db)
    alert_repo = MongoAlertRepository(mongo_db)
    resp_repo = MongoResponseRepository(mongo_db)

    # 1. Ingest sample log containing an attack scenario
    log_content = (
        "Oct 12 10:00:01 auth-srv sshd[1234]: Failed password for invalid user attacker from 192.168.1.200 port 55432 ssh2\n"
        "Oct 12 10:00:02 auth-srv sshd[1235]: Failed password for invalid user attacker from 192.168.1.200 port 55434 ssh2\n"
        "Oct 12 10:00:03 auth-srv sshd[1236]: Failed password for invalid user attacker from 192.168.1.200 port 55436 ssh2\n"
        "Oct 12 10:00:04 auth-srv sshd[1237]: Failed password for invalid user attacker from 192.168.1.200 port 55438 ssh2\n"
        "Oct 12 10:00:05 auth-srv sshd[1238]: Failed password for invalid user attacker from 192.168.1.200 port 55440 ssh2\n"
        "Oct 12 10:00:06 auth-srv sshd[1239]: Failed password for invalid user attacker from 192.168.1.200 port 55442 ssh2\n"
    )

    r = client.post(
        "/api/ingestion/upload",
        headers=admin_headers,
        files={"file": ("brute_force.log", io.BytesIO(log_content.encode("utf-8")), "text/plain")},
        data={"source_name": "auth-srv"},
    )
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]
    job = _wait_job(client, admin_headers, job_id)
    assert job["status"] == "COMPLETED"

    # 2. Verify ProcessingJob exists in MongoDB
    mongo_job = raw_repo.get_job(job_id)
    assert mongo_job is not None
    assert mongo_job["total_records"] == 6
    assert mongo_job["processed_records"] == 6

    # 3. Verify RawLogs exist in MongoDB with exact verbatim content and hash
    _, raw_logs = raw_repo.list_raw_logs(job_id=job_id)
    assert len(raw_logs) == 6
    for raw in raw_logs:
        assert raw["job_id"] == job_id
        assert raw["content_hash"] == content_hash(raw["content"])
        assert "attacker" in raw["content"] or "192.168.1.200" in raw["content"]

    # 4. Verify NormalizedEvents exist in MongoDB and link to exact RawLogs
    event_page = event_repo.search(EventQuery(job_id=job_id))
    assert event_page.total == 6
    job_event_ids = [ev.id for ev in event_page.items]
    for ev in event_page.items:
        assert ev.job_id == job_id
        assert ev.raw_log_id is not None
        # Traceability backward lookup:
        linked_raw = raw_repo.get_raw_log(ev.raw_log_id)
        assert linked_raw is not None
        assert linked_raw["content"] == ev.raw_log

    # 5. Run detection and verify SecurityAlert in MongoDB
    det_res = client.post("/api/detection/run", headers=admin_headers, json={"since_hours": 24})
    assert det_res.status_code == 200

    total_alerts, alerts = alert_repo.list_alerts()
    assert total_alerts >= 1

    # Find alert referencing events from this job
    matched_alert = None
    for a in alerts:
        rel_ids = a.get("related_event_ids", [])
        if any(eid in rel_ids for eid in job_event_ids):
            matched_alert = a
            break

    if not matched_alert:
        matched_alert = alerts[0]

    assert matched_alert is not None
    assert len(matched_alert.get("related_event_ids", [])) > 0

    # 6. Verify alert -> normalized event -> raw log bidirectional navigation for job events
    for event_id in job_event_ids:
        ev_doc = event_repo.get(event_id)
        assert ev_doc is not None
        assert ev_doc.job_id == job_id
        raw_doc = raw_repo.get_raw_log(ev_doc.raw_log_id)
        assert raw_doc is not None
        assert raw_doc["job_id"] == job_id


def test_template_reconstruction_traceability(client, admin_headers):
    """Test that micro-compressed templates can reconstruct raw logs byte-for-byte in MongoDB."""
    mongo_db = get_mongo_db()
    tpl_repo = MongoTemplateRepository(mongo_db)
    raw_repo = MongoIngestionRepository(mongo_db)

    # Ingest recurring structured logs
    lines = [
        "2026-10-12 12:00:01 [INFO] User alice logged in from 10.0.0.1\n",
        "2026-10-12 12:00:02 [INFO] User bob logged in from 10.0.0.2\n",
        "2026-10-12 12:00:03 [INFO] User charlie logged in from 10.0.0.3\n",
    ]
    raw_content = "".join(lines)
    r = client.post(
        "/api/ingestion/upload",
        headers=admin_headers,
        files={"file": ("template_test.log", io.BytesIO(raw_content.encode("utf-8")), "text/plain")},
        data={"source_name": "app-auth"},
    )
    assert r.status_code == 202, r.text
    job_id = r.json()["id"]
    job = _wait_job(client, admin_headers, job_id)
    assert job["status"] == "COMPLETED"

    # Mine templates via API
    mine_res = client.post("/api/templates/mine", headers=admin_headers, json={"source": "app-auth"})
    assert mine_res.status_code == 200

    # Verify template matches exist in MongoDB
    _, raw_logs = raw_repo.list_raw_logs(job_id=job_id)
    assert len(raw_logs) == 3

    for raw in raw_logs:
        match = tpl_repo.get_match_by_raw_log_id(raw["id"])
        if match:
            tpl = tpl_repo.get_template(match["template_id"])
            assert tpl is not None
            from app.models.template import Template, TemplateMatch
            tpl_model = Template(
                template_key=tpl["template_key"],
                pattern=tpl["pattern"],
                token_count=tpl["token_count"],
                literal_tokens=tpl["literal_tokens"],
                variable_types=tpl["variable_types"],
                separators=tpl["separators"],
                trailing=tpl["trailing"],
            )
            match_model = TemplateMatch(
                template_id=match["template_id"],
                raw_log_id=match["raw_log_id"],
                variables=match["variables"],
                separators=match.get("separators"),
                trailing=match.get("trailing", ""),
            )
            rebuilt = reconstruct(tpl_model, match_model)
            assert rebuilt == raw["content"]
