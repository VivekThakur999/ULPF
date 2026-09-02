"""Syslog parsers - RFC 3164 (BSD) and RFC 5424."""
from __future__ import annotations

import re

from app.services.parsing.base import ParseResult, RegexParser

_RFC3164 = (
    r"^(?:<(?P<pri>\d{1,3})>)?"
    r"(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>[\w.\-]+)\s+"
    r"(?P<process>[^:\[\s]+)(?:\[(?P<pid>\d+)\])?:\s*"
    r"(?P<message>.*)$"
)
_RFC5424 = (
    r"^<(?P<pri>\d{1,3})>(?P<version>\d)\s+"
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T[\d:.]+(?:Z|[+\-]\d{2}:\d{2}))\s+"
    r"(?P<host>\S+)\s+(?P<process>\S+)\s+(?P<pid>\S+)\s+(?P<msgid>\S+)\s+"
    r"(?:\[.*?\]|-)\s*(?P<message>.*)$"
)


class SyslogParser(RegexParser):
    name = "syslog"
    version = "1.0.0"
    format = "SYSLOG"
    specificity = 2
    description = "Generic syslog (RFC 3164 / RFC 5424)"
    patterns = [_RFC5424, _RFC3164]
    detect_hints = [r"^<\d{1,3}>", r"[A-Z][a-z]{2}\s+\d{1,2}\s\d{2}:\d{2}:\d{2}\s\S+\s\S+"]
    default_event_type = "generic"

    _SEV_BY_FACILITY = {0: "critical", 1: "high", 2: "critical", 3: "high", 4: "medium"}

    def _post_parse(self, line, match, result: ParseResult) -> None:
        pri = result.fields.pop("pri", None)
        if pri is not None:
            try:
                p = int(pri)
                sev = p % 8
                result.fields["_syslog_severity_num"] = sev
                result.fields["severity"] = (
                    "critical" if sev <= 2 else "high" if sev == 3
                    else "medium" if sev == 4 else "low" if sev == 5 else "info"
                )
            except ValueError:
                pass
        proc = result.fields.get("process", "")
        if proc:
            result.fields["service"] = proc
        # crude event typing from message keywords
        msg = result.fields.get("message", "").lower()
        if "authentication failure" in msg or "failed password" in msg:
            result.event_type = "authentication_failure"
        elif "accepted password" in msg or "session opened" in msg:
            result.event_type = "session_opened"
