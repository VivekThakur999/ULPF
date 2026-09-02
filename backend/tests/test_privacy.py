from app.services.privacy.pii import apply_pii, mask, pseudonymize
from app.services.pipeline.service import run_record


def test_pseudonym_is_deterministic_and_prefixed():
    a = pseudonymize("192.168.1.50", "ip")
    b = pseudonymize("192.168.1.50", "ip")
    assert a == b
    assert a.startswith("IP_")
    assert pseudonymize("admin", "username").startswith("USER_")
    assert pseudonymize("a@b.com", "email").startswith("EMAIL_")


def test_pseudonym_scope_isolation():
    assert pseudonymize("192.168.1.50", "ip", scope="tenant-a") != pseudonymize(
        "192.168.1.50", "ip", scope="tenant-b"
    )


def test_mask_mode():
    assert mask("192.168.1.50", "ip") == "192.168.x.x"
    assert mask("admin@corp.example", "email") == "a***@corp.example"
    assert mask("administrator", "username") == "a***"


def test_apply_pii_off_is_noop():
    out, transforms, mode = apply_pii({"source_ip": "1.2.3.4"}, mode_override="OFF")
    assert out == {"source_ip": "1.2.3.4"}
    assert transforms == []
    assert mode == "OFF"


def test_apply_pii_does_not_record_original_value():
    _, transforms, _ = apply_pii({"source_ip": "192.168.1.50"}, mode_override="DETERMINISTIC_HASH")
    for t in transforms:
        assert "192.168.1.50" not in str(t)
        assert "original" not in t


def test_apply_pii_alias_aware():
    # windows-style field name still gets protected
    out, transforms, _ = apply_pii(
        {"targetusername": "Administrator", "ipaddress": "192.168.1.50"},
        mode_override="DETERMINISTIC_HASH",
    )
    assert out["targetusername"].startswith("USER_")
    assert out["ipaddress"].startswith("IP_")


def test_pii_end_to_end_modes():
    off = run_record("Failed password for admin from 192.168.1.50 port 22 ssh2 host db-02",
                     pii_mode="OFF").event
    assert off.source_ip == "192.168.1.50"

    det = run_record("Sep  2 09:02:15 db-02 sshd[1]: Failed password for admin from 192.168.1.50 port 22 ssh2",
                     pii_mode="DETERMINISTIC_HASH").event
    assert det.source_ip.startswith("IP_")
    assert det.pii_protected is True
    assert det.pii_mode == "DETERMINISTIC_HASH"


# --- API ---

def test_privacy_settings_get_and_analyst_cannot_update(client, analyst_headers, admin_headers):
    r = client.get("/api/privacy/settings", headers=analyst_headers)
    assert r.status_code == 200
    assert r.json()["mode"] in ("OFF", "MASK", "DETERMINISTIC_HASH")

    bad = client.put("/api/privacy/settings", headers=analyst_headers, json={"mode": "OFF"})
    assert bad.status_code == 403


def test_privacy_settings_admin_update_and_audit(client, admin_headers):
    r = client.put("/api/privacy/settings", headers=admin_headers,
                   json={"mode": "MASK", "protect_host": True, "token_length": 8})
    assert r.status_code == 200
    assert r.json()["mode"] == "MASK"
    assert r.json()["token_length"] == 8

    logs = client.get("/api/users/audit-logs?action=privacy.settings_update", headers=admin_headers)
    assert logs.json()["total"] >= 1

    # restore
    client.put("/api/privacy/settings", headers=admin_headers, json={"mode": "DETERMINISTIC_HASH"})


def test_privacy_preview(client, admin_headers):
    client.put("/api/privacy/settings", headers=admin_headers, json={"mode": "DETERMINISTIC_HASH"})
    r = client.post("/api/privacy/preview", headers=admin_headers,
                    json={"value": "192.168.1.50", "kind": "ip"})
    assert r.status_code == 200
    assert r.json()["output"].startswith("IP_")
    assert "192.168.1.50" == r.json()["input"]


def test_invalid_mode_rejected(client, admin_headers):
    r = client.put("/api/privacy/settings", headers=admin_headers, json={"mode": "BOGUS"})
    assert r.status_code == 422
