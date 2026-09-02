"""Ingestion jobs and preserved raw logs."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import Timestamps, UUIDPk, utcnow

JOB_PENDING = "PENDING"
JOB_RUNNING = "RUNNING"
JOB_COMPLETED = "COMPLETED"
JOB_FAILED = "FAILED"

# Per-record disposition on the raw log.
RAW_STATUS_PENDING = "PENDING"
RAW_STATUS_PROCESSED = "PROCESSED"
RAW_STATUS_INVALID = "INVALID"
RAW_STATUS_DUPLICATE = "DUPLICATE"
RAW_STATUS_QUARANTINED = "QUARANTINED"


class ProcessingJob(Base, UUIDPk, Timestamps):
    __tablename__ = "processing_jobs"

    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("log_sources.id"), nullable=True, index=True
    )
    source_name: Mapped[str] = mapped_column(String(120), default="upload")
    filename: Mapped[str] = mapped_column(String(255), default="")
    declared_format: Mapped[str | None] = mapped_column(String(48), nullable=True)
    detected_format: Mapped[str | None] = mapped_column(String(48), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default=JOB_PENDING, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    total_records: Mapped[int] = mapped_column(Integer, default=0)
    processed_records: Mapped[int] = mapped_column(Integer, default=0)
    invalid_records: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_records: Mapped[int] = mapped_column(Integer, default=0)
    quarantined_records: Mapped[int] = mapped_column(Integer, default=0)

    processing_rate: Mapped[float] = mapped_column(Float, default=0.0)  # records / sec
    error: Mapped[str] = mapped_column(Text, default="")
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class RawLog(Base, UUIDPk):
    __tablename__ = "raw_logs"

    job_id: Mapped[str] = mapped_column(ForeignKey("processing_jobs.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(120), default="upload", index=True)
    line_number: Mapped[int] = mapped_column(Integer, default=0)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # The original bytes-as-text, preserved verbatim for auditability.
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)

    status: Mapped[str] = mapped_column(String(16), default=RAW_STATUS_PENDING, index=True)
    security_verdict: Mapped[str] = mapped_column(String(24), default="SAFE")
    processing_errors: Mapped[list] = mapped_column(JSON, default=list)

    __table_args__ = (
        Index("ix_rawlog_job_status", "job_id", "status"),
        Index("ix_rawlog_job_line", "job_id", "line_number"),
    )
