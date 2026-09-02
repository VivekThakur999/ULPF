"""Load declarative parser packs from disk and from the database."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.core.logging import get_logger
from app.services.parsing.declarative import DeclarativeParser, PackValidationError
from app.services.parsing.registry import registry

log = get_logger("parsing.packs")

_PACK_ROOT = Path(__file__).resolve().parents[4] / "parser_packs"


def load_pack_dict(definition: dict[str, Any], *, kind: str = "pack") -> DeclarativeParser:
    parser = DeclarativeParser(definition, kind=kind)
    problems = parser.validate()
    if problems:
        raise PackValidationError("; ".join(problems))
    return parser


def load_disk_packs() -> list[DeclarativeParser]:
    parsers: list[DeclarativeParser] = []
    if not _PACK_ROOT.exists():
        return parsers
    for path in sorted(_PACK_ROOT.rglob("*.y*ml")):
        try:
            definition = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(definition, dict) or "parser" not in definition:
                continue
            parser = load_pack_dict(definition, kind="pack")
            parsers.append(parser)
            log.info("loaded parser pack '%s' v%s from %s", parser.name, parser.version, path.name)
        except (yaml.YAMLError, PackValidationError) as exc:
            log.warning("skipped invalid pack %s: %s", path, exc)
    return parsers


def register_disk_packs() -> int:
    count = 0
    for parser in load_disk_packs():
        registry.register(parser)
        count += 1
    return count
