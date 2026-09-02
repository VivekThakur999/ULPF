from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_admin
from app.auth.security import hash_password
from app.core.database import get_db
from app.models.user import AuditLog, User
from app.schemas.auth import UserOut
from app.schemas.user import UserCreate, UserUpdate
from app.services import audit

router = APIRouter()


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return [UserOut.from_user(u) for u in db.query(User).order_by(User.email).all()]


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        role = payload.validated_role()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role_name=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit.record(db, action="user.create", actor=admin, target_type="user", target_id=user.id,
                 detail=f"role={role}", ip_address=request.client.host if request.client else None)
    return UserOut.from_user(user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.role is not None:
        from app.models.user import ALL_ROLES

        if payload.role not in ALL_ROLES:
            raise HTTPException(status_code=422, detail=f"role must be one of {ALL_ROLES}")
        user.role_name = payload.role
    if payload.is_active is not None:
        if user.id == admin.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="You cannot disable your own account")
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    audit.record(db, action="user.update", actor=admin, target_type="user", target_id=user.id,
                 ip_address=request.client.host if request.client else None)
    return UserOut.from_user(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    db.delete(user)
    db.commit()
    audit.record(db, action="user.delete", actor=admin, target_type="user", target_id=user_id,
                 ip_address=request.client.host if request.client else None)


@router.get("/audit-logs")
def list_audit_logs(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    action: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    total = q.count()
    rows = q.order_by(desc(AuditLog.ts)).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "ts": r.ts,
                "actor_email": r.actor_email,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "detail": r.detail,
                "ip_address": r.ip_address,
            }
            for r in rows
        ],
    }
