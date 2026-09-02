"""Supplementary field extraction (Module 8).

Runs after parsing/cleaning. Fills gaps by scanning the raw line / message for
well-known identifier shapes, and assigns per-field confidence.
"""
from __future__ import annotations

import re
from typing import Any

_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_MAC = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
_URL = re.compile(r"\bhttps?://[^\s\"'<>]+")

_PARSED_CONF = 0.95  # confidence for a value the parser extracted directly


def extract_supplementary(
    fields: dict[str, Any],
    *,
    raw_line: str,
    parse_confidence: float,
) -> tuple[dict[str, Any], dict[str, float], list[str]]:
    out = dict(fields)
    confidence: dict[str, float] = {}
    found: list[str] = []

    for k, v in fields.items():
        if v not in (None, ""):
            confidence[k.lower()] = round(max(0.5, parse_confidence), 3)

    text = out.get("message") or raw_line
    if not isinstance(text, str):
        text = raw_line

    if "email" not in out:
        m = _EMAIL.search(text)
        if m:
            out["email"] = m.group(0)
            confidence["email"] = 0.8
            found.append("email")

    if "source_ip" not in out and "src_ip" not in out:
        ips = _IPV4.findall(raw_line)
        if ips:
            out["source_ip"] = ips[0]
            confidence["source_ip"] = 0.6
            found.append("source_ip")
            if len(ips) > 1 and "destination_ip" not in out:
                out["destination_ip"] = ips[1]
                confidence["destination_ip"] = 0.45
                found.append("destination_ip")

    if "url" not in out:
        m = _URL.search(text)
        if m:
            out["url"] = m.group(0)
            confidence["url"] = 0.7
            found.append("url")

    if "mac" not in out:
        m = _MAC.search(raw_line)
        if m:
            out["mac_address"] = m.group(0)
            confidence["mac_address"] = 0.7
            found.append("mac_address")

    # ensure a message field always exists
    if "message" not in out or not out["message"]:
        out["message"] = raw_line.strip()

    return out, confidence, found
