"""The Universal Log Event - canonical normalized schema (Module 11)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import UUIDPk, utcnow

SCHEMA_VERSION = "1.0"


class NormalizedEvent(Base, UUIDPk):
    """One canonical event. Every parser, regardless of source, produces this shape.

    Most fields are nullable on purpose - not every log carries every field.
    """

    __tablename__ = "normalized_events"

    # provenance
    job_id: Mapped[str | None] = mapped_column(ForeignKey("processing_jobs.id"), nullable=True, index=True)
    raw_log_id: Mapped[str | None] = mapped_column(ForeignKey("raw_logs.id"), nullable=True, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    # core universal fields
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(120), default="unknown", index=True)
    host: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    event_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)

    username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    destination_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    destination_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    protocol: Mapped[str | None] = mapped_column(String(16), nullable=True)

    action: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(48), nullable=True)
    process: Mapped[str | None] = mapped_column(String(128), nullable=True)
    service: Mapped[str | None] = mapped_column(String(128), nullable=True)

    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    message: Mapped[str] = mapped_column(Text, default="")

    # extra parsed fields that don't map to a column
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
    # per-field extraction confidence, e.g. {"source_ip": 0.99}
    field_confidence: Mapped[dict] = mapped_column(JSON, default=dict)

    # raw + processing metadata
    raw_log: Mapped[str] = mapped_column(Text, default="")
    parser: Mapped[str] = mapped_column(String(64), default="unknown")
    parser_version: Mapped[str] = mapped_column(String(24), default="0.0")
    schema_version: Mapped[str] = mapped_column(String(8), default=SCHEMA_VERSION)
    pii_protected: Mapped[bool] = mapped_column(default=False)
    pii_mode: Mapped[str] = mapped_column(String(24), default="OFF")
    processing_status: Mapped[str] = mapped_column(String(16), default="ok", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    # template mining (Module 23/24)
    template_id: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_event_src_ip_ts", "source_ip", "timestamp"),
        Index("ix_event_user_ts", "username", "timestamp"),
        Index("ix_event_type_ts", "event_type", "timestamp"),
        Index("ix_event_source_ts", "source", "timestamp"),
        Index("ix_event_host_ts", "host", "timestamp"),
        Index("ix_event_severity_ts", "severity", "timestamp"),
    )
