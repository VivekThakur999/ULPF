from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class TemplateOut(BaseModel):
    id: str
    template_key: str
    pattern: str
    token_count: int
    variable_count: int
    variable_types: list[Optional[str]]
    occurrences: int
    source_distribution: dict[str, int]
    example: str
    first_seen: datetime
    last_seen: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateDetailOut(TemplateOut):
    literal_tokens: list[Optional[str]]
    separators: list[str]
    trailing: str
    token_signature: str
    examples: list[dict[str, Any]]


class TemplateListOut(BaseModel):
    total: int
    items: list[TemplateOut]
    covered_events: int
    unique_sources: int
    avg_variables: float


class MineRequest(BaseModel):
    source: Optional[str] = None
    time_from: Optional[datetime] = None
    time_to: Optional[datetime] = None
    limit: Optional[int] = None


class MineResponse(BaseModel):
    records_scanned: int
    records_matched: int
    templates_total: int
    templates_created: int
    templates_updated: int
    duration_seconds: float
    scan_limit_hit: bool
    template_keys: list[str]


class TemplateExampleOut(BaseModel):
    raw_log_id: str
    source: str
    ts: Optional[str]
    raw: str
    variables: list[str]
