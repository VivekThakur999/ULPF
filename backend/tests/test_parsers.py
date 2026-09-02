"""Each parser must ultimately produce a valid UniversalLogEvent."""
import pytest

from app.services.parsing.registry import registry
from app.services.pipeline.service import run_record

PARSER_CASES = [
    (
        "linux_auth",
        "Sep  2 09:02:11 db-02 sshd[4412]: Failed password for admin from 192.168.1.50 port 44210 ssh2",
        {"event_type": "authentication_failure", "username": "admin",
         "source_ip": "192.168.1.50", "source_port": 44210, "host": "db-02"},
    ),
    (
        "linux_auth",
        "Sep  2 08:14:02 web-01 sshd[20413]: Accepted password for jdoe from 10.20.0.14 port 51522 ssh2",
        {"event_type": "authentication_success", "username": "jdoe", "source_ip": "10.20.0.14"},
    ),
    (
        "apache",
        '203.0.113.44 - - [02/Sep/2025:10:15:01 +0000] "POST /api/login HTTP/1.1" 401 173 "-" "python-requests/2.31"',
        {"event_type": "http_request", "http_method": "POST", "url": "/api/login",
         "response_code": 401, "source_ip": "203.0.113.44"},
    ),
    (
        "nginx",
        '10.20.0.14 - - [02/Sep/2025:08:16:11 +0000] "GET /api/v1/me HTTP/2.0" 200 421 "https://portal.corp.example/" "Mozilla/5.0" "-" rt=0.012 uct="0.001" urt="0.011"',
        {"event_type": "http_request", "http_method": "GET", "response_code": 200,
         "source_ip": "10.20.0.14"},
    ),
    (
        "firewall",
        "Sep  2 09:01:55 fw kernel: [488213.114] IPTABLES DROP IN=eth0 SRC=192.168.1.50 DST=10.20.0.20 PROTO=TCP SPT=44208 DPT=22 SYN",
        {"event_type": "connection_denied", "source_ip": "192.168.1.50",
         "destination_ip": "10.20.0.20", "destination_port": 22, "action": "deny"},
    ),
    (
        "firewall",
        'date=2025-09-02 time=09:01:50 devname=fw-01 action=deny srcip=192.168.1.50 dstip=10.20.0.20 dstport=22 proto=6 service=SSH',
        {"event_type": "connection_denied", "source_ip": "192.168.1.50", "destination_port": 22},
    ),
    (
        "json",
        '{"ts":"2025-09-02T09:02:12Z","level":"warning","logger":"auth-svc","event":"login_failed","user":"admin","src_ip":"192.168.1.50"}',
        {"event_type": "authentication_failure", "username": "admin",
         "source_ip": "192.168.1.50", "severity": "medium"},
    ),
]


@pytest.mark.parametrize("expected_parser,line,expected_fields", PARSER_CASES)
def test_parser_end_to_end(expected_parser, line, expected_fields):
    ctx = run_record(line, pii_mode="OFF")
    assert ctx.parser_name == expected_parser, f"got {ctx.parser_name}"
    assert ctx.event is not None, ctx.errors
    ev = ctx.event
    for key, value in expected_fields.items():
        assert getattr(ev, key) == value, f"{key}: {getattr(ev, key)!r} != {value!r}"
    # schema invariants
    assert ev.schema_version == "1.0"
    assert ev.raw_log == line
    assert ev.parser_version


def test_every_builtin_parser_self_validates():
    for parser in registry.all():
        assert parser.validate() == [], f"{parser.name}: {parser.validate()}"


def test_raw_fallback_never_loses_the_line():
    line = "◊◊ totally unstructured gibberish ◊◊ 12345"
    ctx = run_record(line, pii_mode="OFF")
    assert ctx.event is not None
    assert ctx.event.message  # the line is preserved somewhere
    assert ctx.event.raw_log == line
    assert ctx.event.processing_status in ("partial", "ok")
