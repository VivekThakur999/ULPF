"""Dashboard analytics must reflect real DB state, never fabricated numbers."""
import time
from pathlib import Path

_SAMPLES = Path(__file__).resolve().parents[2] / "sample_logs"


def _wait(client, headers, job_id):
    for _ in range(80):
        j = client.get(f"/api/ingestion/jobs/{job_id}", headers=headers).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            return j
        time.sleep(0.2)
    raise AssertionError("job timeout")


def test_overview_zero_state(client, admin_headers):
    r = client.get("/api/analytics/overview", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    for key in ("total_logs", "processed", "invalid", "duplicates", "quarantined",
                "normalized_events", "alerts", "avg_processing_rate"):
        assert key in body["cards"]
    for chart in ("logs_by_source", "logs_by_format", "events_by_severity",
                  "events_by_type", "events_over_time", "processing_outcomes",
                  "pii_transformations", "alerts_by_severity", "risk_distribution"):
        assert chart in body["charts"]


def test_overview_counts_match_ingestion(client, analyst_headers, admin_headers):
    before = client.get("/api/analytics/overview", headers=admin_headers).json()["cards"]

    content = (_SAMPLES / "linux" / "auth.log").read_bytes()
    r = client.post("/api/ingestion/upload", headers=analyst_headers,
                    files={"file": ("auth.log", content, "text/plain")},
                    data={"source_name": "analytics-linux"})
    job = _wait(client, analyst_headers, r.json()["id"])

    after = client.get("/api/analytics/overview", headers=admin_headers).json()

    # totals moved by exactly the job's numbers - not invented
    assert after["cards"]["total_logs"] == before["total_logs"] + job["total_records"]
    assert after["cards"]["processed"] >= before["processed"] + job["processed_records"] - 0
    assert after["cards"]["normalized_events"] >= before["normalized_events"] + job["processed_records"]

    # source status now lists the source we just ingested
    names = [s["name"] for s in after["source_status"]]
    assert "analytics-linux" in names
    src = next(s for s in after["source_status"] if s["name"] == "analytics-linux")
    assert src["events_processed"] >= 1
    assert src["last_received"] is not None

    # processing success rate is a real ratio in [0, 100]
    assert 0 <= after["processing_success_rate"] <= 100


def test_timeline_endpoint(client, admin_headers):
    r = client.get("/api/analytics/timeline?bucket=hour&hours=48", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["bucket"] == "hour"
    assert isinstance(r.json()["series"], list)


def test_analytics_requires_auth(client):
    assert client.get("/api/analytics/overview").status_code == 401
