import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models.event import NormalizedEvent
from app.repositories.events import EventRepository


def test_export_ndjson_and_json_and_ml_ready(client: TestClient, admin_token: str):
    db_session = SessionLocal()
    try:
        # Insert sample normalized events
        repo = EventRepository(db_session)
        ev1 = NormalizedEvent(
            id="evt-export-001",
            timestamp=datetime(2026, 10, 5, 14, 30, 0, tzinfo=timezone.utc),
            source="firewall_asa",
            host="fw-edge-01",
            event_type="network_deny",
            severity="WARNING",
            action="deny",
            status="blocked",
            source_ip="192.168.1.105",
            destination_ip="10.0.0.50",
            source_port=49152,
            destination_port=443,
            protocol="TCP",
            username="secuser",
            message="%ASA-4-106023: Deny tcp src outside:192.168.1.105/49152 dst inside:10.0.0.50/443",
            raw_log="%ASA-4-106023: Deny tcp src outside:192.168.1.105/49152 dst inside:10.0.0.50/443",
            parser="cisco_asa",
            parser_version="1.0.0",
            schema_version="1.0.0",
            pii_protected=False,
            confidence=0.98,
            processing_status="ok",
        )
        ev2 = NormalizedEvent(
            id="evt-export-002",
            timestamp=datetime(2026, 10, 5, 14, 35, 0, tzinfo=timezone.utc),
            source="linux_auth",
            host="auth-srv-02",
            event_type="auth_failure",
            severity="ERROR",
            action="login",
            status="failure",
            source_ip="203.0.113.42",
            username="root",
            message="Failed password for root from 203.0.113.42 port 22 ssh2",
            raw_log="Oct  5 14:35:00 auth-srv-02 sshd[1234]: Failed password for root from 203.0.113.42 port 22 ssh2",
            parser="linux_auth",
            parser_version="1.0.0",
            schema_version="1.0.0",
            pii_protected=False,
            confidence=0.95,
            processing_status="ok",
        )

        if repo._mongo is not None:
            repo._mongo.insert({
                "id": ev1.id, "timestamp": ev1.timestamp, "source": ev1.source, "host": ev1.host,
                "event_type": ev1.event_type, "severity": ev1.severity, "action": ev1.action, "status": ev1.status,
                "source_ip": ev1.source_ip, "destination_ip": ev1.destination_ip, "source_port": ev1.source_port,
                "destination_port": ev1.destination_port, "protocol": ev1.protocol, "username": ev1.username,
                "message": ev1.message, "raw_log": ev1.raw_log, "parser": ev1.parser, "confidence": ev1.confidence,
                "processing_status": ev1.processing_status, "schema_version": ev1.schema_version,
            })
            repo._mongo.insert({
                "id": ev2.id, "timestamp": ev2.timestamp, "source": ev2.source, "host": ev2.host,
                "event_type": ev2.event_type, "severity": ev2.severity, "action": ev2.action, "status": ev2.status,
                "source_ip": ev2.source_ip, "username": ev2.username, "message": ev2.message, "raw_log": ev2.raw_log,
                "parser": ev2.parser, "confidence": ev2.confidence, "processing_status": ev2.processing_status,
                "schema_version": ev2.schema_version,
            })
        else:
            db_session.add(ev1)
            db_session.add(ev2)
            db_session.commit()

        headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Test NDJSON Export
        res_ndjson = client.get("/api/logs/export/ndjson", headers=headers)
        assert res_ndjson.status_code == 200
        assert "application/x-ndjson" in res_ndjson.headers.get("content-type", "")
        assert "attachment;" in res_ndjson.headers.get("content-disposition", "")
        
        lines = [line for line in res_ndjson.text.strip().split("\n") if line.strip()]
        assert len(lines) >= 2
        record_0 = json.loads(lines[0])
        assert "@timestamp" in record_0
        assert "ecs" in record_0
        assert record_0["ecs"]["version"] == "1.12.0"
        assert "event" in record_0
        assert "ulpf" in record_0
        assert "traceability" in record_0["ulpf"]

        # 2. Test JSON Export
        res_json = client.get("/api/logs/export/json?source=firewall_asa", headers=headers)
        assert res_json.status_code == 200
        assert "application/json" in res_json.headers.get("content-type", "")
        data_json = res_json.json()
        assert data_json["schema_version"] == "1.0.0"
        assert data_json["export_type"] == "siem_universal_events"
        assert data_json["exported_count"] >= 1
        assert any(e["ulpf"]["source"] == "firewall_asa" for e in data_json["events"])

        # 3. Test ML-Ready Export
        res_ml = client.get("/api/logs/export/ml-ready", headers=headers)
        assert res_ml.status_code == 200
        data_ml = res_ml.json()
        assert data_ml["schema_version"] == "1.0.0"
        assert data_ml["export_type"] == "ml_feature_matrix"
        assert "feature_names" in data_ml
        assert "records" in data_ml
        assert len(data_ml["records"]) >= 2
        first_ml = data_ml["records"][0]
        assert "feature_vector" in first_ml
        assert isinstance(first_ml["feature_vector"], list)
        assert len(first_ml["feature_vector"]) == 14
        assert "severity_numeric" in first_ml
        assert "hour_of_day" in first_ml
        assert "timestamp_epoch" in first_ml
    finally:
        db_session.close()
