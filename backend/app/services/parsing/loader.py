"""Register all parsers (disk packs + active DB packs) into the live registry."""
from __future__ import annotations

from app.core.logging import get_logger
from app.services.parsing.declarative import DeclarativeParser, PackValidationError
from app.services.parsing.packs import register_disk_packs
from app.services.parsing.registry import registry

log = get_logger("parsing.loader")


def load_db_packs() -> int:
    """Load enabled parser packs stored in the database."""
    from app.core.database import SessionLocal
    from app.models.parser import ParserPack, ParserVersion

    count = 0
    db = SessionLocal()
    try:
        packs = db.query(ParserPack).filter(ParserPack.enabled.is_(True)).all()
        for pack in packs:
            version = (
                db.query(ParserVersion)
                .filter(ParserVersion.pack_id == pack.id, ParserVersion.is_active.is_(True))
                .order_by(ParserVersion.created_at.desc())
                .first()
            )
            if not version or pack.kind != "pack":
                continue
            try:
                parser = DeclarativeParser(version.definition, kind="db-pack")
                problems = parser.validate()
                if problems:
                    log.warning("db pack %s failed validation: %s", pack.name, problems)
                    continue
                registry.register(parser)
                count += 1
            except (PackValidationError, Exception) as exc:  # pragma: no cover
                log.warning("could not load db pack %s: %s", pack.name, exc)
    finally:
        db.close()
    return count


def load_wasm_parsers() -> int:
    """Register the built-in WASM proof-of-concept parser + active DB WASM packs."""
    from app.services.wasm.runtime import WASM_AVAILABLE

    if not WASM_AVAILABLE:
        log.info("WASM runtime unavailable - skipping sandboxed parsers")
        return 0

    count = 0
    try:
        from app.services.wasm.parser import build_poc_parser

        registry.register(build_poc_parser())
        count += 1
    except Exception as exc:  # pragma: no cover
        log.warning("could not register WASM PoC parser: %s", exc)

    try:
        from app.core.database import SessionLocal
        from app.models.parser import ParserPack, ParserVersion
        from app.services.wasm.parser import WasmParser

        db = SessionLocal()
        try:
            packs = db.query(ParserPack).filter(
                ParserPack.enabled.is_(True), ParserPack.kind == "wasm"
            ).all()
            for pack in packs:
                version = (
                    db.query(ParserVersion)
                    .filter(ParserVersion.pack_id == pack.id, ParserVersion.is_active.is_(True))
                    .order_by(ParserVersion.created_at.desc())
                    .first()
                )
                if not version:
                    continue
                try:
                    registry.register(WasmParser(version.definition, kind="db-wasm"))
                    count += 1
                except Exception as exc:  # pragma: no cover
                    log.warning("could not load db WASM pack %s: %s", pack.name, exc)
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover
        log.warning("db WASM pack load skipped: %s", exc)
    return count


def load_all_parsers() -> dict:
    disk = register_disk_packs()
    try:
        db = load_db_packs()
    except Exception as exc:  # pragma: no cover - DB may not be ready
        log.warning("db pack load skipped: %s", exc)
        db = 0
    wasm = load_wasm_parsers()
    total = len(registry.all())
    log.info("parsers registered: %d total (%d disk packs, %d db packs, %d wasm)",
             total, disk, db, wasm)
    return {"disk_packs": disk, "db_packs": db, "wasm_parsers": wasm, "total_parsers": total}
