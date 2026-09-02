"""Log templates and template-based compression records (Modules 23-24)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import UUIDPk, utcnow


class Template(Base, UUIDPk):
    __tablename__ = "templates"

    template_key: Mapped[str] = mapped_column(String(24), unique=True, index=True)  # TPL-0045
    pattern: Mapped[str] = mapped_column(Text)  # "User <*> logged in at <*> from <*>"
    token_signature: Mapped[str] = mapped_column(String(64), index=True)
    example: Mapped[str] = mapped_column(Text, default="")
    occurrences: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    source: Mapped[str] = mapped_column(String(120), default="unknown")


class CompressionRecord(Base, UUIDPk):
    __tablename__ = "compression_records"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String(64), default="job")
    original_bytes: Mapped[int] = mapped_column(Integer, default=0)
    compressed_bytes: Mapped[int] = mapped_column(Integer, default=0)
    reduction_pct: Mapped[float] = mapped_column(Float, default=0.0)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    template_count: Mapped[int] = mapped_column(Integer, default=0)
    method: Mapped[str] = mapped_column(String(48), default="template+varsub")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
