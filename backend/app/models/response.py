"""Response-simulation records (Module 28).

Every row here is a SIMULATION. Nothing in this module or the services that
write it touches real infrastructure - see docs/security-model.md.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import UUIDPk, utcnow


class ResponseSimulation(Base, UUIDPk):
    __tablename__ = "response_simulations"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    alert_id: Mapped[str] = mapped_column(ForeignKey("security_alerts.id"), index=True)
    alert_title: Mapped[str] = mapped_column(String(200), default="")
    alert_rule_key: Mapped[str | None] = mapped_column(String(48), nullable=True)
    alert_severity: Mapped[str] = mapped_column(String(16), default="")
    alert_risk_score: Mapped[float] = mapped_column(Float, default=0.0)

    # deterministic recommendation derived from real ULPF evidence
    recommendation: Mapped[dict] = mapped_column(JSON, default=dict)
    # structured simulated actions (each carries mode = SIMULATION_ONLY)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    # simulated before/after state + expected outcome text
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(Text, default="")

    # hard-coded True; there is no code path that sets this False.
    simulation_only: Mapped[bool] = mapped_column(Boolean, default=True)
