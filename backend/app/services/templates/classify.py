"""Tokenization + conservative variable classification for template mining.

Deterministic, regex-only - no ML, no external dependency. Log content is
only ever inspected as text; nothing here executes or interprets it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Tokens are simply whitespace-delimited runs. Exact inter-token separators are
# captured separately, so reconstruction stays byte-exact regardless of odd
# spacing, tabs, or quote characters in the data.
_TOKEN_RE = re.compile(r"\S+")

# Variable types that are effectively always unique per occurrence - safe to
# treat a position as a variable the moment it is classified as one of these.
# "number" and "quoted" are deliberately excluded: a constant port or a
# constant quoted user-agent should stay literal unless it actually varies.
HIGH_CARDINALITY_TYPES = frozenset(
    {"ipv4", "ipv6", "uuid", "mac", "timestamp", "hash", "email", "url"}
)

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_MAC = re.compile(r"^(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
_IPV4 = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?::\d{1,5})?$"
)
_IPV6_GROUP = re.compile(r"^[0-9a-fA-F]{0,4}$")
_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_URL = re.compile(r"^https?://\S+$")
_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+\-]\d{2}:?\d{2})?$"
    r"|^\d{2}:\d{2}:\d{2}(?:\.\d+)?$"
    r"|^\[\d+\.\d+\]$"
)
_QUOTED = re.compile(r'^"[^"]*"$|^\'[^\']*\'$')
_NUMBER = re.compile(r"^[+-]?\d+(?:\.\d+)?%?$")
_HEX = re.compile(r"^[0-9a-fA-F]+$")

# order matters: first match wins
_CLASSIFIERS: list[tuple[str, re.Pattern]] = [
    ("quoted", _QUOTED),
    ("uuid", _UUID),
    ("mac", _MAC),
    ("ipv4", _IPV4),
    ("timestamp", _TIMESTAMP),
    ("email", _EMAIL),
    ("url", _URL),
    ("number", _NUMBER),
]


def _looks_like_ipv6(token: str) -> bool:
    # A bare "hh:mm:ss" style timestamp technically matches a loose IPv6
    # regex, so require either the "::" abbreviation or at least 4 groups -
    # real IPv6 addresses have up to 8; times only ever have 2-3 colons.
    if ":" not in token:
        return False
    body = token
    if "::" in body:
        parts = [p for p in body.split(":") if p]
        return len(parts) >= 2 and all(_IPV6_GROUP.match(p) for p in parts)
    parts = body.split(":")
    return len(parts) >= 4 and all(_IPV6_GROUP.match(p) and p for p in parts)


def classify_token(token: str) -> str | None:
    """Return a variable-type tag for an "obviously variable" token, else None."""
    for name, rx in _CLASSIFIERS:
        if rx.match(token):
            return name
    if _looks_like_ipv6(token):
        return "ipv6"
    # hex-looking hash: long hex runs, or shorter ones that actually contain a
    # letter (so we don't misfire on plain small integers).
    if _HEX.match(token) and len(token) >= 8:
        if len(token) >= 32 or any(c in "abcdefABCDEF" for c in token):
            return "hash"
    return None


@dataclass
class TokenSpan:
    text: str
    start: int
    end: int


def tokenize(line: str) -> list[TokenSpan]:
    return [TokenSpan(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(line)]


def separators_for(line: str, spans: list[TokenSpan]) -> tuple[list[str], str]:
    """Return (separators-before-each-token, trailing-text-after-last-token).

    Concatenating sep[0] + tok[0] + sep[1] + tok[1] + ... + trailing reproduces
    `line` exactly.
    """
    seps: list[str] = []
    prev_end = 0
    for sp in spans:
        seps.append(line[prev_end:sp.start])
        prev_end = sp.end
    trailing = line[prev_end:]
    return seps, trailing
