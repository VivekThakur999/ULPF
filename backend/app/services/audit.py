"""Audit logging helper (Module 1 / 37)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.user import AuditLog, User

log = get_logger("audit")


def record(
    db: Session,
    *,
    action: str,
    actor: User | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: str = "",
    ip_address: str | None = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        detail=detail[:2000],
        ip_address=ip_address,
    )
    db.add(entry)
    if commit:
        db.commit()
    log.info("audit action=%s actor=%s target=%s/%s", action,
             entry.actor_email or "system", target_type, target_id)
    return entry
