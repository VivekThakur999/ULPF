from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.source import SOURCE_CATEGORIES

_ADAPTERS = {"FILE", "SYSLOG", "HTTP", "WINDOWS", "FIREWALL", "SIMULATED"}


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = "generic"
    adapter: str = "FILE"
    description: str = Field(default="", max_length=500)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True

    def validate_enums(self) -> None:
        if self.category not in SOURCE_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(SOURCE_CATEGORIES)}")
        if self.adapter not in _ADAPTERS:
            raise ValueError(f"adapter must be one of {sorted(_ADAPTERS)}")


class SourceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=120)
    category: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=500)
    config: Optional[dict[str, Any]] = None
    enabled: Optional[bool] = None


class SourceOut(BaseModel):
    id: str
    name: str
    category: str
    adapter: str
    description: str
    config: dict[str, Any]
    enabled: bool
    connection_status: str
    last_received_at: Optional[datetime]
    events_processed: int
    created_at: datetime

    class Config:
        from_attributes = True
