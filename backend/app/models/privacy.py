"""Administrator privacy / PII configuration (Module 9)."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.common import Timestamps, UUIDPk

PII_OFF = "OFF"
PII_MASK = "MASK"
PII_HASH = "DETERMINISTIC_HASH"
PII_MODES = (PII_OFF, PII_MASK, PII_HASH)


class PiiSetting(Base, UUIDPk, Timestamps):
    """Single-row configuration table (id = 'default')."""

    __tablename__ = "pii_settings"

    mode: Mapped[str] = mapped_column(String(24), default=PII_HASH)
    # Which identifier types to protect.
    protect_ip: Mapped[bool] = mapped_column(Boolean, default=True)
    protect_email: Mapped[bool] = mapped_column(Boolean, default=True)
    protect_username: Mapped[bool] = mapped_column(Boolean, default=True)
    protect_host: Mapped[bool] = mapped_column(Boolean, default=False)
    # Privacy scope label - the same input yields the same pseudonym within a scope.
    scope: Mapped[str] = mapped_column(String(64), default="global")
    # length of the hex suffix in the pseudonym (IP_7F82A1 -> 6)
    token_length: Mapped[int] = mapped_column(Integer, default=6)
    # keep an encrypted/again-hashed reverse map for authorized de-pseudonymization?
    # MVP: never store plaintext; this stays False.
    store_reverse_map: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)
