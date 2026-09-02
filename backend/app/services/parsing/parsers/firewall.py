"""Firewall log parser.

Handles two common shapes:
  * Linux netfilter/iptables kernel logs (SRC=/DST=/SPT=/DPT=/PROTO=)
  * Vendor key=value firewall logs (action=/srcip=/dstip=/proto=), e.g. Fortinet-style
"""
from __future__ import annotations

import re

from app.services.parsing.base import ParseResult, BaseParser

_IPTABLES = re.compile(
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})?.*?"
    r"(?:kernel:.*?)?(?P<fw_action>DROP|ACCEPT|REJECT|DENY)\b.*?"
    r"(?:IN=(?P<in_if>\S*))?.*?(?:OUT=(?P<out_if>\S*))?.*?"
    r"SRC=(?P<source_ip>\S+)\s+DST=(?P<destination_ip>\S+).*?"
    r"(?:PROTO=(?P<protocol>\S+))?"
    r"(?:.*?SPT=(?P<source_port>\d+))?"
    r"(?:.*?DPT=(?P<destination_port>\d+))?",
    re.I,
)
_KV_TOKEN = re.compile(r'(\w[\w.\-]*)=("([^"]*)"|\S+)')

_KV_FIELD_MAP = {
    "srcip": "source_ip", "src": "source_ip", "src_ip": "source_ip",
    "dstip": "destination_ip", "dst": "destination_ip", "dst_ip": "destination_ip",
    "srcport": "source_port", "spt": "source_port",
    "dstport": "destination_port", "dpt": "destination_port",
    "proto": "protocol", "protocol": "protocol",
    "action": "fw_action", "act": "fw_action", "disposition": "fw_action",
    "user": "username", "usr": "username",
    "devname": "host", "hostname": "host", "dvc": "host",
    "service": "service", "app": "service", "svc": "service",
}
_PROTO_NUM = {"6": "tcp", "17": "udp", "1": "icmp"}


class FirewallParser(BaseParser):
    name = "firewall"
    version = "1.0.0"
    format = "FIREWALL"
    specificity = 5
    description = "Netfilter/iptables kernel logs and vendor key=value firewall logs"

    _FW_HINTS = re.compile(
        r"\b(IPTABLES|netfilter|SRC=\d|DPT=\d|action=(?:deny|accept|allow|drop)|"
        r"srcip=|dstip=|devname=|firewall|fw_action)\b",
        re.I,
    )

    def can_parse(self, sample: str) -> float:
        lines = [ln for ln in sample.splitlines() if ln.strip()][:25]
        if not lines:
            return 0.0
        hits = 0
        for ln in lines:
            if _IPTABLES.search(ln) or ("=" in ln and _FW_KV_OK(ln)):
                hits += 1
        score = hits / len(lines)
        if self._FW_HINTS.search(sample):
            score = min(1.0, score + 0.2)
        return round(score, 3)

    def parse(self, line: str) -> ParseResult:
        m = _IPTABLES.search(line)
        if m and m.group("source_ip"):
            f = {k: v for k, v in m.groupdict().items() if v}
            spans = [
                {"field": k, "start": m.span(k)[0], "end": m.span(k)[1], "text": m.group(k)}
                for k in m.groupdict()
                if m.group(k) is not None and m.span(k)[0] >= 0
            ]
            return self._finish(f, spans, 0.95)

        # key=value
        f: dict = {}
        spans = []
        for tm in _KV_TOKEN.finditer(line):
            key = tm.group(1).lower()
            val = tm.group(3) if tm.group(3) is not None else tm.group(2)
            mapped = _KV_FIELD_MAP.get(key, f"kv_{key}")
            f[mapped] = val
            spans.append({"field": mapped, "start": tm.start(2), "end": tm.end(2), "text": val})
        if not any(k in f for k in ("source_ip", "destination_ip", "fw_action")):
            return ParseResult(confidence=0.0, errors=["not a firewall line"], partial=True)
        return self._finish(f, spans, 0.9)

    def _finish(self, f: dict, spans: list, conf: float) -> ParseResult:
        act = str(f.pop("fw_action", "")).lower()
        if act in ("drop", "deny", "reject", "block"):
            event_type, action, status, sev = "connection_denied", "deny", "blocked", "medium"
        elif act in ("accept", "allow", "permit"):
            event_type, action, status, sev = "connection_allowed", "allow", "allowed", "info"
        else:
            event_type, action, status, sev = "generic", act or None, None, "info"
        proto = str(f.get("protocol", "")).lower()
        f["protocol"] = _PROTO_NUM.get(proto, proto) or None
        f["event_type"] = event_type
        if action:
            f["action"] = action
        if status:
            f["status"] = status
        f.setdefault("severity", sev)
        f.setdefault("service", "firewall")
        return ParseResult(fields={k: v for k, v in f.items() if v is not None},
                           confidence=conf, event_type=event_type, match_spans=spans)


def _FW_KV_OK(line: str) -> bool:
    low = line.lower()
    return any(t in low for t in ("srcip=", "src=", "action=", "dpt=", "dstip=", "devname="))
