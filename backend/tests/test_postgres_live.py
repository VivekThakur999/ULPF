"""Live PostgreSQL & Supabase Control Plane Integration Tests.

Validates schema, migrations, tables, RBAC, and Supabase Auth flow against live PostgreSQL.
"""
from pathlib import Path
import time
import pytest
import jwt
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models.user import Role, User, AuditLog, ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER
from app.models.source import LogSource
from app.models.privacy import PiiSetting
from app.models.security import SecurityRule
from app.models.parser import ParserPack, ParserVersion
from app.auth.security import create_access_token, decode_token
from app.auth.deps import get_current_user, require_admin, require_analyst, require_viewer


POSTGRES_TEST_URL = "postgresql+psycopg2://ulpf:ulpf@127.0.0.1:5433/ulpf"


@pytest.fixture(scope="module")
def pg_session():
    """Create live PostgreSQL session."""
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        # Seed baseline roles
        for r in (ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER):
            if not db.get(Role, r):
                db.add(Role(name=r, description=f"{r} role"))
        db.commit()
        yield db
    finally:
        db.close()
        engine.dispose()


def test_postgres_control_plane_all_tables_exist(pg_session):
    """Verify all 8 control plane tables exist in live PostgreSQL."""
    engine = pg_session.get_bind()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
        "roles",
        "app_users",
        "audit_logs",
        "log_sources",
        "pii_settings",
        "security_rules",
        "parser_packs",
        "parser_versions",
    }

    missing = expected_tables - table_names
    assert not missing, f"Missing control plane tables in Postgres: {missing}"


def test_postgres_supabase_user_mapping(pg_session):
    """Verify app_users model supports supabase_user_id and nullable password_hash."""
    supabase_uid = f"sb_user_{int(time.time())}"
    email = f"analyst_{int(time.time())}@ulpf.io"

    user = User(
        email=email,
        full_name="Postgres Live Analyst",
        supabase_user_id=supabase_uid,
        password_hash=None,  # Supabase Auth users don't have local passwords
        role_name=ROLE_ANALYST,
        is_active=True,
    )
    pg_session.add(user)
    pg_session.commit()
    pg_session.refresh(user)

    assert user.id
    assert user.supabase_user_id == supabase_uid
    assert user.password_hash is None
    assert user.role_name == ROLE_ANALYST

    # Query back
    fetched = pg_session.query(User).filter(User.supabase_user_id == supabase_uid).first()
    assert fetched is not None
    assert fetched.email == email

    # Cleanup
    pg_session.delete(fetched)
    pg_session.commit()


def test_postgres_supabase_auth_rbac_resolution(pg_session, monkeypatch):
    """Verify Supabase JWT decoding and role enforcement on live PostgreSQL."""
    supabase_secret = "test-live-postgres-supabase-secret-12345"
    monkeypatch.setattr(settings, "supabase_jwt_secret", supabase_secret)

    now = int(time.time())
    sub_id = f"sb_adm_{now}"
    email = f"admin_{now}@ulpf.io"

    # Create admin user
    adm = User(
        email=email,
        full_name="Postgres Admin",
        supabase_user_id=sub_id,
        role_name=ROLE_ADMIN,
        is_active=True,
    )
    pg_session.add(adm)
    pg_session.commit()

    token = jwt.encode(
        {
            "sub": sub_id,
            "aud": "authenticated",
            "email": email,
            "app_metadata": {"role": "ADMIN"},
            "exp": now + 3600,
        },
        supabase_secret,
        algorithm="HS256",
    )

    # Validate get_current_user resolves the correct DB record
    resolved_user = get_current_user(token=token, db=pg_session)
    assert resolved_user.id == adm.id
    assert resolved_user.role_name == ROLE_ADMIN

    # Test RBAC guards
    admin_guard = require_admin(resolved_user)
    assert admin_guard.id == adm.id

    analyst_guard = require_analyst(resolved_user)
    assert analyst_guard.id == adm.id

    viewer_guard = require_viewer(resolved_user)
    assert viewer_guard.id == adm.id

    # Cleanup
    pg_session.delete(adm)
    pg_session.commit()


def test_no_supabase_service_role_key_leaked_in_frontend():
    """Verify frontend code never references or bundles the Supabase service-role secret."""
    frontend_dir = Path(__file__).resolve().parents[2] / "frontend" / "src"
    assert frontend_dir.is_dir()

    forbidden_patterns = ["SUPABASE_SERVICE_ROLE_KEY", "service_role", "serviceRole"]

    for file_path in frontend_dir.rglob("*"):
        if file_path.suffix in (".ts", ".tsx", ".js", ".jsx", ".html", ".json"):
            content = file_path.read_text(encoding="utf-8")
            for pat in forbidden_patterns:
                assert pat not in content, f"Forbidden secret identifier '{pat}' found in frontend file: {file_path}"
