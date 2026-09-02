"""Generic key=value log parser (logfmt-style). Low-confidence fallback."""
from __future__ import annotations

import re

from app.services.parsing.base import BaseParser, ParseResult

_TOKEN = re.compile(r'([A-Za-z_][\w.\-]*)=("([^"]*)"|\'([^\']*)\'|[^\s]+)')

_ALIASES = {
    "src_ip": "source_ip", "srcip": "source_ip", "client_ip": "source_ip", "remote_ip": "source_ip",
    "dst_ip": "destination_ip", "dest_ip": "destination_ip",
    "src_port": "source_port", "dst_port": "destination_port",
    "user": "username", "usr": "username", "account": "username",
    "lvl": "severity", "level": "severity",
    "msg": "message", "message": "message",
    "proto": "protocol",
    "method": "http_method", "status": "response_code", "code": "response_code",
    "path": "url", "uri": "url",
    "event": "event_type", "action": "action",
    "host": "host", "hostname": "host", "service": "service", "svc": "service",
}


class GenericKeyValueParser(BaseParser):
    name = "keyvalue"
    version = "1.0.0"
    format = "KEYVALUE"
    specificity = 1
    description = "Generic key=value / logfmt lines"

    def can_parse(self, sample: str) -> float:
        lines = [ln for ln in sample.splitlines() if ln.strip()][:25]
        if not lines:
            return 0.0
        scores = []
        for ln in lines:
            toks = _TOKEN.findall(ln)
            words = max(1, len(ln.split()))
            scores.append(min(1.0, len(toks) / words))
        avg = sum(scores) / len(scores)
        # keep this a fallback: cap confidence
        return round(min(avg, 0.75), 3)

    def parse(self, line: str) -> ParseResult:
        fields: dict = {}
        spans = []
        for m in _TOKEN.finditer(line):
            key = m.group(1).lower()
            val = m.group(3) if m.group(3) is not None else (
                m.group(4) if m.group(4) is not None else m.group(2)
            )
            mapped = _ALIASES.get(key, f"kv_{key}")
            fields[mapped] = val
            spans.append({"field": mapped, "start": m.start(2), "end": m.end(2), "text": val})
        if not fields:
            return ParseResult(confidence=0.0, errors=["no key=value tokens"], partial=True)
        if "message" not in fields:
            fields["message"] = line
        return ParseResult(fields=fields, confidence=min(0.7, 0.3 + 0.05 * len(fields)),
                           event_type=fields.get("event_type"), match_spans=spans)
