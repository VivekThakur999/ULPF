"""Log source (connector) configuration."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import Timestamps, UUIDPk

# Adapter kinds the MVP understands.
ADAPTER_FILE = "FILE"
ADAPTER_SYSLOG = "SYSLOG"
ADAPTER_HTTP = "HTTP"
ADAPTER_WINDOWS = "WINDOWS"
ADAPTER_FIREWALL = "FIREWALL"
ADAPTER_SIMULATED = "SIMULATED"

# Logical source categories (used for dashboards / detection hints).
SOURCE_CATEGORIES = (
    "linux",
    "windows",
    "apache",
    "nginx",
    "firewall",
    "network",
    "application",
    "generic",
)


class LogSource(Base, UUIDPk, Timestamps):
    __tablename__ = "log_sources"

    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(32), default="generic", index=True)
    adapter: Mapped[str] = mapped_column(String(32), default=ADAPTER_FILE)
    description: Mapped[str] = mapped_column(String(500), default="")

    # Non-secret adapter configuration only. Secrets belong in env / a vault.
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # connection_status is only ever "CONFIGURED" until an adapter actually
    # verifies connectivity - we never fake a live enterprise connection.
    connection_status: Mapped[str] = mapped_column(String(24), default="CONFIGURED")
    last_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    events_processed: Mapped[int] = mapped_column(Integer, default=0)
