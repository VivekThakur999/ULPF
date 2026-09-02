"""First-run bootstrap: create tables and seed baseline data.

Idempotent. Used for dev/demo when Alembic migrations are not run.
docker-compose runs `alembic upgrade head` then this seed step.
"""
from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.logging import get_logger
from app.models import (  # noqa: F401  (import registers all tables)
    PiiSetting,
    Role,
    SecurityRule,
    User,
)
from app.models.user import ALL_ROLES, ROLE_ADMIN

log = get_logger("bootstrap")

_DEFAULT_RULES = [
    dict(rule_key="RULE_1", name="Multiple failed logins from same source",
         description="More than N failed authentication events from one source IP within the window.",
         severity="high", threshold=5, window_seconds=120),
    dict(rule_key="RULE_2", name="Brute-force pattern",
         description="Sustained high-rate authentication failures against a host/service.",
         severity="high", threshold=10, window_seconds=300),
    dict(rule_key="RULE_3", name="Repeated auth failures across multiple hosts",
         description="Same source failing authentication against 3+ distinct hosts.",
         severity="high", threshold=3, window_seconds=600,
         params={"distinct_hosts": 3}),
    dict(rule_key="RULE_4", name="Unusual login frequency",
         description="Login attempt rate for an account far exceeds its normal baseline.",
         severity="medium", threshold=20, window_seconds=300),
    dict(rule_key="RULE_5", name="Suspicious network connection sequence",
         description="Firewall connection followed by repeated auth failures from the same source.",
         severity="medium", threshold=1, window_seconds=180),
    dict(rule_key="RULE_6", name="Failed auth burst followed by success",
         description="Several failed authentications then a successful login for the same account/source.",
         severity="critical", threshold=4, window_seconds=300),
    dict(rule_key="RULE_7", name="Suspicious log-injection payload",
         description="Security Shield flagged a raw log as SUSPICIOUS or WEAPONIZED_LOG.",
         severity="high", threshold=1, window_seconds=3600),
    dict(rule_key="RULE_8", name="Abnormal event burst",
         description="Event volume from a source spikes far above its recent rate.",
         severity="medium", threshold=100, window_seconds=60),
]


def _seed_roles(db: Session) -> None:
    for name in ALL_ROLES:
        if not db.get(Role, name):
            db.add(Role(name=name, description=f"{name} role"))
    db.commit()


def _seed_admin(db: Session) -> None:
    email = settings.first_admin_email.lower()
    if db.query(User).filter(User.email == email).first():
        return
    db.add(User(
        email=email,
        full_name="ULPF Administrator",
        password_hash=hash_password(settings.first_admin_password),
        role_name=ROLE_ADMIN,
        is_active=True,
    ))
    db.commit()
    log.info("Seeded first admin user: %s", email)


def _seed_pii(db: Session) -> None:
    row = db.get(PiiSetting, "default")
    if not row:
        db.add(PiiSetting(id="default", mode=settings.pii_default_mode))
        db.commit()


def _seed_rules(db: Session) -> None:
    for spec in _DEFAULT_RULES:
        if not db.query(SecurityRule).filter(SecurityRule.rule_key == spec["rule_key"]).first():
            db.add(SecurityRule(**spec))
    db.commit()


def bootstrap() -> None:
    # In SQLite dev mode we create tables directly; with Postgres, Alembic owns
    # the schema but create_all is still safe (only creates missing tables).
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    Base.metadata.create_all(bind=engine)
    if not existing:
        log.info("Created %d tables", len(Base.metadata.tables))

    db = SessionLocal()
    try:
        _seed_roles(db)
        _seed_admin(db)
        _seed_pii(db)
        _seed_rules(db)
    finally:
        db.close()
