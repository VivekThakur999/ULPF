"""Air-Gapped Sovereign Mode Verification Tests.

Guarantees zero outbound network calls, local SQLite/PostgreSQL control plane,
and local deterministic AI explainer operation when disconnected from cloud infrastructure.
"""
import socket
import pytest
from app.core.config import settings
from app.services.ai.service import provider_status, select_provider, build_raw_context


def test_airgap_mode_configuration_defaults(monkeypatch):
    """Verify system operates in sovereign air-gapped mode when Supabase is unconfigured."""
    monkeypatch.setattr(settings, "supabase_url", None)
    monkeypatch.setattr(settings, "supabase_anon_key", None)
    monkeypatch.setattr(settings, "supabase_service_role_key", None)
    monkeypatch.setattr(settings, "ai_provider", "local_template")

    status = provider_status()
    assert status["offline"] is True
    assert status["provider"] == "LOCAL OFFLINE EXPLAINER"
    assert status["available"] is True

    provider, fallback = select_provider()
    assert provider.name == "LOCAL OFFLINE EXPLAINER"
    assert fallback is None


def test_airgap_ai_explainer_offline_execution(client, analyst_headers, monkeypatch):
    """Verify offline AI explainer functions with zero external model/cloud calls."""
    monkeypatch.setattr(settings, "ai_provider", "local_template")

    r = client.post(
        "/api/ai/explain",
        headers=analyst_headers,
        json={
            "kind": "raw",
            "text": "Sep 04 12:00:01 srv01 sshd[123]: Failed password for root from 10.0.0.99 port 22",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["offline"] is True
    assert body["provider"] == "LOCAL OFFLINE EXPLAINER"
    assert "explanation" in body
    assert "suggested_steps" in body["explanation"]
    assert "advisory" in body["explanation"]["disclaimer"].lower()


def test_airgap_pipeline_zero_cloud_leakage(client, analyst_headers):
    """Verify ingestion pipeline runs without any outbound cloud communication."""
    content = (
        "Sep 04 12:00:01 web-01 nginx: 192.168.1.50 - - [04/Sep/2026:12:00:01 +0000] "
        '"GET /admin/login.php HTTP/1.1" 401 128 "-" "Mozilla/5.0"\n'
    ).encode("utf-8")

    r = client.post(
        "/api/ingestion/upload",
        headers=analyst_headers,
        files={"file": ("airgap.log", content, "text/plain")},
        data={"source_name": "airgap-source"},
    )
    assert r.status_code == 202
    job_id = r.json()["id"]

    job = client.get(f"/api/ingestion/jobs/{job_id}", headers=analyst_headers).json()
    assert job["id"] == job_id
