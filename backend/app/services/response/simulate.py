"""Virtual (in-memory) simulation of response actions (Module 28 sections 4-5).

Pure data transformation. This whole package deliberately imports no process,
shell, or infrastructure client of any kind; a test in test_response.py scans
the source and fails if one appears.
"""
from __future__ import annotations

from typing import Any

from app.services.response.recommend import (
    BLOCK_SOURCE,
    DISABLE_ACCOUNT_SIMULATION,
    ISOLATE_HOST,
    SimAction,
)

DISCLAIMER = "SIMULATION ONLY - NO REAL NETWORK, HOST OR IDENTITY CHANGE WAS MADE."


def _firewall_sim(action: SimAction) -> dict[str, Any]:
    port = action.port or 0
    proto = (action.protocol or "TCP").upper()
    dest = f"{proto}/{port}" if port else proto
    return {
        "kind": "virtual_firewall",
        "target": action.target,
        "dest": dest,
        "before": [
            {"rule": "default-allow", "verdict": "ALLOW", "match": f"any -> {dest}"},
        ],
        "simulated_rule": {
            "position": "prepended",
            "verdict": "DENY",
            "source": action.target,
            "dest": dest,
            "expr": f"DENY {action.target} -> {dest}",
        },
        "after": [
            {"rule": "sim-1", "verdict": "WOULD BLOCK", "match": f"{action.target} -> {dest}"},
            {"rule": "default-allow", "verdict": "ALLOW", "match": f"any -> {dest}"},
        ],
        "expected_result": (
            f"Future {proto} connections from {action.target}"
            + (f" to port {port}" if port else "")
            + " would be denied. Existing traffic is unaffected in this model."
        ),
        "state_change": {"before": "ALLOW", "after": "WOULD BLOCK"},
        "disclaimer": DISCLAIMER,
    }


def _host_isolation_sim(action: SimAction) -> dict[str, Any]:
    host = action.target or "unknown-host"
    return {
        "kind": "virtual_host_isolation",
        "target": host,
        "before": [{"interface": "primary", "state": "CONNECTED"}],
        "simulated_change": {"expr": f"ISOLATE {host} (quarantine VLAN)"},
        "after": [{"interface": "primary", "state": "WOULD ISOLATE (management access only)"}],
        "expected_result": (
            f"{host} would be moved to an isolation segment; only investigation "
            "tooling would retain access. No connectivity was actually changed."
        ),
        "state_change": {"before": "CONNECTED", "after": "WOULD ISOLATE"},
        "disclaimer": DISCLAIMER,
    }


def _account_hold_sim(action: SimAction) -> dict[str, Any]:
    acct = action.target or "unknown-account"
    return {
        "kind": "virtual_account_hold",
        "target": acct,
        "before": [{"account": acct, "state": "ENABLED"}],
        "simulated_change": {"expr": f"HOLD {acct} pending verification"},
        "after": [{"account": acct, "state": "WOULD DISABLE (temporary hold)"}],
        "expected_result": (
            f"Account {acct} would be placed on a temporary hold requiring an "
            "administrator to re-enable. No identity system was contacted."
        ),
        "state_change": {"before": "ENABLED", "after": "WOULD DISABLE"},
        "disclaimer": DISCLAIMER,
    }


def _monitoring_sim(action: SimAction) -> dict[str, Any]:
    return {
        "kind": "virtual_monitoring",
        "target": action.target,
        "before": [{"scope": action.target, "monitoring": "baseline"}],
        "simulated_change": {"expr": f"{action.action} {action.target or ''}".strip()},
        "after": [{"scope": action.target, "monitoring": "elevated"}],
        "expected_result": action.detail
        or "Monitoring / evidence collection would be increased for this entity. "
           "This is a workflow note, not an enforcement action.",
        "state_change": {"before": "baseline", "after": "elevated"},
        "disclaimer": DISCLAIMER,
    }


def simulate_action(action: SimAction) -> dict[str, Any]:
    if action.action == BLOCK_SOURCE:
        return _firewall_sim(action)
    if action.action == ISOLATE_HOST:
        return _host_isolation_sim(action)
    if action.action == DISABLE_ACCOUNT_SIMULATION:
        return _account_hold_sim(action)
    return _monitoring_sim(action)


def simulate_all(actions: list[SimAction]) -> dict[str, Any]:
    primary = actions[0] if actions else None
    return {
        "simulation": True,
        "disclaimer": DISCLAIMER,
        "primary": simulate_action(primary) if primary else None,
        "all": [
            {"action": a.action, "target": a.target, **simulate_action(a)}
            for a in actions
        ],
        "no_real_change": True,
    }
