"""WASM sandbox: security-first. Skips cleanly if the runtime is absent."""
import pytest

from app.services.wasm.runtime import WASM_AVAILABLE, WasmError, WasmLimits, WasmSandbox, validate_module_bytes

pytestmark = pytest.mark.skipif(not WASM_AVAILABLE, reason="wasmtime not installed")

if WASM_AVAILABLE:
    import wasmtime

    def _wasm(wat: str) -> bytes:
        return bytes(wasmtime.wat2wasm(wat))

_MINIMAL_OK = """
(module
  (memory (export "memory") 1)
  (global $h (mut i32) (i32.const 1024))
  (func (export "alloc") (param $n i32) (result i32)
    (local $p i32) (local.set $p (global.get $h))
    (global.set $h (i32.add (global.get $h) (local.get $n))) (local.get $p))
  (func (export "ulpf_parse") (param i32 i32) (result i64)
    ;; write {} at offset 0 and return it
    (i32.store8 (i32.const 0) (i32.const 123))
    (i32.store8 (i32.const 1) (i32.const 125))
    (i64.const 2)))
"""


def test_poc_pipe_parser_runs_in_sandbox():
    from app.services.wasm.parser import build_poc_parser

    p = build_poc_parser()
    res = p.parse("2025-09-02T09:02:11Z|db-02|admin|192.168.1.50|login_failed")
    assert res.fields["host"] == "db-02"
    assert res.fields["username"] == "admin"
    assert res.fields["source_ip"] == "192.168.1.50"
    assert res.fields["action"] == "login_failed"
    assert p.run_tests()["passed"] == p.run_tests()["total"]


def test_poc_parser_escapes_quotes_keeping_json_valid():
    from app.services.wasm.parser import build_poc_parser

    res = build_poc_parser().parse('a"b|h|u|10.0.0.1|act')
    assert res.fields["timestamp"] == 'a"b'  # decoded from valid JSON


def test_module_importing_anything_is_rejected():
    wat = """(module
      (import "env" "sneaky" (func))
      (memory (export "memory") 1)
      (func (export "alloc") (param i32) (result i32) i32.const 0)
      (func (export "ulpf_parse") (param i32 i32) (result i64) i64.const 0))"""
    problems = validate_module_bytes(_wasm(wat))
    assert any("must not import" in p for p in problems)
    with pytest.raises(WasmError):
        WasmSandbox(_wasm(wat))


def test_missing_exports_rejected():
    wat = '(module (memory (export "memory") 1))'
    problems = validate_module_bytes(_wasm(wat))
    assert any("alloc" in p for p in problems)
    assert any("ulpf_parse" in p for p in problems)


def test_infinite_loop_is_stopped_by_fuel_and_timeout():
    wat = """(module (memory (export "memory") 1)
      (func (export "alloc") (param i32) (result i32) i32.const 1024)
      (func (export "ulpf_parse") (param i32 i32) (result i64)
        (loop $l (br $l)) i64.const 0))"""
    sb = WasmSandbox(_wasm(wat), WasmLimits(fuel=500_000, timeout_ms=150))
    with pytest.raises(WasmError):
        sb.run_json("x")


def test_implausible_output_length_is_rejected():
    wat = """(module (memory (export "memory") 1)
      (func (export "alloc") (param i32) (result i32) i32.const 1024)
      (func (export "ulpf_parse") (param i32 i32) (result i64)
        (i64.or (i64.shl (i64.const 0) (i64.const 32)) (i64.const 99999999))))"""
    sb = WasmSandbox(_wasm(wat))
    with pytest.raises(WasmError):
        sb.run_json("x")


def test_fuel_accounting_reported():
    sb = WasmSandbox(_wasm(_MINIMAL_OK))
    r = sb.run_json("hello")
    assert r.output == {}
    assert r.fuel_consumed > 0
    assert r.duration_ms >= 0


def test_no_wasi_no_filesystem():
    # a module that tries to import a WASI fd_write must be rejected
    wat = """(module
      (import "wasi_snapshot_preview1" "fd_write"
        (func (param i32 i32 i32 i32) (result i32)))
      (memory (export "memory") 1)
      (func (export "alloc") (param i32) (result i32) i32.const 0)
      (func (export "ulpf_parse") (param i32 i32) (result i64) i64.const 0))"""
    with pytest.raises(WasmError):
        WasmSandbox(_wasm(wat))


def test_wasm_api_status_and_run(client, admin_headers, analyst_headers):
    st = client.get("/api/wasm/status", headers=analyst_headers)
    assert st.status_code == 200
    assert st.json()["available"] is True
    assert any("no WASI" in x for x in st.json()["isolation"])

    poc_wat = (
        __import__("pathlib").Path(
            "app/services/wasm/poc_parser.wat"
        ).read_text(encoding="utf-8")
    )
    r = client.post("/api/wasm/run", headers=admin_headers,
                    json={"wat": poc_wat, "input": "T|h1|bob|1.2.3.4|login"})
    assert r.status_code == 200, r.text
    assert r.json()["output"]["username"] == "bob"
    assert r.json()["fuel_consumed"] > 0

    # analyst cannot run arbitrary modules
    assert client.post("/api/wasm/run", headers=analyst_headers,
                       json={"wat": poc_wat, "input": "x"}).status_code == 403
