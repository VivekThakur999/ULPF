"""Parser registry - resolves format keys and best-effort parser selection."""
from __future__ import annotations

from app.core.logging import get_logger
from app.services.parsing.base import BaseParser, ParseResult
from app.services.parsing.parsers.apache import ApacheParser
from app.services.parsing.parsers.firewall import FirewallParser
from app.services.parsing.parsers.json_parser import JSONParser
from app.services.parsing.parsers.keyvalue import GenericKeyValueParser
from app.services.parsing.parsers.linux_auth import LinuxAuthParser
from app.services.parsing.parsers.nginx import NginxParser
from app.services.parsing.parsers.syslog import SyslogParser

log = get_logger("parsing")


class RawFallbackParser(BaseParser):
    """Always "parses": keeps the line as message so nothing is silently lost."""

    name = "raw"
    version = "1.0.0"
    format = "UNKNOWN"
    description = "Fallback - preserves the raw line as the message"

    def can_parse(self, sample: str) -> float:
        return 0.01

    def parse(self, line: str) -> ParseResult:
        return ParseResult(fields={"message": line}, confidence=0.1,
                           event_type="generic", partial=True)


# order matters only for stable tie-breaking; selection is score-based
_BUILTINS: list[BaseParser] = [
    LinuxAuthParser(),
    SyslogParser(),
    ApacheParser(),
    NginxParser(),
    FirewallParser(),
    JSONParser(),
    GenericKeyValueParser(),
    RawFallbackParser(),
]


class ParserRegistry:
    def __init__(self, parsers: list[BaseParser] | None = None):
        self._parsers = parsers if parsers is not None else list(_BUILTINS)
        self._by_format = {p.format: p for p in self._parsers}
        self._by_name = {p.name: p for p in self._parsers}

    # --- registration (used by parser packs / wasm later) ---
    def register(self, parser: BaseParser, *, replace: bool = True) -> None:
        if parser.name in self._by_name and not replace:
            raise ValueError(f"parser {parser.name} already registered")
        self._parsers = [p for p in self._parsers if p.name != parser.name]
        self._parsers.insert(0, parser)
        self._by_format[parser.format] = parser
        self._by_name[parser.name] = parser

    def all(self) -> list[BaseParser]:
        return list(self._parsers)

    def get_by_format(self, fmt: str) -> BaseParser | None:
        return self._by_format.get(fmt)

    def get_by_name(self, name: str) -> BaseParser | None:
        return self._by_name.get(name)

    def score_all(self, sample: str) -> list[tuple[BaseParser, float]]:
        scored = [(p, p.can_parse(sample)) for p in self._parsers]
        # higher score wins; ties broken by parser specificity
        scored.sort(key=lambda t: (round(t[1], 3), getattr(t[0], "specificity", 3)), reverse=True)
        return scored

    def select(self, sample: str, *, hint_format: str | None = None) -> tuple[BaseParser, float]:
        """Pick the best parser for a sample. A valid hint_format wins if it scores > 0."""
        if hint_format and hint_format in self._by_format:
            p = self._by_format[hint_format]
            s = p.can_parse(sample)
            if s > 0.2:
                return p, s
        scored = self.score_all(sample)
        best, score = scored[0]
        if score <= 0.0:
            return self._by_name["raw"], 0.1
        return best, score


registry = ParserRegistry()
