"""Universal normalization (Modules 8-11): map arbitrary parsed fields onto the
canonical Universal Log Event, coercing types and building the validated model.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from dateutil import parser as date_parser

from app.schemas.event import EVENT_TYPES, UniversalLogEvent
from app.services.normalization.aliases import (
    FIELD_ALIASES,
    INT_FIELDS,
    SEVERITY_ALIASES,
)

_CANONICAL_FIELDS = set(UniversalLogEvent.model_fields.keys())

_EVENT_TYPE_ALIASES = {
    "auth_failure": "authentication_failure", "authfail": "authentication_failure",
    "login_failed": "authentication_failure", "failed_login": "authentication_failure",
    "authentication failure": "authentication_failure",
    "auth_success": "authentication_success", "login_success": "authentication_success",
    "logon": "authentication_success", "login": "authentication_success",
    "request": "http_request", "http": "http_request", "access": "http_request",
    "deny": "connection_denied", "denied": "connection_denied", "block": "connection_denied",
    "allow": "connection_allowed", "accept": "connection_allowed", "permit": "connection_allowed",
}


def _coerce_int(value: Any) -> int | None:
    try:
        i = int(str(value).strip())
        return i
    except (ValueError, TypeError):
        return None


def parse_timestamp(value: Any, *, reference_year: int | None = None) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    # epoch seconds / millis
    if s.replace(".", "", 1).isdigit() and len(s.split(".")[0]) in (10, 13):
        num = float(s)
        if num > 1e12:
            num /= 1000.0
        try:
            return datetime.fromtimestamp(num, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        dt = date_parser.parse(s, default=datetime(
            reference_year or datetime.now(timezone.utc).year, 1, 1, tzinfo=timezone.utc
        ))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError, TypeError):
        return None


def normalize_severity(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    return SEVERITY_ALIASES.get(s, s if s in {"info", "low", "medium", "high", "critical"} else None)


def normalize_event_type(value: Any) -> str | None:
    if not value:
        return None
    s = str(value).strip().lower().replace(" ", "_")
    if s in EVENT_TYPES:
        return s
    return _EVENT_TYPE_ALIASES.get(s, s)


class NormalizationResult:
    def __init__(self) -> None:
        self.canonical: dict[str, Any] = {}
        self.extra: dict[str, Any] = {}
        self.transformations: list[dict[str, Any]] = []
        self.warnings: list[str] = []


def normalize_fields(
    fields: dict[str, Any],
    *,
    extra_aliases: dict[str, str] | None = None,
) -> NormalizationResult:
    """Map raw field names -> canonical, coerce types. Unknowns go to `extra`."""
    result = NormalizationResult()
    aliases = {**FIELD_ALIASES, **(extra_aliases or {})}

    for raw_key, value in fields.items():
        if value is None or value == "":
            continue
        key = raw_key.strip()
        low = key.lower()

        if low.startswith("_") or low.startswith("kv_") or low.startswith("_extra"):
            if low == "_extra" and isinstance(value, dict):
                result.extra.update(value)
            elif low not in ("_rule", "_syslog_severity_num"):
                result.extra[key.lstrip("_")] = value
            continue

        canonical = aliases.get(low, low if low in _CANONICAL_FIELDS else None)
        if canonical is None:
            result.extra[key] = value
            continue

        if canonical != low:
            result.transformations.append(
                {"type": "rename", "from": raw_key, "to": canonical}
            )

        if canonical in INT_FIELDS:
            iv = _coerce_int(value)
            if iv is None:
                result.warnings.append(f"{canonical}: '{value}' is not an integer, dropped")
                result.extra[f"{canonical}_raw"] = value
                continue
            value = iv
        elif canonical == "severity":
            nv = normalize_severity(value)
            if nv != value:
                result.transformations.append({"type": "map_severity", "from": value, "to": nv})
            value = nv
            if value is None:
                continue
        elif canonical == "event_type":
            nv = normalize_event_type(value)
            if nv != value:
                result.transformations.append({"type": "map_event_type", "from": value, "to": nv})
            value = nv
        elif canonical == "protocol":
            value = str(value).lower()

        result.canonical[canonical] = value

    # merge any nested extra dict
    if isinstance(result.canonical.get("extra"), dict):
        result.extra.update(result.canonical.pop("extra"))

    return result


def build_event(
    *,
    canonical: dict[str, Any],
    extra: dict[str, Any],
    raw_log: str,
    parser: str,
    parser_version: str,
    field_confidence: dict[str, float] | None = None,
    pii_mode: str = "OFF",
    pii_protected: bool = False,
    confidence: float = 0.0,
    source: str | None = None,
    processing_status: str = "ok",
) -> UniversalLogEvent:
    payload: dict[str, Any] = {k: v for k, v in canonical.items() if k in _CANONICAL_FIELDS}
    payload.setdefault("message", canonical.get("message") or "")
    if source:
        payload["source"] = source
    _infer_from_event_type(payload)
    if "timestamp" in payload and not isinstance(payload["timestamp"], datetime):
        payload["timestamp"] = parse_timestamp(payload["timestamp"])
    payload["raw_log"] = raw_log
    payload["parser"] = parser
    payload["parser_version"] = parser_version
    payload["extra"] = {k: _jsonable(v) for k, v in extra.items()}
    payload["field_confidence"] = field_confidence or {}
    payload["pii_mode"] = pii_mode
    payload["pii_protected"] = pii_protected
    payload["confidence"] = round(max(0.0, min(1.0, confidence)), 3)
    payload["processing_status"] = processing_status
    payload["ingested_at"] = datetime.now(timezone.utc)
    return UniversalLogEvent(**payload)


_EVENT_TYPE_DEFAULTS = {
    "authentication_failure": {"action": "login", "status": "failure"},
    "authentication_success": {"action": "login", "status": "success"},
    "session_opened": {"action": "login", "status": "success"},
    "session_closed": {"action": "logout", "status": "success"},
    "connection_denied": {"action": "deny", "status": "blocked"},
    "connection_allowed": {"action": "allow", "status": "allowed"},
    "account_locked": {"action": "lock", "status": "locked", "severity": "high"},
    "privilege_escalation": {"severity": "medium"},
    "http_request": {"action": "request"},
}


def _infer_from_event_type(payload: dict[str, Any]) -> None:
    et = payload.get("event_type")
    defaults = _EVENT_TYPE_DEFAULTS.get(et or "")
    if not defaults:
        return
    for k, v in defaults.items():
        payload.setdefault(k, v)


def _jsonable(v: Any) -> Any:
    if isinstance(v, (str, int, float, bool)) or v is None:
        return v
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return str(v)
