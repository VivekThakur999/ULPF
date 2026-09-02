"""Declarative parser packs (Module 20).

A pack is pure data (YAML/JSON): detection hints, an ordered list of named-group
regexes, field mappings, value transformations and self-tests. No code from the
pack is ever executed - only ``re`` and a small fixed set of transforms.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as _dateparser

from app.services.parsing.base import BaseParser, ParseResult

_ALLOWED_TRANSFORMS = {"int", "float", "lower", "upper", "strip", "strptime", "epoch", "const"}
_MAX_PATTERNS = 25
_REGEX_TIMEOUT_LEN = 100_000  # refuse absurdly long inputs to a pack regex


class PackValidationError(ValueError):
    pass


def _apply_transform(value: Any, spec: Any) -> Any:
    if isinstance(spec, str):
        spec = {"type": spec}
    t = spec.get("type")
    try:
        if t == "int":
            return int(str(value).strip())
        if t == "float":
            return float(str(value).strip())
        if t == "lower":
            return str(value).lower()
        if t == "upper":
            return str(value).upper()
        if t == "strip":
            return str(value).strip()
        if t == "const":
            return spec.get("value")
        if t == "epoch":
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
        if t == "strptime":
            fmt = spec.get("format")
            if fmt:
                dt = datetime.strptime(str(value), fmt)
            else:
                dt = _dateparser.parse(str(value))
            if not dt.tzinfo:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
    except (ValueError, TypeError, OverflowError):
        return value
    return value


class DeclarativeParser(BaseParser):
    def __init__(self, definition: dict[str, Any], *, kind: str = "pack"):
        self.definition = definition
        meta = definition.get("parser", {})
        self.name = meta.get("name", "unnamed_pack")
        self.version = str(meta.get("version", "1.0.0"))
        self.format = meta.get("format", self.name.upper())
        self.description = meta.get("description", "")
        self.schema_version = str(meta.get("schema_version", "1.0"))
        self.specificity = int(meta.get("specificity", 4))
        self._kind = kind

        # compile defensively - validate() surfaces bad regexes as problems
        # rather than the constructor exploding.
        self._raw_patterns: list[str] = list(definition.get("patterns", []))
        self._patterns = []
        for p in self._raw_patterns:
            try:
                self._patterns.append(re.compile(p))
            except re.error:
                pass
        self._hints = []
        for h in definition.get("detect", {}).get("hints", []):
            try:
                self._hints.append(re.compile(h))
            except re.error:
                pass
        self._field_mappings: dict[str, str] = definition.get("field_mappings", {})
        self._transforms: dict[str, Any] = definition.get("transformations", {})
        self._event_type_default = definition.get("event_type", {}).get("default")
        self._extra_aliases: dict[str, str] = definition.get("aliases", {})
        # optional: expand a captured "key=value key2=value2" field into fields
        self._kv_expand: str | None = definition.get("kv_expand")
        self._kv_token = re.compile(r'([A-Za-z_][\w.\-]*)=("([^"]*)"|\S+)')

    # --- interface ---------------------------------------------------------

    def can_parse(self, sample: str) -> float:
        lines = [ln for ln in sample.splitlines() if ln.strip()][:25]
        if not lines:
            return 0.0
        matched = sum(1 for ln in lines if any(rx.search(ln) for rx in self._patterns))
        score = matched / len(lines)
        if self._hints and any(h.search(sample) for h in self._hints):
            score = min(1.0, score + 0.15)
        return round(score, 3)

    def parse(self, line: str) -> ParseResult:
        if len(line) > _REGEX_TIMEOUT_LEN:
            return ParseResult(confidence=0.0, errors=["input too large for pack"], partial=True)
        for rx in self._patterns:
            m = rx.search(line)
            if not m:
                continue
            fields: dict[str, Any] = {}
            spans = []
            for k, v in m.groupdict().items():
                if v is None:
                    continue
                target = self._field_mappings.get(k, k)
                if k in self._transforms:
                    v = _apply_transform(v, self._transforms[k])
                fields[target] = v
                s, e = m.span(k)
                if s >= 0:
                    spans.append({"field": target, "start": s, "end": e, "text": m.group(k)})
            # constant / default fields
            for k, spec in self._transforms.items():
                if isinstance(spec, dict) and spec.get("type") == "const" and k not in fields:
                    fields[k] = spec.get("value")
            # expand a key=value blob (e.g. CEF extension) using pack aliases
            if self._kv_expand and self._kv_expand in fields:
                blob = str(fields.pop(self._kv_expand))
                for tm in self._kv_token.finditer(blob):
                    key = tm.group(1)
                    val = tm.group(3) if tm.group(3) is not None else tm.group(2)
                    target = self._extra_aliases.get(key, self._extra_aliases.get(key.lower(), key))
                    fields.setdefault(target, val)
            et = fields.get("event_type") or self._event_type_default
            return ParseResult(fields=fields, confidence=0.92, event_type=et,
                               match_spans=spans)
        return ParseResult(confidence=0.0, errors=["no pack pattern matched"], partial=True)

    def validate(self) -> list[str]:
        problems: list[str] = []
        meta = self.definition.get("parser", {})
        if not meta.get("name"):
            problems.append("parser.name is required")
        pats = self.definition.get("patterns", [])
        if not pats:
            problems.append("at least one pattern is required")
        if len(pats) > _MAX_PATTERNS:
            problems.append(f"too many patterns (max {_MAX_PATTERNS})")
        for i, p in enumerate(pats):
            try:
                re.compile(p)
            except re.error as ex:
                problems.append(f"patterns[{i}] invalid regex: {ex}")
        for k, spec in self._transforms.items():
            t = spec.get("type") if isinstance(spec, dict) else spec
            if t not in _ALLOWED_TRANSFORMS:
                problems.append(f"transformation '{k}': unknown type '{t}'")
        return problems

    def run_tests(self) -> dict[str, Any]:
        """Execute the pack's embedded self-tests."""
        results = []
        passed = 0
        for i, case in enumerate(self.definition.get("tests", [])):
            res = self.parse(case.get("input", ""))
            expect = case.get("expect", {})
            mismatches = {
                k: {"expected": v, "got": res.fields.get(k)}
                for k, v in expect.items()
                if str(res.fields.get(k)) != str(v)
            }
            ok = bool(not mismatches and (not expect or res.fields))
            passed += int(ok)
            results.append({"index": i, "input": case.get("input", ""),
                            "ok": ok, "mismatches": mismatches, "fields": res.fields})
        return {"total": len(results), "passed": passed, "results": results}

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name, "version": self.version, "format": self.format,
            "description": self.description, "kind": self._kind,
            "schema_version": self.schema_version, "specificity": self.specificity,
            "pattern_count": len(self._patterns),
            "field_mappings": self._field_mappings,
        }
