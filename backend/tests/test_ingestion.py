import time
from pathlib import Path

from app.core.database import SessionLocal
from app.models.event import NormalizedEvent

_SAMPLES = Path(__file__).resolve().parents[2] / "sample_logs"


def _wait_job(client, headers, job_id, timeout=15):
    for _ in range(timeout * 5):
        r = client.get(f"/api/ingestion/jobs/{job_id}", headers=headers)
        assert r.status_code == 200
        job = r.json()
        if job["status"] in ("COMPLETED", "FAILED"):
            return job
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def test_upload_linux_auth_end_to_end(client, analyst_headers):
    content = (_SAMPLES / "linux" / "auth.log").read_bytes()
    r = client.post(
        "/api/ingestion/upload",
        headers=analyst_headers,
        files={"file": ("auth.log", content, "text/plain")},
        data={"source_name": "linux-auth", "declared_format": "LINUX_AUTH"},
    )
    assert r.status_code == 202, r.text
    job = _wait_job(client, analyst_headers, r.json()["id"])

    assert job["status"] == "COMPLETED"
    assert job["detected_format"] == "LINUX_AUTH"
    assert job["total_records"] == 14
    assert job["processed_records"] >= 12
    assert job["processing_rate"] > 0

    # normalized events were actually stored
    db = SessionLocal()
    try:
        events = db.query(NormalizedEvent).filter(NormalizedEvent.job_id == job["id"]).all()
        assert len(events) >= 12
        assert all(e.schema_version == "1.0" for e in events)
        assert any(e.event_type == "authentication_failure" for e in events)
        assert any(e.source_ip and e.source_ip.startswith("IP_") for e in events)  # PII on
    finally:
        db.close()


def test_upload_detects_duplicates(client, analyst_headers):
    data = b"\n".join([b"Sep  2 09:02:11 db-02 sshd[1]: Failed password for admin from 1.2.3.4 port 22 ssh2"] * 5)
    r = client.post("/api/ingestion/upload", headers=analyst_headers,
                    files={"file": ("dup.log", data, "text/plain")})
    job = _wait_job(client, analyst_headers, r.json()["id"])
    assert job["total_records"] == 5
    assert job["duplicate_records"] == 4
    assert job["processed_records"] == 1


def test_upload_quarantines_weaponized(client, analyst_headers):
    content = (_SAMPLES / "malformed" / "weaponized.log").read_bytes()
    r = client.post("/api/ingestion/upload", headers=analyst_headers,
                    files={"file": ("weaponized.log", content, "text/plain")})
    job = _wait_job(client, analyst_headers, r.json()["id"])
    assert job["quarantined_records"] >= 3
    assert job["stats"]["security_events"] >= 3

    recs = client.get(f"/api/ingestion/jobs/{job['id']}/records?status=QUARANTINED",
                      headers=analyst_headers)
    assert recs.status_code == 200
    assert all(x["security_verdict"] in ("SUSPICIOUS", "WEAPONIZED_LOG") for x in recs.json())


def test_upload_rejects_bad_extension(client, analyst_headers):
    r = client.post("/api/ingestion/upload", headers=analyst_headers,
                    files={"file": ("evil.exe", b"MZ...", "application/octet-stream")})
    assert r.status_code == 415


def test_viewer_cannot_upload(client, admin_headers):
    client.post("/api/users", headers=admin_headers,
                json={"email": "v2@ulpf.io", "password": "ViewerPass!2", "role": "VIEWER"})
    tok = client.post("/api/auth/login",
                      json={"email": "v2@ulpf.io", "password": "ViewerPass!2"}).json()["access_token"]
    r = client.post("/api/ingestion/upload", headers={"Authorization": f"Bearer {tok}"},
                    files={"file": ("x.log", b"hello world", "text/plain")})
    assert r.status_code == 403


def test_samples_listing(client, analyst_headers):
    r = client.get("/api/ingestion/samples", headers=analyst_headers)
    assert r.status_code == 200
    paths = [s["path"] for s in r.json()["samples"]]
    assert "linux/auth.log" in paths
