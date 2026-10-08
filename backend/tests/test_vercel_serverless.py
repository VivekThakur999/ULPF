"""Tests verifying Vercel serverless function entrypoint and execution compatibility."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Ensure root and backend are on sys.path
_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.index import handler
from app.auth.security import create_access_token


@pytest.fixture
def serverless_client():
    with patch.dict(os.environ, {"VERCEL": "1", "EXECUTION_ENV": "serverless"}):
        with TestClient(handler) as client:
            yield client


def test_vercel_entrypoint_loads_successfully(serverless_client):
    """Verify that api.index exports a valid FastAPI handler."""
    resp = serverless_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "telemetry_store" in data


def test_vercel_auth_and_rbac_guards(serverless_client):
    """Verify JWT authentication and role enforcement on serverless entrypoint."""
    # 1. Unauthenticated request to protected endpoint
    resp = serverless_client.get("/api/logs")
    assert resp.status_code == 401

    # 2. Invalid token
    resp = serverless_client.get("/api/logs", headers={"Authorization": "Bearer invalid.jwt.token"})
    assert resp.status_code == 401

    # 3. Valid Admin token
    admin_token = create_access_token(subject="admin-test-id", role="ADMIN", extra={"email": "admin@ulpf.io"})
    resp = serverless_client.get("/api/logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200

    # 4. Viewer cannot trigger admin-only mutations (e.g. creating log sources)
    viewer_token = create_access_token(subject="viewer-test-id", role="VIEWER", extra={"email": "viewer@ulpf.io"})
    resp = serverless_client.post(
        "/api/sources",
        json={"name": "Firewall Source", "category": "firewall", "format": "SYSLOG_RFC5424"},
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403


def test_vercel_synchronous_sample_ingestion(serverless_client):
    """Verify that in serverless mode (VERCEL=1), ingestion runs synchronously."""
    admin_token = create_access_token(subject="admin-test-id", role="ADMIN", extra={"email": "admin@ulpf.io"})
    raw_log = "Oct 08 12:00:00 firewall-gw %ASA-4-106023: Deny tcp src outside:198.51.100.25/4432 dst inside:10.0.0.5/80 by access-group"
    
    resp = serverless_client.post(
        "/api/ingestion/upload",
        files={"file": ("firewall.log", raw_log.encode("utf-8"), "text/plain")},
        data={"source_name": "firewall_test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 202
    job = resp.json()
    assert job["id"]
    assert str(job["status"]).upper() in ("COMPLETED", "PENDING", "PROCESSING")


def test_vercel_siem_and_ml_exports(serverless_client):
    """Verify SIEM NDJSON and ML-ready export endpoints via serverless entrypoint."""
    admin_token = create_access_token(subject="admin-test-id", role="ADMIN", extra={"email": "admin@ulpf.io"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    # NDJSON Export
    resp = serverless_client.get("/api/logs/export/ndjson?limit=10", headers=headers)
    assert resp.status_code == 200
    assert "application/x-ndjson" in resp.headers.get("content-type", "")

    # JSON Export
    resp = serverless_client.get("/api/logs/export/json?limit=10", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert "exported_count" in data or "total" in data

    # ML Feature Matrix Export
    resp = serverless_client.get("/api/logs/export/ml-ready?limit=10", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "feature_names" in data
    assert "records" in data
    assert len(data["feature_names"]) == 14


def test_vercel_offline_ai_explainer(serverless_client):
    """Verify deterministic offline AI provider is operational."""
    admin_token = create_access_token(subject="admin-test-id", role="ADMIN", extra={"email": "admin@ulpf.io"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = serverless_client.get("/api/ai/status", headers=headers)
    assert resp.status_code == 200
    status_data = resp.json()
    assert status_data["available"] is True
    assert status_data["offline"] is True
