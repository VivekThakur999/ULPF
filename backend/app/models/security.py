"""Security rules, alerts and shield events."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import Timestamps, UUIDPk, utcnow

ALERT_NEW = "NEW"
ALERT_ACK = "ACKNOWLEDGED"
ALERT_INVESTIGATING = "INVESTIGATING"
ALERT_RESOLVED = "RESOLVED"
ALERT_FALSE_POSITIVE = "FALSE_POSITIVE"
ALERT_STATUSES = (ALERT_NEW, ALERT_ACK, ALERT_INVESTIGATING, ALERT_RESOLVED, ALERT_FALSE_POSITIVE)

SEVERITIES = ("info", "low", "medium", "high", "critical")


class SecurityRule(Base, UUIDPk, Timestamps):
    __tablename__ = "security_rules"

    rule_key: Mapped[str] = mapped_column(String(48), unique=True, index=True)  # e.g. RULE_1
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    threshold: Mapped[int] = mapped_column(Integer, default=5)
    window_seconds: Mapped[int] = mapped_column(Integer, default=120)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)


class SecurityAlert(Base, UUIDPk):
    __tablename__ = "security_alerts"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    title: Mapped[str] = mapped_column(String(200))
    severity: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    source: Mapped[str] = mapped_column(String(120), default="correlation-engine")
    rule_key: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)

    description: Mapped[str] = mapped_column(Text, default="")
    reason: Mapped[str] = mapped_column(Text, default="")  # human-readable "why it triggered"
    # Structured breakdown of the risk score so it is never a black box.
    risk_breakdown: Mapped[dict] = mapped_column(JSON, default=dict)
    # entity focus of the alert (pseudonymized where applicable)
    entity: Mapped[dict] = mapped_column(JSON, default=dict)
    related_event_ids: Mapped[list] = mapped_column(JSON, default=list)
    affected_hosts: Mapped[list] = mapped_column(JSON, default=list)
    recommended_response: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(20), default=ALERT_NEW, index=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolution_note: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    # dedup key so re-running detection does not create duplicate alerts
    dedup_key: Mapped[str] = mapped_column(String(200), index=True, default="")


class SecurityEvent(Base, UUIDPk):
    """Emitted by the Security Shield (Module 4) - not the same as an alert."""

    __tablename__ = "security_events"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    event_type: Mapped[str] = mapped_column(String(48), default="log_shield")
    detection_type: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(120), default="unknown")
    severity: Mapped[str] = mapped_column(String(16), default="medium", index=True)
    verdict: Mapped[str] = mapped_column(String(24), default="SUSPICIOUS", index=True)
    raw_reference: Mapped[str | None] = mapped_column(String(36), nullable=True)  # raw_log id
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    indicators: Mapped[list] = mapped_column(JSON, default=list)
