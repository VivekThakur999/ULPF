"""Deterministic response recommendation (Module 28).

Maps an alert's real, server-retrieved evidence (rule + entity + correlation)
to a fixed recommendation and a list of *representational* simulated actions.
No AI, no randomness, no infrastructure access. If nothing safe applies it
returns "no recommendation" rather than inventing one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SIMULATION_ONLY = "SIMULATION_ONLY"

# safe, representational action kinds only
BLOCK_SOURCE = "BLOCK_SOURCE"
MONITOR_SOURCE = "MONITOR_SOURCE"
ISOLATE_HOST = "ISOLATE_HOST"
DISABLE_ACCOUNT_SIMULATION = "DISABLE_ACCOUNT_SIMULATION"
COLLECT_EVIDENCE = "COLLECT_EVIDENCE"
INCREASE_MONITORING = "INCREASE_MONITORING"


@dataclass
class SimAction:
    action: str
    target: str | None = None
    port: int | None = None
    protocol: str | None = None
    detail: str = ""
    mode: str = SIMULATION_ONLY

    def to_dict(self) -> dict:
        return {
            "action": self.action, "target": self.target, "port": self.port,
            "protocol": self.protocol, "detail": self.detail, "mode": self.mode,
        }


@dataclass
class Recommendation:
    category: str                       # e.g. BRUTE_FORCE, PORT_SCAN, ...
    available: bool
    label: str                          # "Block source IP"
    rationale: str                      # why, grounded in the evidence
    actions: list[SimAction] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "available": self.available,
            "label": self.label,
            "rationale": self.rationale,
            "actions": [a.to_dict() for a in self.actions],
            "evidence": self.evidence,
        }


_NO_RECOMMENDATION = Recommendation(
    category="NONE", available=False,
    label="No automated response recommendation available.",
    rationale="This alert does not map to a safe, well-defined response pattern.",
)

# which rule keys belong to which response category
_RULE_CATEGORY = {
    "RULE_1": "BRUTE_FORCE",
    "RULE_2": "BRUTE_FORCE",
    "RULE_3": "BRUTE_FORCE",
    "RULE_4": "SUSPICIOUS_AUTHENTICATION",
    "RULE_5": "PORT_SCAN",
    "RULE_6": "SUSPICIOUS_AUTHENTICATION",
    "RULE_7": "SUSPICIOUS_EXECUTION",
    "RULE_8": "ANOMALOUS_VOLUME",
}


def _common_dest(correlation: dict[str, Any]) -> tuple[int | None, str | None]:
    """Best-effort dominant destination port/protocol from correlated events."""
    ports = correlation.get("dest_ports") or {}
    protos = correlation.get("protocols") or {}
    port = None
    proto = None
    if ports:
        port = int(max(ports, key=ports.get))
    if protos:
        proto = str(max(protos, key=protos.get)).upper()
    return port, proto


def recommend(
    *,
    rule_keys: list[str],
    entity: dict[str, Any],
    correlation: dict[str, Any],
    counts: dict[str, Any],
    shield_verdicts: list[str],
) -> Recommendation:
    categories = {_RULE_CATEGORY.get(k) for k in rule_keys if _RULE_CATEGORY.get(k)}
    if "SUSPICIOUS_EXECUTION" in categories or any(
        v in ("WEAPONIZED_LOG", "SUSPICIOUS") for v in shield_verdicts
    ):
        category = "SUSPICIOUS_EXECUTION"
    elif "BRUTE_FORCE" in categories:
        category = "BRUTE_FORCE"
    elif "PORT_SCAN" in categories:
        category = "PORT_SCAN"
    elif "SUSPICIOUS_AUTHENTICATION" in categories:
        category = "SUSPICIOUS_AUTHENTICATION"
    elif "ANOMALOUS_VOLUME" in categories:
        category = "ANOMALOUS_VOLUME"
    else:
        return _NO_RECOMMENDATION

    src_ip = entity.get("source_ip")
    username = entity.get("username")
    host_list = correlation.get("hosts") or []
    host = entity.get("host") or (host_list[0] if host_list else None)
    source_list = correlation.get("sources") or []
    port, proto = _common_dest(correlation)
    ev = {
        "rules": rule_keys,
        "failed_authentications": counts.get("auth_failures"),
        "successful_authentications": counts.get("auth_successes"),
        "denied_connections": counts.get("connections_denied"),
        "affected_hosts": host_list,
        "sources_correlated": source_list,
        "shield_verdicts": shield_verdicts,
        "entity": entity,
    }

    if category == "BRUTE_FORCE" and src_ip:
        return Recommendation(
            category="BRUTE_FORCE", available=True,
            label="Block source IP",
            rationale=(
                f"{counts.get('auth_failures', 0)} failed authentications from "
                f"{src_ip} across {counts.get('sources', 1)} source(s) "
                f"({', '.join(host_list) or 'one host'})."
            ),
            actions=[
                SimAction(BLOCK_SOURCE, target=src_ip, port=port or 22,
                          protocol=proto or "TCP",
                          detail="Perimeter deny for future matching traffic (representation)."),
                SimAction(MONITOR_SOURCE, target=src_ip,
                          detail="Watch-list the source for further authentication attempts."),
                SimAction(INCREASE_MONITORING, target="authentication",
                          detail="Raise logging/alert sensitivity for the targeted hosts."),
            ],
            evidence=ev,
        )

    if category == "PORT_SCAN" and src_ip:
        return Recommendation(
            category="PORT_SCAN", available=True,
            label="Block or closely monitor the scanning source",
            rationale=(
                f"{counts.get('connections_denied', 0)} denied connection(s) followed by "
                f"authentication activity from {src_ip}."
            ),
            actions=[
                SimAction(BLOCK_SOURCE, target=src_ip, port=port, protocol=proto or "TCP",
                          detail="Deny the source at the network edge (representation)."),
                SimAction(INCREASE_MONITORING, target="network",
                          detail="Increase flow/connection monitoring for the target segment."),
                SimAction(COLLECT_EVIDENCE, target=src_ip,
                          detail="Snapshot related firewall + connection logs for review."),
            ],
            evidence=ev,
        )

    if category == "SUSPICIOUS_AUTHENTICATION":
        target = username or src_ip
        return Recommendation(
            category="SUSPICIOUS_AUTHENTICATION", available=bool(target),
            label=(f"Require step-up authentication for {target}" if username
                   else f"Monitor and rate-limit source {src_ip}"),
            rationale=(
                "Repeated authentication failures"
                + (" followed by a success" if counts.get("auth_successes") else "")
                + f" for {'account ' + username if username else 'source ' + str(src_ip)}."
            ),
            actions=[
                (SimAction(DISABLE_ACCOUNT_SIMULATION, target=username,
                           detail="Represent a temporary account hold pending verification.")
                 if username else
                 SimAction(MONITOR_SOURCE, target=src_ip,
                           detail="Watch-list and rate-limit the source.")),
                SimAction(MONITOR_SOURCE, target=src_ip or username,
                          detail="Track subsequent authentication events for this entity."),
                SimAction(COLLECT_EVIDENCE, target=target,
                          detail="Gather the authentication timeline for the incident record."),
            ],
            evidence=ev,
        )

    if category == "SUSPICIOUS_EXECUTION":
        return Recommendation(
            category="SUSPICIOUS_EXECUTION", available=True,
            label=(f"Isolate host {host} (simulation only) and collect logs" if host
                   else "Collect logs and increase monitoring"),
            rationale=(
                "The Security Shield flagged weaponized / injection log content"
                + (f" involving host {host}" if host else "")
                + ". Treat as possible exploitation attempt."
            ),
            actions=[
                *( [SimAction(ISOLATE_HOST, target=host,
                             detail="Represent network isolation of the host for triage.")]
                   if host else [] ),
                SimAction(COLLECT_EVIDENCE, target=host or "affected_systems",
                          detail="Preserve the flagged raw logs and related events."),
                SimAction(INCREASE_MONITORING, target=host or "environment",
                          detail="Elevate monitoring around the affected systems."),
            ],
            evidence=ev,
        )

    if category == "ANOMALOUS_VOLUME":
        subject = src_ip or (counts.get("sources") and "the source") or "the source"
        return Recommendation(
            category="ANOMALOUS_VOLUME", available=True,
            label=f"Increase monitoring on {subject}",
            rationale="Event volume from this source spiked well above its recent baseline.",
            actions=[
                SimAction(INCREASE_MONITORING, target=src_ip or "source",
                          detail="Raise sampling/alert thresholds for the source."),
                SimAction(MONITOR_SOURCE, target=src_ip,
                          detail="Watch-list the source for sustained anomalous volume."),
                SimAction(COLLECT_EVIDENCE, target=src_ip,
                          detail="Capture a window of the burst for analysis."),
            ],
            evidence=ev,
        )

    return _NO_RECOMMENDATION
