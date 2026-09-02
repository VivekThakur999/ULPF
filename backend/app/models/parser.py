"""Parser packs and their versions (Module 20)."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.common import Timestamps, UUIDPk

PARSER_KIND_BUILTIN = "builtin"
PARSER_KIND_PACK = "pack"          # declarative YAML/JSON parser pack
PARSER_KIND_WASM = "wasm"          # sandboxed custom module


class ParserPack(Base, UUIDPk, Timestamps):
    __tablename__ = "parser_packs"

    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(16), default=PARSER_KIND_PACK)
    format: Mapped[str] = mapped_column(String(48), default="GENERIC")
    author: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    latest_version: Mapped[str] = mapped_column(String(24), default="1.0.0")

    versions: Mapped[list["ParserVersion"]] = relationship(
        back_populates="pack", cascade="all, delete-orphan", lazy="selectin"
    )


class ParserVersion(Base, UUIDPk, Timestamps):
    __tablename__ = "parser_versions"

    pack_id: Mapped[str] = mapped_column(ForeignKey("parser_packs.id"), index=True)
    version: Mapped[str] = mapped_column(String(24), default="1.0.0")
    schema_version: Mapped[str] = mapped_column(String(8), default="1.0")
    # Declarative definition: patterns, field_mappings, transformations, tests.
    definition: Mapped[dict] = mapped_column(JSON, default=dict)
    # For wasm parsers: base64 module + metadata. Never executed in the API process.
    wasm_module_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    validation_report: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    pack: Mapped[ParserPack] = relationship(back_populates="versions")
