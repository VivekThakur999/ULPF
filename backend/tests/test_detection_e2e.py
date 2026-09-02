"""End-to-end: ingest the multi-source brute-force scenario, verify one
correlated, risk-scored alert with an incident timeline."""
import time
from pathlib import Path

import pytest

_SCEN = Path(__file__).resolve().parents[2] / "sample_logs" / "security_scenarios" / "scenario_brute_force"


def _wait(client, headers, job_id):
    for _ in range(80):
        j = client.get(f"/api/ingestion/jobs/{job_id}", headers=headers).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            return j
        time.sleep(0.2)
    raise AssertionError("job timeout")


@pytest.fixture(scope="module")
def scenario_loaded(client_module, analyst_headers_module):
    client, headers = client_module, analyst_headers_module
    for f in ["firewall.log", "linux.log", "application.jsonl", "windows.jsonl"]:
        r = client.post("/api/ingestion/upload", headers=headers,
                        files={"file": (f, (_SCEN / f).read_bytes(), "text/plain")},
                        data={"source_name": f.split(".")[0]})
        _wait(client, headers, r.json()["id"])
    return client, headers


def test_events_normalize_to_one_schema_across_sources(scenario_loaded):
    client, headers = scenario_loaded
    r = client.get("/api/logs?limit=200", headers=headers)
    assert r.status_code == 200
    items = r.json()["items"]
    sources = {e["source"] for e in items}
    assert {"firewall", "linux", "application", "windows"} <= sources
    # every event has the same schema version and shape
    assert all(e["schema_version"] == "1.0" for e in items)
    # the attacker IP is one pseudonym everywhere it appears - check via the
    # pseudonymized-search path so the assertion is scoped to this scenario.
    tok = client.get("/api/logs/pseudonymize?value=192.168.1.50&kind=ip", headers=headers).json()
    attacker = tok["pseudonym"]
    assert attacker.startswith("IP_")
    for src in ("firewall", "linux", "application", "windows"):
        hits = client.get(f"/api/logs?source={src}&source_ip={attacker}&limit=50",
                          headers=headers).json()
        assert hits["total"] >= 1, f"attacker pseudonym not found in {src}"


def test_search_pseudonymizes_raw_ip_query(scenario_loaded):
    client, headers = scenario_loaded
    r = client.get("/api/logs?source_ip=192.168.1.50", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert "pseudonymized" in (body["note"] or "")


def test_detection_creates_one_correlated_alert(scenario_loaded):
    client, headers = scenario_loaded
    client.post("/api/detection/run", headers=headers, json={"since_hours": 24})
    alerts = client.get("/api/alerts", headers=headers).json()["items"]
    assert len(alerts) >= 1
    top = alerts[0]
    assert top["risk_score"] >= 65
    assert top["severity"] in ("high", "critical")
    # multiple rules contributed
    assert "RULE_" in top["description"]
    # transparent risk breakdown
    factors = top["risk_breakdown"]["factors"]
    assert len(factors) >= 3
    assert all("detail" in f and f["points"] > 0 for f in factors)
    assert any(f["factor"] == "cross_source_correlation" for f in factors)
    # recommended response is a recommendation only
    assert top["recommended_response"]["auto_execute"] is False


def test_alert_detail_has_incident_timeline(scenario_loaded):
    client, headers = scenario_loaded
    alert_id = client.get("/api/alerts", headers=headers).json()["items"][0]["id"]
    d = client.get(f"/api/alerts/{alert_id}", headers=headers).json()
    tl = d["timeline"]
    assert len(tl) >= 5
    # timeline ordered by time
    times = [t["ts"] for t in tl if t["ts"]]
    assert times == sorted(times)
    # spans multiple sources
    assert len({t["source"] for t in tl}) >= 3
    assert len(d["related_events"]) >= 5


def test_alert_status_workflow(scenario_loaded):
    client, headers = scenario_loaded
    alert_id = client.get("/api/alerts", headers=headers).json()["items"][0]["id"]
    r = client.put(f"/api/alerts/{alert_id}", headers=headers,
                   json={"status": "INVESTIGATING", "resolution_note": "triaging"})
    assert r.status_code == 200
    assert r.json()["status"] == "INVESTIGATING"
    bad = client.put(f"/api/alerts/{alert_id}", headers=headers, json={"status": "BOGUS"})
    assert bad.status_code == 422


def test_log_detail_shows_pipeline_and_related(scenario_loaded):
    client, headers = scenario_loaded
    ev = client.get("/api/logs?event_type=authentication_failure&limit=1", headers=headers).json()["items"][0]
    d = client.get(f"/api/logs/{ev['id']}", headers=headers).json()
    assert [s["stage"] for s in d["pipeline"]][:3] == ["security_shield", "format_detection", "parsing"]
    assert d["raw_log"]["content"]
    assert d["event"]["raw_log"]  # original preserved
    assert isinstance(d["related_events"], list)
