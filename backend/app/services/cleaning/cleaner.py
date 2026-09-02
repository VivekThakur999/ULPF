"""Cleaning & validation engine (Module 7).

Operates on the flat parsed-field dict BEFORE normalization. It never silently
drops information: rejected values are preserved under `<field>_raw` and a
warning is recorded.
"""
from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as _dateparser

_WS = re.compile(r"\s+")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_IP_FIELDS = ("source_ip", "destination_ip", "src_ip", "dst_ip", "ip", "ipaddress",
              "client_ip", "remote_addr")
_PORT_FIELDS = ("source_port", "destination_port", "src_port", "dst_port", "port",
                "spt", "dpt", "sport", "dport", "ipport")
_TS_FIELDS = ("timestamp", "time", "ts", "date", "datetime", "@timestamp", "eventtime",
              "timecreated", "event_time")


def _valid_timestamp(value: Any) -> bool:
    if isinstance(value, datetime):
        return True
    s = str(value).strip()
    if not s:
        return False
    if s.replace(".", "", 1).isdigit() and len(s.split(".")[0]) in (10, 13):
        return True
    try:
        _dateparser.parse(s, default=datetime(2000, 1, 1, tzinfo=timezone.utc))
        return True
    except (ValueError, OverflowError, TypeError):
        return False


def _clean_ws(value: str) -> str:
    return _WS.sub(" ", value.strip())


def valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


def valid_port(value: Any) -> bool:
    try:
        p = int(str(value).strip())
        return 0 <= p <= 65535
    except (ValueError, TypeError):
        return False


def clean_fields(
    fields: dict[str, Any],
) -> tuple[dict[str, Any], list[dict], list[str], bool]:
    """Return (cleaned_fields, transformations, warnings, had_invalid)."""
    cleaned: dict[str, Any] = {}
    transforms: list[dict] = []
    warnings: list[str] = []
    had_invalid = False

    for key, value in fields.items():
        if value is None:
            continue

        if isinstance(value, str):
            if _CTRL.search(value):
                value = _CTRL.sub("", value)
                transforms.append({"type": "strip_control_chars", "field": key})
            stripped = value.strip()
            if stripped == "":
                continue
            collapsed = _clean_ws(stripped)
            if collapsed != value:
                transforms.append({"type": "trim_whitespace", "field": key})
            value = collapsed
            # strip stray surrounding quotes
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
                transforms.append({"type": "unquote", "field": key})

        low = key.lower()

        if low in _TS_FIELDS and not _valid_timestamp(value):
            warnings.append(f"{key}: '{value}' is not a parseable timestamp")
            cleaned[f"{key}_raw"] = value
            had_invalid = True
            continue

        if low in _IP_FIELDS and isinstance(value, str):
            if not valid_ip(value):
                warnings.append(f"{key}: '{value}' is not a valid IP address")
                cleaned[f"{key}_raw"] = value
                had_invalid = True
                continue
            try:
                value = str(ipaddress.ip_address(value))  # canonical form
            except ValueError:
                pass

        elif low in _PORT_FIELDS:
            if not valid_port(value):
                warnings.append(f"{key}: '{value}' is not a valid port")
                cleaned[f"{key}_raw"] = value
                had_invalid = True
                continue
            value = int(str(value).strip())
            transforms.append({"type": "coerce_int", "field": key})

        elif low in ("response_code", "status_code", "http_status"):
            try:
                value = int(str(value).strip())
            except (ValueError, TypeError):
                warnings.append(f"{key}: '{value}' is not a numeric status code")
                cleaned[f"{key}_raw"] = value
                had_invalid = True
                continue

        cleaned[key] = value

    return cleaned, transforms, warnings, had_invalid
