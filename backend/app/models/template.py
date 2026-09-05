"""Log templates and template-based compression records (Modules 23-24).

A Template captures the *shape* of a recurring log line: which token
positions are stable literal text and which are variable, plus enough layout
information (per-token separators + trailing text) to reconstruct any
matching line exactly when combined with that line's own variable values
(stored per-occurrence on TemplateMatch).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import Timestamps, UUIDPk, utcnow


class Template(Base, UUIDPk, Timestamps):
    __tablename__ = "templates"

    template_key: Mapped[str] = mapped_column(String(24), unique=True, index=True)  # TPL-0045
    pattern: Mapped[str] = mapped_column(Text)  # "User <*> logged in at <*> from <*>"

    token_count: Mapped[int] = mapped_column(Integer, default=0)
    # literal_tokens[i] is the literal text at position i, or null if that
    # position is a variable (wildcard).
    literal_tokens: Mapped[list] = mapped_column(JSON, default=list)
    # variable_types[i] is set only where literal_tokens[i] is null: a regex
    # class name (ip, email, ...) or "value" when it was wildcarded purely
    # because it differed across occurrences (e.g. a username).
    variable_types: Mapped[list] = mapped_column(JSON, default=list)
    # canonical inter-token separators from the representative example, used
    # only to render a readable example/preview - NOT for reconstruction
    # (each TemplateMatch carries its own exact separators).
    separators: Mapped[list] = mapped_column(JSON, default=list)
    trailing: Mapped[str] = mapped_column(String(64), default="")

    # dedup key for this exact literal/wildcard shape, so re-mining the same
    # data updates rather than duplicates a template.
    token_signature: Mapped[str] = mapped_column(String(64), index=True)

    occurrences: Mapped[int] = mapped_column(Integer, default=0)
    variable_count: Mapped[int] = mapped_column(Integer, default=0)
    source_distribution: Mapped[dict] = mapped_column(JSON, default=dict)
    # bounded sample of real matching lines, most recent mining run
    examples: Mapped[list] = mapped_column(JSON, default=list)
    example: Mapped[str] = mapped_column(Text, default="")  # first example, for quick display

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TemplateMatch(Base, UUIDPk):
    """One raw log's compressed representation: which template it matched
    plus exactly what is needed to reconstruct it byte-for-byte."""

    __tablename__ = "template_matches"

    template_id: Mapped[str] = mapped_column(ForeignKey("templates.id"), index=True)
    raw_log_id: Mapped[str] = mapped_column(
        ForeignKey("raw_logs.id"), unique=True, index=True
    )
    source: Mapped[str] = mapped_column(String(120), default="unknown")
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # extracted variable values, in positional order
    variables: Mapped[list] = mapped_column(JSON, default=list)
    # only stored when it differs from the template's default single-space
    # separators, so the common case stays compact.
    separators: Mapped[list | None] = mapped_column(JSON, nullable=True)
    trailing: Mapped[str] = mapped_column(String(64), default="")


class CompressionRecord(Base, UUIDPk):
    """One benchmark/compression run - every number here is measured, not assumed."""

    __tablename__ = "compression_records"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String(64), default="job")

    original_bytes: Mapped[int] = mapped_column(Integer, default=0)
    compressed_bytes: Mapped[int] = mapped_column(Integer, default=0)   # per-record payloads
    metadata_bytes: Mapped[int] = mapped_column(Integer, default=0)     # template definitions (shared)
    total_compressed_bytes: Mapped[int] = mapped_column(Integer, default=0)  # compressed + metadata
    reduction_pct: Mapped[float] = mapped_column(Float, default=0.0)  # may be negative

    record_count: Mapped[int] = mapped_column(Integer, default=0)
    reconstructable_count: Mapped[int] = mapped_column(Integer, default=0)
    template_count: Mapped[int] = mapped_column(Integer, default=0)

    processing_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    events_per_sec: Mapped[float] = mapped_column(Float, default=0.0)

    method: Mapped[str] = mapped_column(String(48), default="template+varsub")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
