"""Parser plugin interface (Module 6).

can_parse() -> confidence 0..1
parse()     -> ParseResult (flat field dict + confidence + spans + errors)
validate()  -> list of self-check problems (empty == healthy)
metadata()  -> descriptive dict
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParseResult:
    fields: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    event_type: str | None = None
    partial: bool = False
    errors: list[str] = field(default_factory=list)
    # character spans in the raw line, for the debugger's Regex101-style view
    match_spans: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.fields) and not self.errors


class BaseParser(ABC):
    name: str = "base"
    version: str = "0.0.0"
    format: str = "UNKNOWN"
    description: str = ""
    #: tie-breaker when two parsers report the same can_parse score.
    #: more specific formats (linux_auth, firewall) outrank generic ones (syslog).
    specificity: int = 3

    @abstractmethod
    def can_parse(self, sample: str) -> float:
        ...

    @abstractmethod
    def parse(self, line: str) -> ParseResult:
        ...

    def validate(self) -> list[str]:
        return []

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "format": self.format,
            "description": self.description,
            "kind": "builtin",
        }


class RegexParser(BaseParser):
    """Base for parsers driven by an ordered list of named-group regexes."""

    # subclasses set these
    patterns: list[str] = []
    detect_hints: list[str] = []
    default_event_type: str | None = None

    def __init__(self) -> None:
        self._compiled = [re.compile(p) for p in self.patterns]
        self._hints = [re.compile(h) for h in self.detect_hints]

    def can_parse(self, sample: str) -> float:
        lines = [ln for ln in sample.splitlines() if ln.strip()][:25]
        if not lines:
            return 0.0
        matched = 0
        hint_hit = any(h.search(sample) for h in self._hints) if self._hints else False
        for ln in lines:
            if any(rx.search(ln) for rx in self._compiled):
                matched += 1
        ratio = matched / len(lines)
        score = ratio
        if hint_hit:
            score = min(1.0, score + 0.15)
        return round(score, 3)

    def parse(self, line: str) -> ParseResult:
        for rx in self._compiled:
            m = rx.search(line)
            if not m:
                continue
            fields = {k: v for k, v in m.groupdict().items() if v is not None}
            spans = []
            for k in m.groupdict():
                if m.group(k) is None:
                    continue
                s, e = m.span(k)
                if s >= 0 and e >= 0:
                    spans.append({"field": k, "start": s, "end": e, "text": m.group(k)})
            res = ParseResult(
                fields=fields,
                confidence=0.9,
                event_type=self.default_event_type,
                match_spans=spans,
            )
            self._post_parse(line, m, res)
            return res
        return ParseResult(confidence=0.0, errors=["no pattern matched"], partial=True)

    def _post_parse(self, line: str, match: "re.Match[str]", result: ParseResult) -> None:
        """Hook for subclasses to refine event_type / fields."""

    def validate(self) -> list[str]:
        problems: list[str] = []
        for i, p in enumerate(self.patterns):
            try:
                re.compile(p)
            except re.error as e:
                problems.append(f"pattern[{i}] invalid: {e}")
        return problems
