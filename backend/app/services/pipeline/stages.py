"""Concrete pipeline stages.

Checkpoint 1 implements Detect / Parse / Normalize / Validate fully, plus thin
but real Shield / Clean / Extract / PII stages. Checkpoints 2 deepens Shield,
Clean, Extract and PII in place - the seams here do not change.
"""
from __future__ import annotations

import hashlib
from typing import Any

from app.schemas.event import PROCESSING_ERROR, PROCESSING_OK, PROCESSING_PARTIAL
from app.services.detection.detector import detector
from app.services.normalization.normalizer import build_event, normalize_fields
from app.services.parsing.registry import registry
from app.services.pipeline.base import PipelineStage
from app.services.pipeline.context import (
    DISPOSITION_INVALID,
    DISPOSITION_PROCESSED,
    DISPOSITION_QUARANTINED,
    STAGE_ERROR,
    STAGE_OK,
    STAGE_SKIPPED,
    STAGE_WARN,
    PipelineContext,
    StageResult,
)


class SecurityShieldStage(PipelineStage):
    name = "security_shield"

    def run(self, ctx: PipelineContext, result: StageResult) -> None:
        from app.core.config import settings
        from app.services.security.shield import screen_line

        result.input = ctx.raw_line
        verdict = screen_line(
            ctx.raw_line,
            quarantine_injection=settings.shield_quarantine_suspicious,
        )
        ctx.security_verdict = verdict.verdict
        ctx.security_indicators = verdict.indicators
        result.output = verdict.verdict
        result.fields = {"verdict": verdict.verdict}
        result.meta = {"indicators": verdict.indicators}
        result.summary = verdict.summary

        if verdict.verdict == "WEAPONIZED_LOG":
            result.status = STAGE_ERROR
            result.errors.append(verdict.summary)
            if verdict.quarantine:
                ctx.dropped = True
                ctx.disposition = DISPOSITION_QUARANTINED
        elif verdict.verdict == "SUSPICIOUS":
            result.status = STAGE_WARN
            result.warnings.append(verdict.summary)
            if verdict.quarantine:
                ctx.dropped = True
                ctx.disposition = DISPOSITION_QUARANTINED


class FormatDetectionStage(PipelineStage):
    name = "format_detection"

    def run(self, ctx: PipelineContext, result: StageResult) -> None:
        result.input = ctx.raw_line
        det = detector.detect(ctx.raw_line, hint=ctx.declared_format)
        ctx.detected_format = det.format
        ctx.format_confidence = det.confidence
        ctx.format_candidates = det.candidates
        result.output = {"format": det.format, "confidence": det.confidence}
        result.fields = {"format": det.format, "confidence": det.confidence}
        result.meta = {"candidates": det.candidates, "signals": det.signals}
        result.summary = f"{det.format} ({det.confidence:.0%})"
        if det.confidence < 0.35:
            result.status = STAGE_WARN
            result.warnings.append("low-confidence format detection")


class ParsingStage(PipelineStage):
    name = "parsing"

    def run(self, ctx: PipelineContext, result: StageResult) -> None:
        result.input = ctx.raw_line
        parser, score = registry.select(ctx.raw_line, hint_format=ctx.detected_format)
        pr = parser.parse(ctx.raw_line)
        ctx.parser_name = parser.name
        ctx.parser_version = parser.version
        ctx.parsed_fields = dict(pr.fields)
        ctx.parse_confidence = pr.confidence
        ctx.parse_match_spans = pr.match_spans
        if pr.event_type and "event_type" not in ctx.parsed_fields:
            ctx.parsed_fields["event_type"] = pr.event_type

        result.output = ctx.parsed_fields
        result.fields = ctx.parsed_fields
        result.meta = {
            "parser": parser.name,
            "parser_version": parser.version,
            "select_score": round(score, 3),
            "parse_confidence": pr.confidence,
            "match_spans": pr.match_spans,
        }
        result.summary = f"{parser.name} v{parser.version} → {len(ctx.parsed_fields)} fields"
        if pr.errors:
            result.status = STAGE_WARN
            result.warnings.extend(pr.errors)
        if parser.name == "raw":
            result.status = STAGE_WARN
            result.warnings.append("no structured parser matched; raw fallback used")


class CleaningStage(PipelineStage):
    name = "cleaning"

    def run(self, ctx: PipelineContext, result: StageResult) -> None:
        from app.services.cleaning.cleaner import clean_fields

        result.input = ctx.parsed_fields
        cleaned, transforms, warnings, invalid = clean_fields(ctx.parsed_fields)
        ctx.cleaned_fields = cleaned
        result.output = cleaned
        result.fields = cleaned
        result.transformations = transforms
        result.warnings.extend(warnings)
        result.summary = f"{len(transforms)} transformation(s)"
        if invalid:
            result.status = STAGE_WARN


