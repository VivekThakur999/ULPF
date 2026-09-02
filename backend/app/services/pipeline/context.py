"""PipelineContext + StageResult - the objects threaded through every stage.

The exact same context/stage machinery powers both batch ingestion and the
live Pipeline Debugger, so whatever an analyst sees in the debugger is what
actually happened during ingestion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# per-record disposition
DISPOSITION_PENDING = "PENDING"
DISPOSITION_PROCESSED = "PROCESSED"
DISPOSITION_INVALID = "INVALID"
DISPOSITION_DUPLICATE = "DUPLICATE"
DISPOSITION_QUARANTINED = "QUARANTINED"

STAGE_OK = "ok"
STAGE_WARN = "warn"
STAGE_ERROR = "error"
STAGE_SKIPPED = "skipped"


@dataclass
class StageResult:
    stage: str
    status: str = STAGE_OK
    summary: str = ""
    input: Any = None
    output: Any = None
    fields: dict[str, Any] = field(default_factory=dict)
    transformations: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "summary": self.summary,
            "input": self.input,
            "output": self.output,
            "fields": self.fields,
            "transformations": self.transformations,
            "warnings": self.warnings,
            "errors": self.errors,
            "meta": self.meta,
            "duration_ms": round(self.duration_ms, 3),
        }


@dataclass
class PipelineContext:
    # --- inputs ---
    raw_line: str
    line_number: int = 0
    source_name: str = "upload"
    source_category: str = "generic"
    declared_format: str | None = None
    pii_mode: str = "OFF"
    pii_settings: Any = None  # PiiSetting-like object or None

    # --- security shield ---
    security_verdict: str = "SAFE"
    security_indicators: list[dict[str, Any]] = field(default_factory=list)

    # --- format detection ---
    detected_format: str | None = None
    format_confidence: float = 0.0
    format_candidates: list[dict[str, Any]] = field(default_factory=list)

    # --- parsing ---
    parser_name: str | None = None
    parser_version: str | None = None
    parsed_fields: dict[str, Any] = field(default_factory=dict)
    parse_confidence: float = 0.0
    parse_match_spans: list[dict[str, Any]] = field(default_factory=list)

    # --- cleaning / extraction ---
    cleaned_fields: dict[str, Any] = field(default_factory=dict)
    field_confidence: dict[str, float] = field(default_factory=dict)

    # --- privacy ---
    pii_transformations: list[dict[str, Any]] = field(default_factory=list)

    # --- normalization / final event ---
    normalized: dict[str, Any] = field(default_factory=dict)
    event: Any = None  # UniversalLogEvent

    # --- control / bookkeeping ---
    stages: list[StageResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dropped: bool = False
    disposition: str = DISPOSITION_PENDING
    content_hash: str = ""

    def add(self, result: StageResult) -> None:
        self.stages.append(result)
        self.errors.extend(result.errors)
        self.warnings.extend(result.warnings)

    def stage_dicts(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self.stages]
