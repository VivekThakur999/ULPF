"""The Universal Log Event contract (Module 11) and the canonical vocabularies.

Every parser - built-in, declarative pack, or WASM - ultimately produces a
``UniversalLogEvent``. Analytical fields are nullable on purpose.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

SCHEMA_VERSION = "1.0"

# --- Canonical event_type vocabulary (initial set) ---
EVENT_TYPES = {
    "authentication_success",
    "authentication_failure",
    "session_opened",
    "session_closed",
    "http_request",
    "connection_allowed",
    "connection_denied",
    "process_start",
    "process_end",
    "config_change",
    "privilege_escalation",
    "account_locked",
    "dns_query",
    "generic",
}

SEVERITIES = ("info", "low", "medium", "high", "critical")

PROCESSING_OK = "ok"
PROCESSING_PARTIAL = "partial"
PROCESSING_ERROR = "error"


class UniversalLogEvent(BaseModel):
    """Canonical normalized event. schema_version pins the shape."""

    model_config = {"extra": "forbid"}

    id: Optional[str] = None
    schema_version: str = SCHEMA_VERSION

    # time
    timestamp: Optional[datetime] = None
    ingested_at: Optional[datetime] = None

    # origin
    source: str = "unknown"
    host: Optional[str] = None

    # classification
    event_type: Optional[str] = None
    severity: Optional[str] = None

    # identity (may be pseudonymized)
    username: Optional[str] = None
    email: Optional[str] = None

    # network
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    source_port: Optional[int] = Field(default=None, ge=0, le=65535)
    destination_port: Optional[int] = Field(default=None, ge=0, le=65535)
    protocol: Optional[str] = None

    # activity
    action: Optional[str] = None
    status: Optional[str] = None
    process: Optional[str] = None
    service: Optional[str] = None

    # http
    url: Optional[str] = None
    http_method: Optional[str] = None
    response_code: Optional[int] = Field(default=None, ge=0, le=599)

    # content
    message: str = ""
    extra: dict[str, Any] = Field(default_factory=dict)
    field_confidence: dict[str, float] = Field(default_factory=dict)

    # provenance / processing
    raw_log: str = ""
    parser: str = "unknown"
    parser_version: str = "0.0"
    pii_protected: bool = False
    pii_mode: str = "OFF"
    processing_status: str = PROCESSING_OK
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    template_id: Optional[str] = None

    @field_validator("severity")
    @classmethod
    def _sev(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.lower()
        if v not in SEVERITIES:
            raise ValueError(f"severity must be one of {SEVERITIES}")
        return v

    @field_validator("event_type")
    @classmethod
    def _etype(cls, v: Optional[str]) -> Optional[str]:
        # Unknown event types are allowed but coerced to a namespaced form so
        # dashboards stay clean; the canonical set is preferred.
        if v is None:
            return v
        return v.strip().lower().replace(" ", "_")

    @field_validator("protocol")
    @classmethod
    def _proto(cls, v: Optional[str]) -> Optional[str]:
        return v.lower() if v else v


class EventOut(BaseModel):
    """Read model returned by the API (adds server-side fields)."""

    id: str
    schema_version: str
    timestamp: Optional[datetime]
    ingested_at: Optional[datetime]
    source: str
    host: Optional[str]
    event_type: Optional[str]
    severity: Optional[str]
    username: Optional[str]
    email: Optional[str]
    source_ip: Optional[str]
    destination_ip: Optional[str]
    source_port: Optional[int]
    destination_port: Optional[int]
    protocol: Optional[str]
    action: Optional[str]
    status: Optional[str]
    process: Optional[str]
    service: Optional[str]
    url: Optional[str]
    http_method: Optional[str]
    response_code: Optional[int]
    message: str
    extra: dict[str, Any]
    field_confidence: dict[str, float]
    raw_log: str
    parser: str
    parser_version: str
    pii_protected: bool
    pii_mode: str
    processing_status: str
    confidence: float
    template_id: Optional[str]
    job_id: Optional[str] = None
    raw_log_id: Optional[str] = None

    class Config:
        from_attributes = True
