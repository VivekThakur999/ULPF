"""Security Shield / anti-log-injection pre-check (Module 4).

A heuristic screen run BEFORE parsing. It is NOT a malware detector. Log content
is never executed or interpreted here - we only inspect bytes and structure.

Two categories of finding:

* ``injection`` - the log content threatens the pipeline / downstream consumers
  itself (terminal escapes, control chars, CRLF log-forging, ${jndi:} lookups,
  format-string specifiers). These drive quarantine.
* ``payload`` - the log merely *records* an attack someone attempted against a
  monitored system (an SQLi string in a URL, ``<script>`` in a form field). The
  log is still legitimate and IS processed & stored; it is only flagged so an
  analyst - and detection RULE_7 - can see it.

Verdicts: SAFE | SUSPICIOUS | WEAPONIZED_LOG
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_DANGEROUS_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_ANSI_OSC = re.compile(r"\x1b\][^\x07]*(?:\x07|\x1b\\)")

# (name, regex, severity, category)
_PATTERNS: list[tuple[str, str, str, str]] = [
    ("crlf_injection",
     r"(?:%0d%0a|%0a%0d|%0a|%0d|\\r\\n).{0,40}"
     r"(?:\bLOGIN\b|\bAUTH\b|status=|sshd\[|Accepted password|Failed password|"
     r"[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})",
     "high", "injection"),
    ("log4shell", r"\$\{jndi:(?:ldap|ldaps|rmi|dns|nis|iiop|corba|nds|http):",
     "critical", "injection"),
    ("template_injection", r"\$\{(?:env|sys|java|lower|upper|date|main|jndi):",
     "high", "injection"),
    ("format_string", r"(?:%n){2,}|%\d*\$n",
     "high", "injection"),
    ("literal_escape_seq", r"\\x1b[\[\]]|\\033[\[\]]|\\e\[|\\u001b",
     "high", "injection"),
    ("xxe", r"<!ENTITY\b|<!DOCTYPE\b[^>]*\bSYSTEM\b",
     "high", "injection"),
    ("script_tag", r"<\s*script[\s/>]", "high", "payload"),
    ("event_html", r"on(?:error|load|click|mouseover)\s*=\s*['\"]?", "medium", "payload"),
    ("sql_injection",
     r"(?i)(?:\bunion\s+select\b|\bor\s+1\s*=\s*1\b|'\s*or\s*'?1'?\s*=\s*'?1|"
     r";\s*drop\s+table\b|\bxp_cmdshell\b)",
     "high", "payload"),
    ("path_traversal", r"(?:\.\./){2,}|(?:\.\.\\){2,}|%2e%2e%2f|/etc/passwd\b",
     "medium", "payload"),
    ("shell_metachars", r"\$\(|\|\s*(?:sh|bash|nc|curl|wget|python)\b|`[^`]+`",
     "medium", "payload"),
]
_COMPILED = [(n, re.compile(rx), sev, cat) for n, rx, sev, cat in _PATTERNS]

_MAX_LINE = 32 * 1024
_SEV_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class ShieldVerdict:
    verdict: str = "SAFE"
    indicators: list[dict] = field(default_factory=list)
    summary: str = "no injection indicators"
    quarantine: bool = False

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "indicators": self.indicators,
            "summary": self.summary,
            "quarantine": self.quarantine,
        }


def screen_line(line: str, *, quarantine_injection: bool = True) -> ShieldVerdict:
    indicators: list[dict] = []

    def note(kind: str, sev: str, cat: str, detail: str) -> None:
        indicators.append({"type": kind, "severity": sev, "category": cat, "detail": detail})

    if len(line) > _MAX_LINE:
        note("oversize_line", "medium", "injection", f"{len(line)} bytes")

    if _ANSI_ESCAPE.search(line) or _ANSI_OSC.search(line):
        note("terminal_escape_sequence", "high", "injection",
             "ANSI/OSC escape sequence in log content")

    ctrl = _DANGEROUS_CONTROL.findall(line.replace("\x1b", ""))
    if ctrl:
        codes = sorted({f"0x{ord(c):02x}" for c in ctrl})
        note("dangerous_control_chars", "high", "injection", ", ".join(codes))

    for name, rx, sev, cat in _COMPILED:
        m = rx.search(line)
        if m:
            note(name, sev, cat, _safe_snippet(m.group(0)))

    if not indicators:
        return ShieldVerdict()

    injection = [i for i in indicators if i["category"] == "injection"]
    payload = [i for i in indicators if i["category"] == "payload"]
    inj_max = max((_SEV_RANK[i["severity"]] for i in injection), default=0)

    if inj_max >= 4 or (inj_max == 3 and len(injection) >= 2):
        verdict, quarantine = "WEAPONIZED_LOG", True
    elif injection:
        verdict, quarantine = "SUSPICIOUS", quarantine_injection
    else:
        # payload only: the log records an attack but is itself legitimate
        verdict, quarantine = "SUSPICIOUS", False

    types = ", ".join(sorted({i["type"] for i in indicators}))
    return ShieldVerdict(
        verdict=verdict,
        indicators=indicators,
        summary=f"{verdict}: {types}",
        quarantine=quarantine,
    )


def _safe_snippet(s: str, limit: int = 120) -> str:
    cleaned = _DANGEROUS_CONTROL.sub("\ufffd", s.replace("\x1b", "\\x1b"))
    return cleaned[:limit]
