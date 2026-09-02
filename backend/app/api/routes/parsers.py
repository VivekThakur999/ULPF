from __future__ import annotations

from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.parser import ParserPack, ParserVersion
from app.models.user import User
from app.services import audit
from app.services.parsing.declarative import DeclarativeParser
from app.services.parsing.registry import registry

router = APIRouter()


def _is_wasm_def(definition: dict) -> bool:
    if definition.get("parser", {}).get("kind") == "wasm":
        return True
    return any(k in definition for k in ("wat", "wasm_base64", "wat_file"))


def _build_parser(definition: dict, *, kind: str):
    if _is_wasm_def(definition):
        from app.services.wasm.parser import WasmParser
        from app.services.wasm.runtime import WASM_AVAILABLE, WasmError

        if not WASM_AVAILABLE:
            raise HTTPException(status_code=503, detail="WASM runtime not installed")
        try:
            return WasmParser(definition, kind="db-wasm"), "wasm"
        except WasmError as e:
            raise HTTPException(status_code=422, detail={"problems": [str(e)]})
    return DeclarativeParser(definition, kind=kind), "pack"


class PackBody(BaseModel):
    # either a parsed object or a YAML string
    definition: dict[str, Any] | None = None
    yaml_text: str | None = Field(default=None, max_length=100_000)
    author: str = ""

    def resolved(self) -> dict[str, Any]:
        if self.definition:
            return self.definition
        if self.yaml_text:
            obj = yaml.safe_load(self.yaml_text)
            if not isinstance(obj, dict):
                raise ValueError("YAML must define a mapping")
            return obj
        raise ValueError("provide 'definition' or 'yaml_text'")


class SampleBody(BaseModel):
    sample: str = Field(min_length=1, max_length=64_000)


@router.get("")
def list_parsers(_: User = Depends(get_current_user)):
    return {
        "parsers": [
            {**p.metadata(),
             "can_parse_hint": getattr(p, "detect_hints", []) or
                               list(getattr(p, "_hints", []) and
                                    [h.pattern for h in getattr(p, "_hints", [])]) or []}
            for p in registry.all()
        ]
    }


@router.get("/{name}")
def get_parser(name: str, _: User = Depends(get_current_user)):
    p = registry.get_by_name(name)
    if not p:
        raise HTTPException(status_code=404, detail="Parser not found")
    out = p.metadata()
    definition = getattr(p, "definition", None)
    if definition is not None:
        out["definition"] = definition
    if hasattr(p, "run_tests"):
        try:
            out["tests"] = p.run_tests()
        except Exception:  # pragma: no cover
            pass
    return out


@router.post("/validate")
def validate_pack(body: PackBody, _: User = Depends(get_current_user)):
    try:
        definition = body.resolved()
    except (ValueError, yaml.YAMLError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    parser, _pk = _build_parser(definition, kind="pack")
    problems = parser.validate()
    tests = parser.run_tests() if not problems else {"total": 0, "passed": 0, "results": []}
    return {"valid": not problems, "problems": problems, "tests": tests,
            "metadata": parser.metadata()}


@router.post("", status_code=201)
def create_pack(
    body: PackBody,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        definition = body.resolved()
    except (ValueError, yaml.YAMLError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    parser, pack_kind = _build_parser(definition, kind="db-pack")
    problems = parser.validate()
    if problems:
        raise HTTPException(status_code=422, detail={"problems": problems})
    tests = parser.run_tests()
    if tests["total"] and tests["passed"] < tests["total"]:
        raise HTTPException(status_code=422,
                            detail={"problems": ["embedded tests failed"], "tests": tests})

    existing_parser = registry.get_by_name(parser.name)
    if existing_parser and existing_parser.metadata().get("kind") == "builtin":
        raise HTTPException(status_code=409,
                            detail=f"'{parser.name}' shadows a built-in parser; pick another name")

    pack = db.query(ParserPack).filter(ParserPack.name == parser.name).first()
    if not pack:
        pack = ParserPack(name=parser.name, kind=pack_kind, format=parser.format,
                          author=body.author, description=parser.description,
                          latest_version=parser.version)
        db.add(pack)
        db.flush()
    else:
        pack.latest_version = parser.version
        pack.format = parser.format
        db.query(ParserVersion).filter(ParserVersion.pack_id == pack.id).update(
            {"is_active": False}
        )

    version = ParserVersion(
        pack_id=pack.id, version=parser.version,
        schema_version=parser.schema_version, definition=definition,
        is_active=True, validation_report={"problems": problems, "tests": tests},
        created_by=admin.id,
    )
    db.add(version)
    db.commit()

    registry.register(parser)
    audit.record(db, action="parser.pack_create", actor=admin, target_type="parser_pack",
                 target_id=pack.id, detail=f"{parser.name} v{parser.version}",
                 ip_address=request.client.host if request.client else None)
    return {"name": parser.name, "version": parser.version, "tests": tests,
            "registered": True}


@router.get("/{name}/versions")
def list_versions(name: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    pack = db.query(ParserPack).filter(ParserPack.name == name).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Pack not found (built-in parsers are unversioned)")
    return {
        "name": pack.name, "latest_version": pack.latest_version,
        "versions": [
            {"version": v.version, "is_active": v.is_active, "created_at": v.created_at,
             "created_by": v.created_by, "tests_passed": v.validation_report.get("tests", {}).get("passed")}
            for v in sorted(pack.versions, key=lambda x: x.created_at, reverse=True)
        ],
    }


@router.post("/{name}/test")
def test_parser(name: str, body: SampleBody, _: User = Depends(get_current_user)):
    p = registry.get_by_name(name)
    if not p:
        raise HTTPException(status_code=404, detail="Parser not found")
    first_line = body.sample.splitlines()[0] if body.sample.splitlines() else body.sample
    result = p.parse(first_line)
    out = {
        "parser": name,
        "can_parse": p.can_parse(body.sample),
        "fields": result.fields,
        "confidence": result.confidence,
        "event_type": result.event_type,
        "match_spans": result.match_spans,
        "errors": result.errors,
        "partial": result.partial,
    }
    if hasattr(p, "run_tests"):
        try:
            out["tests"] = p.run_tests()
        except Exception:  # pragma: no cover
            pass
    return out
