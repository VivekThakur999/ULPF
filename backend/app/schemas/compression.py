from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CompressRequest(BaseModel):
    job_id: Optional[str] = None
    source: Optional[str] = None
    limit: Optional[int] = None


class CompressResponse(BaseModel):
    records_in_scope: int
    records_compressed: int
    templates_used: int
    mining_summary: dict[str, Any]


class BenchmarkRequest(BaseModel):
    job_id: Optional[str] = None
    source: Optional[str] = None
    limit: Optional[int] = None


class BenchmarkResponse(BaseModel):
    scope: str
    record_count: int
    reconstructable_count: int
    template_count: int
    original_bytes: int
    compressed_bytes: int
    metadata_bytes: int
    total_compressed_bytes: int
    savings_bytes: int
    reduction_pct: float
    processing_seconds: float
    events_per_sec: float
    mismatches: list[dict[str, Any]]


class DecompressRequest(BaseModel):
    raw_log_id: str = Field(min_length=1)


class DecompressResponse(BaseModel):
    raw_log_id: str
    template_key: Optional[str]
    original: str
    reconstructed: Optional[str]
    exact_match: bool
    variables: list[str]


class CompressionRecordOut(BaseModel):
    id: str
    ts: datetime
    job_id: Optional[str]
    scope: str
    original_bytes: int
    compressed_bytes: int
    metadata_bytes: int
    total_compressed_bytes: int
    reduction_pct: float
    record_count: int
    reconstructable_count: int
    template_count: int
    processing_seconds: float
    events_per_sec: float
    method: str

    class Config:
        from_attributes = True
