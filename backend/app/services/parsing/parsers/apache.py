"""Apache access log parser (common + combined log format)."""
from __future__ import annotations

from app.services.parsing.base import ParseResult, RegexParser

_COMBINED = (
    r'^(?P<source_ip>[\da-fA-F.:]+)\s+\S+\s+(?P<username>\S+)\s+'
    r'\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<http_method>[A-Z]+)\s+(?P<url>\S+)\s+(?P<http_version>[^"]+)"\s+'
    r'(?P<response_code>\d{3})\s+(?P<bytes>\d+|-)'
    r'(?:\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
)


class ApacheParser(RegexParser):
    name = "apache"
    version = "1.0.0"
    format = "APACHE_COMBINED"
    specificity = 4
    description = "Apache HTTP Server access log (common/combined)"
    patterns = [_COMBINED]
    detect_hints = [
        r'"\s*(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)\s+\S+\s+HTTP/\d',
        r'\[\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2}\s[+\-]\d{4}\]',
    ]
    default_event_type = "http_request"

    def _post_parse(self, line, match, result: ParseResult) -> None:
        f = result.fields
        if f.get("username") == "-":
            f.pop("username", None)
        if f.get("bytes") == "-":
            f["bytes"] = 0
        f["service"] = "http"
        f["protocol"] = "tcp"
        try:
            code = int(f.get("response_code", 0))
            if code >= 500:
                f["severity"] = "high"
                f["status"] = "failure"
            elif code >= 400:
                f["severity"] = "medium"
                f["status"] = "failure"
            else:
                f["status"] = "success"
        except ValueError:
            pass
        result.confidence = 0.96
