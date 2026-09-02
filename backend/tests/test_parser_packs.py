"""Parser packs: declarative-only, validated, versioned, no code execution."""
from app.services.parsing.declarative import DeclarativeParser
from app.services.parsing.packs import load_disk_packs
from app.services.pipeline.service import run_record

_HAPROXY = ('Sep  2 10:15:03 lb-01 haproxy[2213]: 203.0.113.44:51000 '
            '[02/Sep/2025:10:15:03.221] fe_http be_api/web-03 12/0/1/4/17 401 173 '
            '- - ---- 8/8/0/0/0 0/0 "POST /api/login HTTP/1.1"')
_CEF = ('Sep  2 09:02:10 siem CEF:0|Vendor|IDS|1.0|1001|SSH brute force detected|8|'
        'src=192.168.1.50 dst=10.20.0.20 spt=44208 dpt=22 act=blocked proto=TCP')


def test_disk_packs_load_and_selftest():
    packs = {p.name: p for p in load_disk_packs()}
    assert {"haproxy", "cef", "postgresql"} <= set(packs)
    for name, p in packs.items():
        assert p.validate() == [], f"{name}: {p.validate()}"
        report = p.run_tests()
        assert report["passed"] == report["total"] and report["total"] >= 1, f"{name}: {report}"


def test_declarative_rejects_bad_regex_and_unknown_transform():
    bad = DeclarativeParser({
        "parser": {"name": "bad"},
        "patterns": ["(?P<x>[unclosed"],
        "transformations": {"x": "explode"},
    })
    problems = bad.validate()
    assert any("invalid regex" in p for p in problems)
    assert any("unknown type" in p for p in problems)


def test_declarative_only_runs_whitelisted_transforms():
    # a "transform" that looks like code must not be honoured
    p = DeclarativeParser({
        "parser": {"name": "t", "format": "T"},
        "patterns": [r"^v=(?P<v>\S+)$"],
        "transformations": {"v": {"type": "__import__('os').system"}},
    })
    assert any("unknown type" in x for x in p.validate())


def test_pack_produces_universal_event_via_pipeline():
    ctx = run_record(_HAPROXY, pii_mode="OFF")
    assert ctx.parser_name == "haproxy"
    e = ctx.event
    assert e.source_ip == "203.0.113.44"
    assert e.response_code == 401
    assert e.http_method == "POST"
    assert e.schema_version == "1.0"


def test_cef_kv_expansion():
    ctx = run_record(_CEF, pii_mode="OFF")
    assert ctx.parser_name == "cef"
    e = ctx.event
    assert e.source_ip == "192.168.1.50"
    assert e.destination_port == 22
    assert e.action == "blocked"


# --- API: CRUD + versioning ---

_PACK_YAML = r"""
parser:
  name: test_apitest
  version: 1.0.0
  format: APITEST
  specificity: 6
patterns:
  - '^APITEST (?P<username>\S+) from (?P<source_ip>\S+) code=(?P<response_code>\d+)$'
transformations:
  response_code: int
event_type:
  default: generic
tests:
  - input: 'APITEST alice from 10.0.0.5 code=200'
    expect: { username: alice, source_ip: 10.0.0.5, response_code: 200 }
"""


def test_parser_pack_crud_and_versioning(client, admin_headers, analyst_headers):
    # list includes builtins + disk packs
    r = client.get("/api/parsers", headers=analyst_headers)
    assert r.status_code == 200
    names = {p["name"] for p in r.json()["parsers"]}
    assert {"linux_auth", "haproxy", "cef"} <= names

    # analyst cannot create
    assert client.post("/api/parsers", headers=analyst_headers,
                       json={"yaml_text": _PACK_YAML}).status_code == 403

    # validate (dry run)
    v = client.post("/api/parsers/validate", headers=analyst_headers,
                    json={"yaml_text": _PACK_YAML})
    assert v.status_code == 200 and v.json()["valid"] is True
    assert v.json()["tests"]["passed"] == 1

    # admin creates -> registered live
    c = client.post("/api/parsers", headers=admin_headers, json={"yaml_text": _PACK_YAML})
    assert c.status_code == 201, c.text
    assert c.json()["tests"]["passed"] == 1

    # now usable by the pipeline
    t = client.post("/api/parsers/test_apitest/test", headers=analyst_headers,
                    json={"sample": "APITEST bob from 10.0.0.9 code=404"})
    assert t.status_code == 200
    assert t.json()["fields"]["username"] == "bob"
    assert t.json()["fields"]["response_code"] == 404

    # new version
    v2 = _PACK_YAML.replace("version: 1.0.0", "version: 1.1.0")
    c2 = client.post("/api/parsers", headers=admin_headers, json={"yaml_text": v2})
    assert c2.status_code == 201

    hist = client.get("/api/parsers/test_apitest/versions", headers=analyst_headers).json()
    assert hist["latest_version"] == "1.1.0"
    versions = [v["version"] for v in hist["versions"]]
    assert "1.0.0" in versions and "1.1.0" in versions
    assert sum(1 for v in hist["versions"] if v["is_active"]) == 1


def test_cannot_shadow_builtin_parser(client, admin_headers):
    shadow = _PACK_YAML.replace("name: test_apitest", "name: linux_auth")
    r = client.post("/api/parsers", headers=admin_headers, json={"yaml_text": shadow})
    assert r.status_code == 409


def test_pack_with_failing_selftests_is_rejected(client, admin_headers):
    broken = _PACK_YAML.replace("username: alice", "username: WRONG")
    r = client.post("/api/parsers", headers=admin_headers, json={"yaml_text": broken})
    assert r.status_code == 422
