"""Automatic log format detection (Module 5).

Combines parser self-assessment (can_parse) with a few structural signatures.
Returns the winning format + confidence + the full candidate list.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from app.services.parsing.registry import ParserRegistry, registry as default_registry

# canonical format keys the framework recognises
FORMATS = {
    "SYSLOG", "LINUX_AUTH", "APACHE_COMBINED", "NGINX_ACCESS",
    "FIREWALL", "JSON", "KEYVALUE", "CSV", "GENERIC_TEXT", "UNKNOWN",
}


@dataclass
class DetectionResult:
    format: str = "UNKNOWN"
    confidence: float = 0.0
    candidates: list[dict] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "format": self.format,
            "confidence": round(self.confidence, 3),
            "candidates": self.candidates,
            "signals": self.signals,
        }


class FormatDetector:
    def __init__(self, reg: ParserRegistry | None = None):
        self.registry = reg or default_registry

    def _looks_like_csv(self, sample: str) -> float:
        lines = [ln for ln in sample.splitlines() if ln.strip()][:20]
        if len(lines) < 2:
            return 0.0
        try:
            dialect = csv.Sniffer().sniff("\n".join(lines))
        except csv.Error:
            return 0.0
        reader = list(csv.reader(io.StringIO("\n".join(lines)), dialect))
        widths = {len(r) for r in reader if r}
        if len(widths) == 1 and next(iter(widths)) >= 3:
            return 0.85
        if len(widths) <= 2 and max(widths) >= 3:
            return 0.6
        return 0.2

    def detect(self, sample: str, *, hint: str | None = None) -> DetectionResult:
        sample = sample or ""
        if not sample.strip():
            return DetectionResult(format="UNKNOWN", confidence=0.0, signals=["empty input"])

        scored = self.registry.score_all(sample)
        candidates: list[dict] = []
        for parser, score in scored:
            if parser.name == "raw":
                continue
            candidates.append({"format": parser.format, "parser": parser.name,
                               "confidence": round(score, 3),
                               "specificity": getattr(parser, "specificity", 3)})

        csv_score = self._looks_like_csv(sample)
        if csv_score > 0:
            candidates.append({"format": "CSV", "parser": "csv",
                               "confidence": round(csv_score, 3), "specificity": 3})

        candidates.sort(key=lambda c: (c["confidence"], c["specificity"]), reverse=True)
        best = candidates[0] if candidates else {"format": "UNKNOWN", "confidence": 0.0}

        signals: list[str] = []
        fmt = best["format"]
        conf = best["confidence"]

        if hint and hint in FORMATS:
            for c in candidates:
                if c["format"] == hint and c["confidence"] > 0.2:
                    fmt, conf = hint, max(conf, c["confidence"])
                    signals.append(f"user hint '{hint}' corroborated")
                    break

        if conf < 0.35:
            # nothing structured matched well - is it at least plain text?
            fmt = "GENERIC_TEXT" if sample.strip() else "UNKNOWN"
            conf = 0.3 if fmt == "GENERIC_TEXT" else 0.0
            signals.append("no strong structural match; treated as generic text")

        return DetectionResult(format=fmt, confidence=conf, candidates=candidates[:6],
                               signals=signals)


detector = FormatDetector()
