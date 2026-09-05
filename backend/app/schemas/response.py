from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SimulateRequest(BaseModel):
    # only an alert id is accepted - no actions, no targets, no firewall syntax.
    model_config = {"extra": "forbid"}
    alert_id: str = Field(min_length=1)


class RecommendationOut(BaseModel):
    category: str
    available: bool
    label: str
    rationale: str
    actions: list[dict[str, Any]]
    evidence: dict[str, Any]


class SimulateResponse(BaseModel):
    simulation: bool
    disclaimer: str
    audit_id: str
    alert: dict[str, Any]
    recommendation: RecommendationOut
    actions: list[dict[str, Any]]
    result: dict[str, Any]
    evidence: dict[str, Any]


class RecommendResponse(BaseModel):
    alert: dict[str, Any]
    recommendation: RecommendationOut
    evidence: dict[str, Any]


class SimulationRecordOut(BaseModel):
    id: str
    ts: datetime
    actor_email: Optional[str]
    alert_id: str
    alert_title: str
    alert_rule_key: Optional[str]
    alert_severity: str
    alert_risk_score: float
    recommendation: dict[str, Any]
    actions: list[dict[str, Any]]
    result: dict[str, Any]
    simulation_only: bool

    class Config:
        from_attributes = True
