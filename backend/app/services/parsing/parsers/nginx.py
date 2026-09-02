"""Nginx access log parser.

Accepts the default `combined` format plus an extended format carrying
X-Forwarded-For and request timing, which is what our sample data uses so the
detector can distinguish it from Apache.
"""
from __future__ import annotations

from app.services.parsing.base import ParseResult, RegexParser

_EXTENDED = (
    r'^(?P<source_ip>[\da-fA-F.:]+)\s+-\s+(?P<username>\S+)\s+'
    r'\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<http_method>[A-Z]+)\s+(?P<url>\S+)\s+(?P<http_version>[^"]+)"\s+'
    r'(?P<response_code>\d{3})\s+(?P<bytes>\d+)\s+'
    r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"\s+'
    r'"(?P<x_forwarded_for>[^"]*)"'
    r'(?:\s+rt=(?P<request_time>[\d.]+))?'
    r'(?:\s+uct="(?P<upstream_connect_time>[^"]*)")?'
    r'(?:\s+urt="(?P<upstream_response_time>[^"]*)")?'
)
_COMBINED = (
    r'^(?P<source_ip>[\da-fA-F.:]+)\s+-\s+(?P<username>\S+)\s+'
    r'\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<http_method>[A-Z]+)\s+(?P<url>\S+)\s+(?P<http_version>[^"]+)"\s+'
    r'(?P<response_code>\d{3})\s+(?P<bytes>\d+)\s+'
    r'"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)"'
)


class NginxParser(RegexParser):
    name = "nginx"
    version = "1.0.0"
    format = "NGINX_ACCESS"
    specificity = 5
    description = "Nginx access log (combined / extended with XFF + timing)"
    patterns = [_EXTENDED, _COMBINED]
    detect_hints = [r'"\s*-\s*"\s+rt=', r'urt="', r'\s"[\d.]+,\s*[\d.]+"\s*$']
    default_event_type = "http_request"

    def can_parse(self, sample: str) -> float:
        score = super().can_parse(sample)
        # Only claim plain combined logs weakly - Apache should win that tie.
        if "rt=" not in sample and "urt=" not in sample and 'for" "' not in sample:
            score *= 0.6
        return round(score, 3)

    def _post_parse(self, line, match, result: ParseResult) -> None:
        f = result.fields
        if f.get("username") == "-":
            f.pop("username", None)
        f["service"] = "http"
        f["protocol"] = "tcp"
        xff = f.pop("x_forwarded_for", None)
        if xff and xff != "-":
            f["x_forwarded_for"] = xff
        try:
            code = int(f.get("response_code", 0))
            f["status"] = "success" if code < 400 else "failure"
            if code >= 500:
                f["severity"] = "high"
            elif code >= 400:
                f["severity"] = "medium"
        except ValueError:
            pass
        result.confidence = 0.96
