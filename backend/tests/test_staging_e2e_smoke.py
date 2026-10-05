"""End-to-End Staging Smoke Test against the Live Docker Compose Stack.

Tests the full ULPF workflow across ports 8080 (Frontend NGINX) -> 8000 (FastAPI Backend)
-> MongoDB 8.0 (ulpf_telemetry) and PostgreSQL 16 (Control Plane).
"""
import json
import time
import urllib.request
import urllib.error
import pytest

BASE_URL = "http://localhost:8080"


def _http(method: str, path: str, data: dict | None = None, token: str | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    headers = {"Accept": "application/json"}
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode("utf-8")
        return json.loads(content) if content else {}


def test_docker_e2e_full_workflow():
    # 1. Health check via NGINX proxy
    health = _http("GET", "/health")
    assert health["status"] == "ok"
    assert health["database"] == "connected"
    assert health["telemetry_store"]["status"] == "connected"
    assert health["telemetry_store"]["mode"] == "live"

    # 2. Login as Admin
    login_resp = _http("POST", "/api/auth/login", {"email": "admin@ulpf.io", "password": "ChangeMe!123"})
    assert "access_token" in login_resp
    token = login_resp["access_token"]
    assert login_resp["user"]["role"] == "ADMIN"

    # 3. Fetch User Profile
    me = _http("GET", "/api/auth/me", token=token)
    assert me["email"] == "admin@ulpf.io"

    # 4. Check Analytics Overview
    overview = _http("GET", "/api/analytics/overview", token=token)
    assert "cards" in overview
    assert "charts" in overview

    # 5. Ingestion via Upload endpoint
    # Send multipart raw logs
    sample_lines = (
        "Sep 04 10:15:01 auth-srv-01 sshd[2841]: Failed password for invalid user root from 192.168.1.105 port 54112 ssh2\n"
        "Sep 04 10:15:03 auth-srv-01 sshd[2842]: Failed password for invalid user admin from 192.168.1.105 port 54114 ssh2\n"
        "Sep 04 10:15:06 auth-srv-01 sshd[2845]: Failed password for invalid user service from 192.168.1.105 port 54118 ssh2\n"
        "Sep 04 10:15:09 auth-srv-01 sshd[2848]: Failed password for user analyst from 192.168.1.105 port 54122 ssh2\n"
        "Sep 04 10:15:12 auth-srv-01 sshd[2850]: Failed password for user backup from 192.168.1.105 port 54126 ssh2\n"
        "Sep 04 10:15:15 auth-srv-01 sshd[2852]: Accepted password for user analyst from 192.168.1.105 port 54130 ssh2\n"
    )

    boundary = "----WebKitFormBoundaryStagingTest7MA4YWxkTrZu0gW"
    body_bytes = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="source_name"\r\n\r\n'
        f"staging-linux-auth\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="auth.log"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
        f"{sample_lines}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/ingestion/upload",
        data=body_bytes,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        upload_resp = json.loads(resp.read().decode("utf-8"))

    assert "id" in upload_resp
    job_id = upload_resp["id"]

    # 6. Poll Job Completion
    for _ in range(30):
        job = _http("GET", f"/api/ingestion/jobs/{job_id}", token=token)
        if job["status"] in ("COMPLETED", "FAILED"):
            break
        time.sleep(0.5)

    assert job["status"] == "COMPLETED"
    assert job["total_records"] >= 6
    assert job["processed_records"] >= 6

    # 7. Log Explorer Queries
    logs = _http("GET", f"/api/logs?job_id={job_id}", token=token)
    assert logs["total"] >= 6
    assert len(logs["items"]) >= 6

    # 8. Detection & Alert Verification
    alerts = _http("GET", "/api/alerts", token=token)
    assert "items" in alerts
    if alerts["items"]:
        alert = alerts["items"][0]
        alert_detail = _http("GET", f"/api/alerts/{alert['id']}", token=token)
        assert "timeline" in alert_detail
        assert "risk_score" in alert_detail["alert"]
        assert "related_events" in alert_detail

        # 9. Offline AI Explanation
        ai_resp = _http("POST", "/api/ai/explain", {"kind": "alert", "alert_id": alert["id"]}, token=token)
        assert ai_resp["kind"] == "alert"
        assert "explanation" in ai_resp
        assert ai_resp["offline"] is True

        # 10. Response Simulation
        sim_resp = _http(
            "POST",
            "/api/response/simulate",
            {"alert_id": alert["id"]},
            token=token,
        )
        assert sim_resp["simulation"] is True
        assert "disclaimer" in sim_resp
        assert "recommendation" in sim_resp

    # 11. Template Mining & Compression Benchmark
    mine_resp = _http("POST", "/api/templates/mine", {"source": "staging-linux-auth"}, token=token)
    assert "templates_total" in mine_resp

    bench_resp = _http("POST", "/api/compression/benchmark", {"source": "staging-linux-auth"}, token=token)
    assert "record_count" in bench_resp
    assert bench_resp["reconstructable_count"] == bench_resp["record_count"]