class FieldExtractionStage(PipelineStage):
    name = "field_extraction"

    def run(self, ctx: PipelineContext, result: StageResult) -> None:
        from app.services.parsing.extractors import extract_supplementary

        base = dict(ctx.cleaned_fields or ctx.parsed_fields)
        result.input = base
        enriched, confidence, found = extract_supplementary(
            base, raw_line=ctx.raw_line, parse_confidence=ctx.parse_confidence
        )
        ctx.cleaned_fields = enriched
        ctx.field_confidence = confidence
        result.output = enriched
        result.fields = enriched
        result.meta = {"field_confidence": confidence, "supplementary": found}
        result.summary = f"{len(enriched)} field(s), {len(found)} inferred"


class PiiStage(PipelineStage):
    name = "pii_obfuscation"

    def run(self, ctx: PipelineContext, result: StageResult) -> None:
        from app.services.privacy.pii import apply_pii

        fields = dict(ctx.cleaned_fields)
        result.input = fields
        protected, transforms, mode = apply_pii(fields, settings=ctx.pii_settings,
                                                mode_override=ctx.pii_mode)
        ctx.cleaned_fields = protected
        ctx.pii_transformations = transforms
        ctx.pii_mode = mode
        result.output = protected
        result.fields = protected
        result.transformations = transforms
        result.meta = {"mode": mode}
        result.summary = (
            f"mode={mode}, {len(transforms)} identifier(s) protected"
            if mode != "OFF" else "PII protection OFF"
        )
        if mode == "OFF":
            result.status = STAGE_SKIPPED


class NormalizationStage(PipelineStage):
    name = "normalization"

    def run(self, ctx: PipelineContext, result: StageResult) -> None:
        result.input = ctx.cleaned_fields
        norm = normalize_fields(ctx.cleaned_fields)
        ctx.normalized = {"canonical": norm.canonical, "extra": norm.extra}
        result.output = norm.canonical
        result.fields = norm.canonical
        result.transformations = norm.transformations
        result.warnings.extend(norm.warnings)
        result.meta = {"extra": norm.extra}
        result.summary = f"{len(norm.canonical)} canonical field(s)"


class ValidationStage(PipelineStage):
    name = "validation"

    def run(self, ctx: PipelineContext, result: StageResult) -> None:
        canonical = ctx.normalized.get("canonical", {})
        extra = ctx.normalized.get("extra", {})
        result.input = canonical

        status = PROCESSING_OK
        if ctx.parser_name == "raw":
            status = PROCESSING_PARTIAL
        elif not canonical:
            status = PROCESSING_PARTIAL

        overall_conf = round(
            0.5 * ctx.parse_confidence
            + 0.3 * ctx.format_confidence
            + 0.2 * (sum(ctx.field_confidence.values()) / len(ctx.field_confidence)
                     if ctx.field_confidence else 0.0),
            3,
        )
        try:
            event = build_event(
                canonical=canonical,
                extra=extra,
                raw_log=ctx.raw_line,
                parser=ctx.parser_name or "unknown",
                parser_version=ctx.parser_version or "0.0",
                field_confidence=ctx.field_confidence,
                pii_mode=ctx.pii_mode,
                pii_protected=ctx.pii_mode != "OFF" and bool(ctx.pii_transformations),
                confidence=overall_conf,
                source=ctx.source_name,
                processing_status=status,
            )
        except Exception as exc:
            result.status = STAGE_ERROR
            result.errors.append(f"schema validation failed: {exc}")
            ctx.disposition = DISPOSITION_INVALID
            return

        ctx.event = event
        if ctx.disposition not in (DISPOSITION_QUARANTINED, DISPOSITION_INVALID):
            ctx.disposition = DISPOSITION_PROCESSED
        result.output = event.model_dump(mode="json")
        result.fields = {k: v for k, v in result.output.items() if v not in (None, "", {}, [])}
        result.summary = f"UniversalLogEvent OK (schema {event.schema_version}, conf {overall_conf})"
        if status == PROCESSING_PARTIAL:
            result.status = STAGE_WARN


# ordered pipeline
PIPELINE_STAGES: list[type[PipelineStage]] = [
    SecurityShieldStage,
    FormatDetectionStage,
    ParsingStage,
    CleaningStage,
    FieldExtractionStage,
    PiiStage,
    NormalizationStage,
    ValidationStage,
]
