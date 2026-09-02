from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.deps import get_current_user, require_admin
from app.models.user import User
from app.services.wasm.runtime import (
    WASM_AVAILABLE,
    WasmError,
    WasmLimits,
    WasmSandbox,
    runtime_status,
    validate_module_bytes,
)

router = APIRouter()


def _to_bytes(wat: str | None, wasm_base64: str | None) -> bytes:
    import base64

    if wat:
        import wasmtime

        return bytes(wasmtime.wat2wasm(wat))
    if wasm_base64:
        return base64.b64decode(wasm_base64)
    raise HTTPException(status_code=422, detail="provide 'wat' or 'wasm_base64'")


class ModuleBody(BaseModel):
    wat: str | None = Field(default=None, max_length=200_000)
    wasm_base64: str | None = Field(default=None, max_length=4_000_000)


class RunBody(ModuleBody):
    input: str = Field(min_length=1, max_length=64_000)
    fuel: int = Field(default=3_000_000, ge=10_000, le=50_000_000)
    timeout_ms: int = Field(default=250, ge=10, le=2000)


@router.get("/status")
def status(_: User = Depends(get_current_user)):
    return runtime_status()


@router.post("/validate")
def validate(body: ModuleBody, _: User = Depends(require_admin)):
    if not WASM_AVAILABLE:
        raise HTTPException(status_code=503, detail="WASM runtime not installed")
    try:
        data = _to_bytes(body.wat, body.wasm_base64)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"could not read module: {e}")
    problems = validate_module_bytes(data)
    return {"valid": not problems, "problems": problems, "size_bytes": len(data)}


@router.post("/run")
def run(body: RunBody, _: User = Depends(require_admin)):
    if not WASM_AVAILABLE:
        raise HTTPException(status_code=503, detail="WASM runtime not installed")
    try:
        data = _to_bytes(body.wat, body.wasm_base64)
        sandbox = WasmSandbox(data, WasmLimits(fuel=body.fuel, timeout_ms=body.timeout_ms))
        result = sandbox.run_json(body.input)
    except WasmError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "output": result.output,
        "fuel_consumed": result.fuel_consumed,
        "duration_ms": result.duration_ms,
        "memory_bytes": result.memory_bytes,
    }
