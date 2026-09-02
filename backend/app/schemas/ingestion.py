from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class JobOut(BaseModel):
    id: str
    source_id: Optional[str]
    source_name: str
    filename: str
    declared_format: Optional[str]
    detected_format: Optional[str]
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    total_records: int
    processed_records: int
    invalid_records: int
    duplicate_records: int
    quarantined_records: int
    processing_rate: float
    error: str
    stats: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class JobListOut(BaseModel):
    total: int
    items: list[JobOut]


class RawLogOut(BaseModel):
    id: str
    line_number: int
    content: str
    content_hash: str
    status: str
    security_verdict: str
    processing_errors: list[Any]

    class Config:
        from_attributes = True


class DetectRequest(BaseModel):
    sample: str
    hint: Optional[str] = None


class DetectResponse(BaseModel):
    format: str
    confidence: float
    candidates: list[dict[str, Any]]
    signals: list[str]
