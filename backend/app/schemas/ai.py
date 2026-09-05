from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class ExplainRequest(BaseModel):
    kind: Literal["event", "alert", "raw"]
    event_id: Optional[str] = None
    alert_id: Optional[str] = None
    text: Optional[str] = Field(default=None, max_length=200_000)

    @model_validator(mode="after")
    def _check(self) -> "ExplainRequest":
        if self.kind == "event" and not self.event_id:
            raise ValueError("event_id is required for kind=event")
        if self.kind == "alert" and not self.alert_id:
            raise ValueError("alert_id is required for kind=alert")
        if self.kind == "raw" and not (self.text and self.text.strip()):
            raise ValueError("text is required for kind=raw")
        return self


class ImportantFieldOut(BaseModel):
    field: str
    value: str
    note: str


class ExplanationOut(BaseModel):
    provider: str
    offline: bool
    model: Optional[str]
    summary: str
    important_fields: list[ImportantFieldOut]
    why_it_matters: str
    detection_context: str
    related_activity: str
    suggested_steps: list[str]
    disclaimer: str
    fallback_from: Optional[str] = None


class ExplainResponse(BaseModel):
    kind: str
    generated_at: str
    provider: str
    offline: bool
    model: Optional[str]
    evidence: dict[str, Any]
    explanation: ExplanationOut


class AIStatusResponse(BaseModel):
    provider: str
    offline: bool
    model: Optional[str]
    available: bool
    fallback_active: bool
    note: str
