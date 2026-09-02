"""Shared pytest fixtures. Uses an isolated SQLite database per test session."""
from __future__ import annotations

import os
import tempfile

import pytest

# Configure an isolated DB BEFORE importing the app.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["PII_HMAC_KEY"] = "test-pii-key"
os.environ["FIRST_ADMIN_EMAIL"] = "admin@ulpf.io"
os.environ["FIRST_ADMIN_PASSWORD"] = "AdminPass!123"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.bootstrap import bootstrap  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    bootstrap()
    yield
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client) -> str:
    r = client.post("/api/auth/login", json={"email": "admin@ulpf.io", "password": "AdminPass!123"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def analyst_headers(client, admin_headers) -> dict:
    client.post(
        "/api/users",
        headers=admin_headers,
        json={"email": "analyst@ulpf.io", "full_name": "An Analyst",
              "password": "AnalystPass!1", "role": "ANALYST"},
    )
    r = client.post("/api/auth/login",
                    json={"email": "analyst@ulpf.io", "password": "AnalystPass!1"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
