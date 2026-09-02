def test_login_success_and_me(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@ulpf.io", "password": "AdminPass!123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert r.json()["user"]["role"] == "ADMIN"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@ulpf.io"


def test_login_wrong_password(client):
    r = client.post("/api/auth/login",
                    json={"email": "admin@ulpf.io", "password": "nope"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_rbac_analyst_cannot_list_users(client, analyst_headers):
    r = client.get("/api/users", headers=analyst_headers)
    assert r.status_code == 403


def test_rbac_admin_can_list_users(client, admin_headers):
    r = client.get("/api/users", headers=admin_headers)
    assert r.status_code == 200
    assert any(u["role"] == "ADMIN" for u in r.json())


def test_admin_creates_user_and_audit_recorded(client, admin_headers):
    r = client.post("/api/users", headers=admin_headers,
                    json={"email": "viewer1@ulpf.io", "password": "ViewerPass!1",
                          "role": "VIEWER", "full_name": "V One"})
    assert r.status_code == 201

    logs = client.get("/api/users/audit-logs?action=user.create", headers=admin_headers)
    assert logs.status_code == 200
    assert logs.json()["total"] >= 1
