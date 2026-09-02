"""Linux authentication log parser (/var/log/auth.log, /var/log/secure)."""
from __future__ import annotations

import re

from app.services.parsing.base import ParseResult, RegexParser

_PREFIX = (
    r"^(?P<timestamp>[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>[\w.\-]+)\s+"
    r"(?P<process>sshd|sudo|su|login|systemd-logind|pam_unix|CRON)(?:\[(?P<pid>\d+)\])?:\s*"
    r"(?P<message>.*)$"
)

# message-level patterns (searched against the message body)
_MSG_PATTERNS: list[tuple[str, str, dict]] = [
    (
        "auth_fail_pw",
        r"Failed password for (?:invalid user )?(?P<username>\S+) from (?P<source_ip>[\da-fA-F.:]+) port (?P<source_port>\d+)",
        {"event_type": "authentication_failure", "action": "login", "status": "failure", "service": "ssh"},
    ),
    (
        "auth_ok_pw",
        r"Accepted (?:password|publickey) for (?P<username>\S+) from (?P<source_ip>[\da-fA-F.:]+) port (?P<source_port>\d+)",
        {"event_type": "authentication_success", "action": "login", "status": "success", "service": "ssh"},
    ),
    (
        "invalid_user",
        r"Invalid user (?P<username>\S+) from (?P<source_ip>[\da-fA-F.:]+)(?: port (?P<source_port>\d+))?",
        {"event_type": "authentication_failure", "action": "login", "status": "failure", "service": "ssh"},
    ),
    (
        "pam_fail",
        r"authentication failure;.*?rhost=(?P<source_ip>[\da-fA-F.:]*)\s*(?:user=(?P<username>\S+))?",
        {"event_type": "authentication_failure", "action": "login", "status": "failure"},
    ),
    (
        "session_open",
        r"session opened for user (?P<username>\S+)",
        {"event_type": "session_opened", "action": "login", "status": "success"},
    ),
    (
        "session_close",
        r"session closed for user (?P<username>\S+)",
        {"event_type": "session_closed", "action": "logout", "status": "success"},
    ),
    (
        "sudo_cmd",
        r"(?P<username>\S+) : TTY=\S+ ; PWD=\S+ ; USER=(?P<target_user>\S+) ; COMMAND=(?P<command>.+)$",
        {"event_type": "privilege_escalation", "action": "sudo", "service": "sudo"},
    ),
]


class LinuxAuthParser(RegexParser):
    name = "linux_auth"
    version = "1.0.0"
    format = "LINUX_AUTH"
    specificity = 6
    description = "Linux auth.log / secure (sshd, sudo, su, pam)"
    patterns = [_PREFIX]
    detect_hints = [
        r"\bsshd\[\d+\]:",
        r"Failed password for",
        r"Accepted password for",
        r"pam_unix\(",
        r"sudo:\s+\S+ : TTY=",
    ]
    default_event_type = "generic"

    def __init__(self) -> None:
        super().__init__()
        self._msg = [(k, re.compile(p, re.I), extra) for k, p, extra in _MSG_PATTERNS]

    def can_parse(self, sample: str) -> float:
        base = super().can_parse(sample)
        if any(rx.search(sample) for _, rx, _ in self._msg):
            base = min(1.0, base + 0.25)
        return round(base, 3)

    def _post_parse(self, line, match, result: ParseResult) -> None:
        message = result.fields.get("message", "")
        result.fields["service"] = result.fields.get("process")
        for key, rx, extra in self._msg:
            mm = rx.search(message)
            if not mm:
                continue
            for k, v in mm.groupdict().items():
                if v is not None:
                    result.fields[k] = v
                    # map message-relative spans back onto the full line
                    s, e = mm.span(k)
                    if s >= 0:
                        offset = match.start("message")
                        result.match_spans.append(
                            {"field": k, "start": offset + s, "end": offset + e, "text": v}
                        )
            result.fields.update(extra)
            result.event_type = extra.get("event_type", result.event_type)
            result.fields["_rule"] = key
            result.confidence = 0.97
            break
        else:
            result.confidence = 0.7  # matched prefix but not a known message shape
