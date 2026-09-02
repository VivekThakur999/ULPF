from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.event import EventOut


class LogSearchResponse(BaseModel):
    total: int
    items: list[EventOut]
    limit: int
    offset: int
    note: Optional[str] = None  # e.g. "search term pseudonymized to IP_7F82A1"


class PipelineStageView(BaseModel):
    stage: str
    status: str
    summary: str
    fields: dict[str, Any]
    transformations: list[dict[str, Any]]
    warnings: list[str]
    errors: list[str]


class LogDetailResponse(BaseModel):
    event: EventOut
    raw_log: Optional[dict[str, Any]] = None
    job: Optional[dict[str, Any]] = None
    pipeline: list[PipelineStageView]
    pii_transformations: list[dict[str, Any]]
    related_events: list[EventOut]
    security_events: list[dict[str, Any]]


class AlertOut(BaseModel):
    id: str
    ts: datetime
    title: str
    severity: str
    risk_score: float
    source: str
    rule_key: Optional[str]
    description: str
    reason: str
    risk_breakdown: dict[str, Any]
    entity: dict[str, Any]
    related_event_ids: list[str]
    affected_hosts: list[str]
    recommended_response: dict[str, Any]
    status: str
    resolution_note: str
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    total: int
    items: list[AlertOut]


class AlertDetailResponse(BaseModel):
    alert: AlertOut
    timeline: list[dict[str, Any]]
    related_events: list[EventOut]
    correlation: dict[str, Any]


class AlertUpdate(BaseModel):
    status: Optional[str] = None
    resolution_note: Optional[str] = None
