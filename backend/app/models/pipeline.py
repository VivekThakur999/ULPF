"""Saved pipeline debugger runs (Module 19)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import UUIDPk, utcnow


class PipelineRun(Base, UUIDPk):
    __tablename__ = "pipeline_runs"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    label: Mapped[str] = mapped_column(String(160), default="")
    raw_input: Mapped[str] = mapped_column(Text, default="")
    # Full ordered list of stage results captured during the run.
    stages: Mapped[list] = mapped_column(JSON, default=list)
    final_event: Mapped[dict] = mapped_column(JSON, default=dict)
    pii_mode: Mapped[str] = mapped_column(String(24), default="OFF")
    saved: Mapped[bool] = mapped_column(default=False)
