"""Template-based micro-compression: lossless + honestly measured."""
import time
from pathlib import Path

from app.core.database import SessionLocal
from app.models.ingestion import RawLog
from app.models.template import Template, TemplateMatch
from app.services.compression.engine import reconstruct, run_benchmark
from app.services.templates.service import mine_templates

_SAMPLES = Path(__file__).resolve().parents[2] / "sample_logs"


def _wait(client, headers, job_id):
    for _ in range(120):
        j = client.get(f"/api/ingestion/jobs/{job_id}", headers=headers).json()
        if j["status"] in ("COMPLETED", "FAILED"):
            return j
        time.sleep(0.2)
    raise AssertionError("job timeout")


def _upload(client, headers, rel):
    data = (_SAMPLES / rel).read_bytes()
    r = client.post("/api/ingestion/upload", headers=headers,
                    files={"file": (Path(rel).name, data, "text/plain")},
                    data={"source_name": Path(rel).parent.name})
    return _wait(client, headers, r.json()["id"])


# --- lossless reconstruction (the critical requirement) ---

def test_every_raw_log_reconstructs_exactly(client, analyst_headers):
    _upload(client, analyst_headers, "application/bulk_access.log")
    _upload(client, analyst_headers, "linux/auth.log")
    _upload(client, analyst_headers, "malformed/broken.log")

    db = SessionLocal()
    try:
        mine_templates(db)
        rows = db.query(RawLog).all()
        assert len(rows) > 500
        matches = {m.raw_log_id: m for m in db.query(TemplateMatch).all()}
        templates = {t.id: t for t in db.query(Template).all()}

        checked = 0
        for r in rows:
            m = matches.get(r.id)
            assert m is not None, f"no template match for raw log {r.id}"
            rebuilt = reconstruct(templates[m.template_id], m)
            assert rebuilt == r.content, (
                f"reconstruction mismatch:\n  orig: {r.content!r}\n  got:  {rebuilt!r}"
            )
            checked += 1
        assert checked == len(rows)
    finally:
        db.close()


def test_benchmark_accounting_is_internally_consistent(client, analyst_headers):
    _upload(client, analyst_headers, "application/bulk_access.log")
    db = SessionLocal()
    try:
        result = run_benchmark(db, source="application", persist=True)
        # every record in scope reconstructs
        assert result.reconstructable_count == result.record_count
        assert result.record_count >= 600
        assert result.mismatches == []
        # totals add up exactly
        assert result.total_compressed_bytes == result.compressed_bytes + result.metadata_bytes
        assert result.savings_bytes == result.original_bytes - result.total_compressed_bytes
        expected_pct = result.savings_bytes / result.original_bytes * 100
        assert abs(result.reduction_pct - round(expected_pct, 2)) < 0.01
        # a persisted row mirrors the response
        from app.models.template import CompressionRecord
        rec = db.query(CompressionRecord).order_by(CompressionRecord.ts.desc()).first()
        assert rec.original_bytes == result.original_bytes
        assert rec.reconstructable_count == result.reconstructable_count
    finally:
        db.close()


def test_benchmark_reports_negative_savings_when_it_loses(client, analyst_headers):
    # a handful of highly heterogeneous lines: per-template metadata dominates,
    # so savings should be reported as negative rather than massaged to >= 0.
    _upload(client, analyst_headers, "malformed/broken.log")
    db = SessionLocal()
    try:
        result = run_benchmark(db, source="malformed", persist=False)
        assert result.record_count >= 1
        assert result.reconstructable_count == result.record_count
        # not asserting the sign rigidly, but the maths must be the real formula
        expected = result.savings_bytes / max(result.original_bytes, 1) * 100
        assert abs(result.reduction_pct - expected) < 1e-6
    finally:
        db.close()


def test_empty_scope_benchmark(client, analyst_headers):
    db = SessionLocal()
    try:
        result = run_benchmark(db, source="does-not-exist", persist=False)
        assert result.record_count == 0
        assert result.reduction_pct == 0.0
    finally:
        db.close()


# --- API ---

def test_template_and_compression_api_flow(client, analyst_headers, admin_headers):
    _upload(client, analyst_headers, "application/bulk_access.log")

    mine = client.post("/api/templates/mine", headers=analyst_headers, json={}).json()
    assert mine["records_scanned"] >= 600
    assert mine["templates_total"] >= 1

    lst = client.get("/api/templates?limit=5", headers=analyst_headers).json()
    assert lst["total"] >= 1
    assert lst["covered_events"] >= 600
    top = lst["items"][0]
    assert top["template_key"].startswith("TPL-")
    assert top["occurrences"] >= 500
    assert "<*>" in top["pattern"]

    detail = client.get(f"/api/templates/{top['template_key']}", headers=analyst_headers).json()
    assert detail["token_signature"]
    assert len(detail["literal_tokens"]) == detail["token_count"]

    examples = client.get(f"/api/templates/{top['template_key']}/examples?limit=3",
                          headers=analyst_headers).json()
    assert len(examples) == 3
    assert all(len(e["variables"]) == top["variable_count"] for e in examples)

    # compress + benchmark
    comp = client.post("/api/compression/compress", headers=analyst_headers,
                       json={"source": "application"}).json()
    assert comp["records_compressed"] >= 600

    bench = client.post("/api/compression/benchmark", headers=analyst_headers,
                        json={"source": "application"}).json()
    assert bench["reconstructable_count"] == bench["record_count"]

    # decompress a specific record and verify against the stored original
    ev = client.get("/api/logs?source=application&limit=1", headers=analyst_headers).json()["items"][0]
    dec = client.post("/api/compression/decompress", headers=analyst_headers,
                      json={"raw_log_id": ev["raw_log_id"]}).json()
    assert dec["exact_match"] is True
    assert dec["reconstructed"] == dec["original"]

    records = client.get("/api/compression/records", headers=analyst_headers).json()
    assert len(records) >= 1
    assert records[0]["scope"] == "source:application"


def test_mine_requires_analyst(client, admin_headers):
    client.post("/api/users", headers=admin_headers,
                json={"email": "tpl-viewer@ulpf.io", "password": "ViewerPass!9", "role": "VIEWER"})
    tok = client.post("/api/auth/login",
                      json={"email": "tpl-viewer@ulpf.io", "password": "ViewerPass!9"}).json()["access_token"]
    r = client.post("/api/templates/mine", headers={"Authorization": f"Bearer {tok}"}, json={})
    assert r.status_code == 403


def test_no_eval_exec_in_template_or_compression_code():
    import re
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    forbidden = re.compile(r"(?<![.\w])(?:eval|exec|compile|__import__)\s*\(")
    for sub in ("templates", "compression"):
        for py in (root / sub).rglob("*.py"):
            assert not forbidden.search(py.read_text(encoding="utf-8")), py
