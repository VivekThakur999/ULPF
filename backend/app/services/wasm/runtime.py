"""Sandboxed execution runtime for custom parser modules (Module 21).

Security model
--------------
* WebAssembly only - never native code, never Python from the module.
* The module is instantiated with an EMPTY linker: no WASI, so no filesystem,
  no clock, no environment, no network, no stdio.
* Any module that imports *anything* is rejected before instantiation.
* Fuel metering caps total executed instructions.
* An epoch-interrupt watchdog thread caps wall-clock time.
* Linear memory is capped (StoreLimits) - growth beyond the cap traps.
* Only three exports are used, over a tiny value-only ABI (see abi.py):
      memory            (WebAssembly.Memory)
      alloc(i32)->i32   bump allocator inside the sandbox
      ulpf_parse(i32 ptr, i32 len) -> i64  (packed out_ptr<<32 | out_len)

If `wasmtime` is not installed the feature reports itself unavailable rather
than crashing the app.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger

log = get_logger("wasm")

try:  # optional dependency
    import wasmtime  # type: ignore

    WASM_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only where wasmtime missing
    wasmtime = None  # type: ignore
    WASM_AVAILABLE = False


DEFAULT_FUEL = 5_000_000
DEFAULT_TIMEOUT_MS = 250
DEFAULT_MAX_MEMORY_BYTES = 16 * 1024 * 1024  # 16 MiB
MAX_INPUT_BYTES = 256 * 1024
MAX_OUTPUT_BYTES = 1 * 1024 * 1024


class WasmError(RuntimeError):
    pass


class WasmUnavailable(WasmError):
    pass


@dataclass
class WasmLimits:
    fuel: int = DEFAULT_FUEL
    timeout_ms: int = DEFAULT_TIMEOUT_MS
    max_memory_bytes: int = DEFAULT_MAX_MEMORY_BYTES


@dataclass
class WasmRunResult:
    output: Any
    fuel_consumed: int
    duration_ms: float
    memory_bytes: int


def validate_module_bytes(data: bytes) -> list[str]:
    """Static checks before we ever instantiate. Returns a list of problems."""
    if not WASM_AVAILABLE:
        return ["wasmtime runtime not installed"]
    problems: list[str] = []
    engine = wasmtime.Engine()
    try:
        module = wasmtime.Module(engine, data)
    except Exception as exc:
        return [f"not a valid WebAssembly module: {exc}"]

    imports = list(module.imports)
    if imports:
        names = ", ".join(f"{i.module}.{i.name}" for i in imports)
        problems.append(f"module must not import anything (found: {names})")

    export_names = {e.name for e in module.exports}
    for required in ("memory", "alloc", "ulpf_parse"):
        if required not in export_names:
            problems.append(f"missing required export '{required}'")
    return problems


class WasmSandbox:
    """One-shot sandboxed executor for a single module + limits."""

    def __init__(self, module_bytes: bytes, limits: WasmLimits | None = None):
        if not WASM_AVAILABLE:
            raise WasmUnavailable("wasmtime runtime not installed")
        self.limits = limits or WasmLimits()
        problems = validate_module_bytes(module_bytes)
        if problems:
            raise WasmError("; ".join(problems))

        cfg = wasmtime.Config()
        cfg.consume_fuel = True
        cfg.epoch_interruption = True
        self._engine = wasmtime.Engine(cfg)
        self._module = wasmtime.Module(self._engine, module_bytes)

    # -- ABI helpers --------------------------------------------------------

    def _read_mem(self, store, memory, ptr: int, length: int) -> bytes:
        if length < 0 or length > MAX_OUTPUT_BYTES:
            raise WasmError(f"module returned an implausible output length ({length})")
        data = memory.read(store, ptr, ptr + length)
        return bytes(data)

    def run_json(self, payload: dict[str, Any] | str) -> WasmRunResult:
        raw = payload if isinstance(payload, str) else json.dumps(payload)
        in_bytes = raw.encode("utf-8")
        if len(in_bytes) > MAX_INPUT_BYTES:
            raise WasmError("input exceeds sandbox limit")

        store = wasmtime.Store(self._engine)
        store.set_fuel(self.limits.fuel)
        store.set_epoch_deadline(1)
        store.set_limits(memory_size=self.limits.max_memory_bytes)

        linker = wasmtime.Linker(self._engine)  # deliberately empty: no WASI
        instance = linker.instantiate(store, self._module)
        exports = instance.exports(store)

        memory = exports["memory"]
        alloc = exports["alloc"]
        parse = exports["ulpf_parse"]

        # watchdog: bump the engine epoch after timeout so a hung module traps
        deadline_hit = threading.Event()

        def _watchdog():
            if not deadline_hit.wait(self.limits.timeout_ms / 1000.0):
                self._engine.increment_epoch()

        wd = threading.Thread(target=_watchdog, daemon=True)
        wd.start()
        start = time.perf_counter()
        try:
            ptr = alloc(store, len(in_bytes))
            if not isinstance(ptr, int) or ptr <= 0:
                raise WasmError("sandbox alloc() failed")
            memory.write(store, in_bytes, ptr)
            packed = parse(store, ptr, len(in_bytes))
            out_ptr = (packed >> 32) & 0xFFFFFFFF
            out_len = packed & 0xFFFFFFFF
            out_bytes = self._read_mem(store, memory, out_ptr, out_len)
        except wasmtime.Trap as exc:
            raise WasmError(f"sandbox trap: {exc}") from exc
        finally:
            deadline_hit.set()
            duration_ms = (time.perf_counter() - start) * 1000.0

        try:
            remaining = store.get_fuel()
        except Exception:
            remaining = 0
        fuel_consumed = max(0, self.limits.fuel - remaining)

        try:
            parsed = json.loads(out_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WasmError(f"sandbox produced invalid JSON output: {exc}") from exc

        return WasmRunResult(
            output=parsed,
            fuel_consumed=fuel_consumed,
            duration_ms=round(duration_ms, 3),
            memory_bytes=memory.data_len(store),
        )


def runtime_status() -> dict[str, Any]:
    return {
        "available": WASM_AVAILABLE,
        "runtime": "wasmtime" if WASM_AVAILABLE else None,
        "defaults": {
            "fuel": DEFAULT_FUEL,
            "timeout_ms": DEFAULT_TIMEOUT_MS,
            "max_memory_bytes": DEFAULT_MAX_MEMORY_BYTES,
            "max_input_bytes": MAX_INPUT_BYTES,
        },
        "isolation": [
            "no WASI (no filesystem / clock / env / network / stdio)",
            "modules importing anything are rejected",
            "fuel-metered instruction cap",
            "epoch-interrupt wall-clock timeout",
            "linear-memory cap via StoreLimits",
        ],
    }
