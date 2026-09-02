"""JSON / NDJSON application log parser."""
from __future__ import annotations

import json
from typing import Any

from app.services.parsing.base import BaseParser, ParseResult

# common vendor keys -> our raw field names (normalization does the rest)
_KEY_ALIASES = {
    "ts": "timestamp", "time": "timestamp", "@timestamp": "timestamp", "eventTime": "timestamp",
    "datetime": "timestamp", "date": "timestamp",
    "level": "severity", "lvl": "severity", "loglevel": "severity", "priority": "severity",
    "msg": "message", "text": "message", "log": "message",
    "logger": "process", "module": "process", "component": "process",
    "user": "username", "userName": "username", "account": "username", "uid": "username",
    "email": "email", "mail": "email",
    "src_ip": "source_ip", "srcIp": "source_ip", "clientIp": "source_ip", "client_ip": "source_ip",
    "remote_addr": "source_ip", "ip": "source_ip", "sourceAddress": "source_ip",
    "dst_ip": "destination_ip", "destIp": "destination_ip", "serverIp": "destination_ip",
    "src_port": "source_port", "dst_port": "destination_port",
    "method": "http_method", "httpMethod": "http_method",
    "path": "url", "uri": "url", "requestUrl": "url", "url": "url",
    "status": "response_code", "statusCode": "response_code", "http_status": "response_code",
    "event": "event_type", "eventType": "event_type", "action": "action", "type": "event_type",
    "host": "host", "hostname": "host", "server": "host",
    "service": "service", "svc": "service", "app": "service", "application": "service",
}
_LEVEL_MAP = {
    "trace": "info", "debug": "info", "info": "info", "notice": "low",
    "warn": "medium", "warning": "medium", "error": "high", "err": "high",
    "crit": "critical", "critical": "critical", "fatal": "critical", "alert": "critical",
    "emerg": "critical",
}


def _flatten(obj: dict, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in obj.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flatten(v, f"{key}."))
        elif isinstance(v, list):
            out[key] = json.dumps(v)[:500]
        else:
            out[key] = v
    return out


class JSONParser(BaseParser):
    name = "json"
    version = "1.0.0"
    format = "JSON"
    specificity = 4
    description = "Structured JSON / NDJSON application logs"

    def can_parse(self, sample: str) -> float:
        lines = [ln for ln in sample.splitlines() if ln.strip()][:25]
        if not lines:
            return 0.0
        ok = 0
        for ln in lines:
            s = ln.strip()
            if not (s.startswith("{") and s.endswith("}")):
                continue
            try:
                json.loads(s)
                ok += 1
            except ValueError:
                pass
        return round(ok / len(lines), 3)

    def parse(self, line: str) -> ParseResult:
        s = line.strip()
        try:
            obj = json.loads(s)
        except ValueError as e:
            return ParseResult(confidence=0.0, errors=[f"invalid json: {e}"], partial=True)
        if not isinstance(obj, dict):
            return ParseResult(confidence=0.2, fields={"message": s},
                               errors=["json is not an object"], partial=True)

        flat = _flatten(obj)
        fields: dict[str, Any] = {}
        for k, v in flat.items():
            if v in (None, ""):
                continue
            base = k.split(".")[-1]
            mapped = (
                _KEY_ALIASES.get(k)
                or _KEY_ALIASES.get(base)
                or _KEY_ALIASES.get(base.lower())
            )
            # Unmapped keys are still forwarded (lowercased leaf) so the
            # normalization alias tables get a chance at them.
            key = mapped or base.lower()
            fields.setdefault(key, v)
        if "severity" in fields:
            lvl = _LEVEL_MAP.get(str(fields["severity"]).lower())
            if lvl:
                fields["severity"] = lvl
            else:
                fields.pop("severity")
        # spans: highlight each mapped key's value position in the raw line
        spans = []
        for mapped, val in fields.items():
            if mapped.startswith("_"):
                continue
            needle = json.dumps(val) if not isinstance(val, str) else val
            idx = line.find(str(needle))
            if idx == -1 and isinstance(val, str):
                idx = line.find(f'"{val}"')
                if idx != -1:
                    idx += 1
            if idx != -1:
                spans.append({"field": mapped, "start": idx, "end": idx + len(str(needle)),
                              "text": str(val)})
        return ParseResult(fields=fields, confidence=0.95,
                           event_type=fields.get("event_type"), match_spans=spans)
