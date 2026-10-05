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


def test_supabase_auth_jwt_verification_and_provisioning(client, monkeypatch):
    import time
    import jwt
    from app.core.config import settings

    supabase_secret = "test-supabase-jwt-secret-key-123456789"
    monkeypatch.setattr(settings, "supabase_jwt_secret", supabase_secret)

    now = int(time.time())
    supabase_sub = "d485f20a-8d76-47b1-9eb0-123456789abc"
    payload = {
        "sub": supabase_sub,
        "aud": "authenticated",
        "email": "supabase_analyst@ulpf.io",
        "exp": now + 3600,
        "iat": now,
        "iss": "https://test-project.supabase.co/auth/v1",
        "app_metadata": {"provider": "email", "role": "ANALYST"},
        "user_metadata": {"full_name": "Supabase Analyst", "role": "ANALYST"},
        "role": "authenticated",
    }
    sb_token = jwt.encode(payload, supabase_secret, algorithm="HS256")
    sb_headers = {"Authorization": f"Bearer {sb_token}"}

    # /api/auth/me should auto-provision and return the user profile with ANALYST role
    me = client.get("/api/auth/me", headers=sb_headers)
    assert me.status_code == 200
    data = me.json()
    assert data["email"] == "supabase_analyst@ulpf.io"
    assert data["role"] == "ANALYST"
    assert data["full_name"] == "Supabase Analyst"

    # Analyst can access analyst routes (/api/alerts)
    alerts = client.get("/api/alerts", headers=sb_headers)
    assert alerts.status_code == 200

    # Analyst cannot access admin-only routes (/api/users)
    users_resp = client.get("/api/users", headers=sb_headers)
    assert users_resp.status_code == 403


def test_supabase_auth_admin_jwt(client, monkeypatch):
    import time
    import jwt
    from app.core.config import settings

    supabase_secret = "test-supabase-jwt-secret-key-123456789"
    monkeypatch.setattr(settings, "supabase_jwt_secret", supabase_secret)

    now = int(time.time())
    supabase_sub = "a1111111-2222-3333-4444-555555555555"
    payload = {
        "sub": supabase_sub,
        "aud": "authenticated",
        "email": "supabase_admin@ulpf.io",
        "exp": now + 3600,
        "iat": now,
        "app_metadata": {"role": "ADMIN"},
        "user_metadata": {"full_name": "Supabase Admin"},
    }
    sb_token = jwt.encode(payload, supabase_secret, algorithm="HS256")
    sb_headers = {"Authorization": f"Bearer {sb_token}"}

    me = client.get("/api/auth/me", headers=sb_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "ADMIN"

    # Admin CAN access /api/users
    users_resp = client.get("/api/users", headers=sb_headers)
    assert users_resp.status_code == 200

