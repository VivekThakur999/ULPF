"""Adapt a sandboxed WASM module to the ULPF parser interface (Module 21)."""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.services.parsing.base import BaseParser, ParseResult
from app.services.wasm.runtime import (
    WASM_AVAILABLE,
    MAX_INPUT_BYTES,
    WasmError,
    WasmLimits,
    WasmSandbox,
)

log = get_logger("wasm.parser")

_POC_WAT = Path(__file__).with_name("poc_parser.wat")
_WASM_LINE_LIMIT = 8 * 1024  # keep PoC well inside sandbox memory


def _module_bytes(definition: dict[str, Any]) -> bytes:
    if definition.get("wat"):
        import wasmtime

        return bytes(wasmtime.wat2wasm(definition["wat"]))
    if definition.get("wasm_base64"):
        return base64.b64decode(definition["wasm_base64"])
    if definition.get("wat_file"):
        return _load_wat_file(definition["wat_file"])
    raise WasmError("module definition needs 'wat', 'wasm_base64' or 'wat_file'")


def _load_wat_file(name: str) -> bytes:
    import wasmtime

    path = Path(__file__).with_name(name)
    if not path.exists() or path.suffix != ".wat":
        raise WasmError(f"wat file not found: {name}")
    return bytes(wasmtime.wat2wasm(path.read_text(encoding="utf-8")))


class WasmParser(BaseParser):
    """A parser whose extraction logic runs entirely inside a WASM sandbox.

    The module receives the raw line as UTF-8 bytes and returns a JSON object of
    flat string fields. ULPF then maps those onto the universal schema exactly
    as it does for any other parser.
    """

    def __init__(self, definition: dict[str, Any], *, kind: str = "wasm"):
        if not WASM_AVAILABLE:
            raise WasmError("wasmtime runtime not installed")
        self.definition = definition
        meta = definition.get("parser", {})
        self.name = meta.get("name", "wasm_parser")
        self.version = str(meta.get("version", "1.0.0"))
        self.format = meta.get("format", self.name.upper())
        self.description = meta.get("description", "sandboxed WASM parser")
        self.schema_version = str(meta.get("schema_version", "1.0"))
        self.specificity = int(meta.get("specificity", 4))
        self._kind = kind
        self._field_mappings: dict[str, str] = definition.get("field_mappings", {})
        self._default_event_type = definition.get("event_type", {}).get("default")
        self._hints = [re.compile(h) for h in definition.get("detect", {}).get("hints", [])]

        lim = definition.get("limits", {})
        self._limits = WasmLimits(
            fuel=int(lim.get("fuel", 5_000_000)),
            timeout_ms=int(lim.get("timeout_ms", 250)),
            max_memory_bytes=int(lim.get("max_memory_bytes", 16 * 1024 * 1024)),
        )
        # compile + validate once
        self._sandbox = WasmSandbox(_module_bytes(definition), self._limits)

    def can_parse(self, sample: str) -> float:
        lines = [ln for ln in sample.splitlines() if ln.strip()][:15]
        if not lines:
            return 0.0
        if self._hints:
            hits = sum(1 for ln in lines if any(h.search(ln) for h in self._hints))
            return round(hits / len(lines), 3)
        # no hints: try a cheap parse of the first line
        try:
            res = self.parse(lines[0])
            return 0.6 if res.fields else 0.0
        except WasmError:
            return 0.0

    def parse(self, line: str) -> ParseResult:
        if len(line.encode("utf-8", "ignore")) > min(_WASM_LINE_LIMIT, MAX_INPUT_BYTES):
            return ParseResult(confidence=0.0, partial=True,
                               errors=["line exceeds WASM parser input limit"])
        try:
            run = self._sandbox.run_json(line)
        except WasmError as exc:
            return ParseResult(confidence=0.0, partial=True, errors=[str(exc)])

        raw = run.output if isinstance(run.output, dict) else {}
        fields: dict[str, Any] = {}
        for k, v in raw.items():
            if v in (None, ""):
                continue
            fields[self._field_mappings.get(k, k)] = v
        et = fields.get("event_type") or self._default_event_type
        return ParseResult(
            fields=fields,
            confidence=0.9 if fields else 0.0,
            event_type=et,
            partial=not fields,
            match_spans=[],  # spans are not recoverable from an opaque module
        )

    def validate(self) -> list[str]:
        try:
            WasmSandbox(_module_bytes(self.definition), self._limits)
        except WasmError as exc:
            return [str(exc)]
        return []

    def run_tests(self) -> dict[str, Any]:
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
            results.append({"index": i, "input": case.get("input", ""), "ok": ok,
                            "mismatches": mismatches, "fields": res.fields})
        return {"total": len(results), "passed": passed, "results": results}

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name, "version": self.version, "format": self.format,
            "description": self.description, "kind": self._kind,
            "schema_version": self.schema_version, "specificity": self.specificity,
            "field_mappings": self._field_mappings,
            "limits": {
                "fuel": self._limits.fuel,
                "timeout_ms": self._limits.timeout_ms,
                "max_memory_bytes": self._limits.max_memory_bytes,
            },
        }


POC_DEFINITION: dict[str, Any] = {
    "parser": {
        "name": "wasm_pipe_poc",
        "version": "1.0.0",
        "format": "PIPE_DELIMITED",
        "specificity": 4,
        "description": "Proof-of-concept sandboxed WASM parser: ts|host|user|src_ip|action",
    },
    "detect": {"hints": [r"^\S+\|\S+\|\S+\|[\d.:a-fA-F]+\|\S+"]},
    "field_mappings": {},
    "event_type": {"default": "generic"},
    "wat_file": "poc_parser.wat",
    "limits": {"fuel": 3_000_000, "timeout_ms": 200},
    "tests": [
        {
            "input": "2025-09-02T09:02:11Z|db-02|admin|192.168.1.50|login_failed",
            "expect": {"host": "db-02", "username": "admin",
                       "source_ip": "192.168.1.50", "action": "login_failed"},
        }
    ],
}


def build_poc_parser() -> WasmParser:
    return WasmParser(POC_DEFINITION, kind="wasm-poc")
