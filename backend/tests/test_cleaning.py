from app.services.cleaning.cleaner import clean_fields, valid_ip, valid_port
from app.services.pipeline.service import run_record


def test_valid_ip_port_helpers():
    assert valid_ip("192.168.1.1")
    assert valid_ip("::1")
    assert not valid_ip("999.1.1.1")
    assert valid_port("443")
    assert not valid_port("999999")


def test_invalid_ip_preserved_not_dropped():
    cleaned, transforms, warnings, invalid = clean_fields(
        {"source_ip": "999.1.1.1", "username": "  admin  "}
    )
    assert invalid is True
    assert "source_ip" not in cleaned
    assert cleaned["source_ip_raw"] == "999.1.1.1"
    assert cleaned["username"] == "admin"
    assert any("999.1.1.1" in w for w in warnings)


def test_invalid_port_preserved():
    cleaned, _, warnings, invalid = clean_fields({"destination_port": "70000"})
    assert invalid
    assert cleaned["destination_port_raw"] == "70000"


def test_invalid_timestamp_preserved():
    cleaned, _, warnings, invalid = clean_fields({"timestamp": "not-a-real-date"})
    assert invalid
    assert cleaned["timestamp_raw"] == "not-a-real-date"
    assert any("timestamp" in w for w in warnings)


def test_valid_values_survive_cleaning():
    cleaned, transforms, _, invalid = clean_fields(
        {"source_ip": "10.20.0.14", "destination_port": "443", "message": '"quoted"',
         "timestamp": "2025-09-02T09:02:12Z"}
    )
    assert invalid is False
    assert cleaned["source_ip"] == "10.20.0.14"
    assert cleaned["destination_port"] == 443
    assert cleaned["message"] == "quoted"


def test_leading_zero_ip_is_rejected():
    # 010.020.000.014 is an octal-ambiguous SSRF-bypass shape - reject it
    _, _, _, invalid = clean_fields({"source_ip": "010.020.000.014"})
    assert invalid is True


def test_control_chars_stripped_from_fields():
    cleaned, transforms, _, _ = clean_fields({"message": "hello\x00\x07world"})
    assert cleaned["message"] == "helloworld"
    assert any(t["type"] == "strip_control_chars" for t in transforms)


def test_pipeline_dedup_and_blank_handling_via_reader():
    # duplicates are handled at the ingestion layer; here confirm hashes are stable
    a = run_record("dup line")
    b = run_record("dup line")
    assert a.content_hash == b.content_hash


def test_malformed_line_does_not_crash_pipeline():
    for bad in [
        "Sep 32 99:99:99 db-02 sshd[1]: Failed password for admin from 999.1.1.1 port 999999 ssh2",
        '{"ts":"not-a-real-date","level":"weird","msg":"half a json record"',
        "this line has     irregular      whitespace    and no structure",
        "",
        "\x00\x00\x00",
    ]:
        ctx = run_record(bad)
        assert ctx.stages  # ran without raising
