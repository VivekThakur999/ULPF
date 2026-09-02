# WASM Sandbox for Custom Parsers (Module 21)

## Why

Declarative parser packs cover most formats with regex + a fixed transform set.
For formats a regex cannot express, ULPF can run a **compiled WebAssembly
module** as the extraction logic — without ever executing native or Python code
from the module author.

## Security model

The runtime is `wasmtime` (`backend/app/services/wasm/runtime.py`).

| Control | How |
|---|---|
| No filesystem / clock / env / network / stdio | The module is instantiated with an **empty `Linker`** — **no WASI** is added. |
| No host imports at all | Any module that imports *anything* is **rejected before instantiation** (`validate_module_bytes`). |
| Instruction cap | `Config.consume_fuel = True`; the store is given a fixed fuel budget (default 5,000,000). Exhaustion → trap. |
| Wall-clock cap | `Config.epoch_interruption = True` + a watchdog thread that calls `engine.increment_epoch()` after `timeout_ms` (default 250 ms). A hung module traps. |
| Memory cap | `store.set_limits(memory_size=…)` (default 16 MiB). Growth beyond the cap traps. |
| Output sanity | The returned `(ptr,len)` is range-checked; `len > 1 MiB` is rejected. Output must be valid UTF-8 JSON or the run fails. |
| Input cap | 256 KiB to the sandbox; the WASM *parser adapter* further caps lines to 8 KiB. |
| One-shot | A fresh `Store` per invocation — no state persists between lines. |

Native code is **never** executed. Python `eval`/`exec`/`subprocess` are **never**
used (enforced by `tests/test_security_no_exec.py`).

## ABI

The guest module exports exactly:

```wat
(memory (export "memory"))
(func   (export "alloc")      (param i32) (result i32))          ;; bump allocator
(func   (export "ulpf_parse") (param i32 i32) (result i64))      ;; (ptr,len) -> packed
```

Host flow: `p = alloc(len)` → write the raw line's UTF-8 bytes at `p` →
`packed = ulpf_parse(p, len)` → `out_ptr = packed >> 32`, `out_len = packed & 0xffffffff`
→ read `[out_ptr, out_ptr+out_len)` → parse as a JSON object of flat string fields
→ map onto the Universal schema like any other parser.

## Proof-of-concept parser

`backend/app/services/wasm/poc_parser.wat` — a genuine parser for a
pipe-delimited format `ts|host|user|src_ip|action` → the universal event. It is
hand-written WAT (~120 lines), compiled at load via `wasmtime.wat2wasm`, imports
nothing, escapes `"`/`\` so its JSON output is always well-formed, and pads
missing fields. Registered automatically as parser `wasm_pipe_poc`
(format `PIPE_DELIMITED`) when `wasmtime` is installed.

Try it: Pipeline Debugger → "WASM PoC" sample, or
`POST /api/wasm/run {wat, input}`.

## API

| Method | Path | Role | |
|---|---|---|---|
| GET | `/api/wasm/status` | any | runtime availability + isolation summary + default limits |
| POST | `/api/wasm/validate` | ADMIN | static-check a `wat`/`wasm_base64` module |
| POST | `/api/wasm/run` | ADMIN | run a module against one input line (ephemeral, sandboxed) |

WASM parser packs are registered through `POST /api/parsers` with
`parser.kind: wasm` and a `wat:` / `wasm_base64:` field; versions are stored in
`parser_packs` / `parser_versions` exactly like declarative packs.

## Honest limitations (MVP)

- **Match spans** (the Regex101-style highlight) are **not** recovered from a
  WASM module — its internals are opaque. Built-in and declarative-pack parsers
  still provide spans.
- No multi-line / stateful parsing in the PoC (one line in, one JSON out).
- `wasmtime` epoch interruption resolution is coarse (~ms); a tight loop is
  stopped by fuel first in practice.
- No compilation toolchain is bundled — authors bring a `.wasm`/`.wat`. A
  Rust/TinyGo → WASM example is future work.
- The sandbox protects the **host**; it does not vet a module for *correctness*
  or *malicious output shape* beyond JSON/size validation. Treat third-party
  modules as untrusted data producers and review their output mappings.
