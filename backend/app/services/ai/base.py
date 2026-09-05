"""AI explanation provider interface (Module 22).

AI is strictly an *explanation* layer. It never determines detection, severity,
risk, correlation or alerting - those stay with ULPF's deterministic engine.
A provider is handed already-retrieved, sanitized ULPF evidence and returns a
structured, human-readable explanation of it.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

ADVISORY_DISCLAIMER = (
    "AI explanations are advisory only and do not determine security decisions. "
    "ULPF's deterministic rules, severity, risk score and alerts remain authoritative."
)


@dataclass
class ImportantField:
    field: str
    value: str
    note: str = ""

    def to_dict(self) -> dict:
        return {"field": self.field, "value": self.value, "note": self.note}


@dataclass
class Explanation:
    provider: str
    offline: bool
    model: str | None
    summary: str
    important_fields: list[ImportantField] = field(default_factory=list)
    why_it_matters: str = ""
    detection_context: str = ""
    related_activity: str = ""
    suggested_steps: list[str] = field(default_factory=list)
    disclaimer: str = ADVISORY_DISCLAIMER
    fallback_from: str | None = None  # set when a preferred provider was unavailable

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "offline": self.offline,
            "model": self.model,
            "summary": self.summary,
            "important_fields": [f.to_dict() for f in self.important_fields],
            "why_it_matters": self.why_it_matters,
            "detection_context": self.detection_context,
            "related_activity": self.related_activity,
            "suggested_steps": self.suggested_steps,
            "disclaimer": self.disclaimer,
            "fallback_from": self.fallback_from,
        }


@dataclass
class ExplainContext:
    """Server-retrieved, sanitized ULPF evidence for one explanation request."""

    kind: str  # "event" | "alert" | "raw"
    # authoritative ULPF data (never AI-generated) - also returned to the UI
    evidence: dict[str, Any] = field(default_factory=dict)
    # the natural-language-ready projection used to build/prompt the explanation
    event: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None
    related_events: list[dict[str, Any]] = field(default_factory=list)
    correlation: dict[str, Any] = field(default_factory=dict)
    parser: dict[str, Any] = field(default_factory=dict)
    raw_untrusted: bool = False


class ProviderUnavailable(RuntimeError):
    """Raised by a provider that cannot service the request (falls back to offline)."""


class AIProvider(ABC):
    name: str = "provider"
    offline: bool = True
    model: str | None = None

    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def explain(self, ctx: ExplainContext) -> Explanation:
        ...
