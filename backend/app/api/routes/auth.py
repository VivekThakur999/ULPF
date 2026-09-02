from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.auth.security import create_access_token, verify_password
from app.core.config import settings
from app.core.database import get_db
from app.models.common import utcnow
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services import audit

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        # Same message either way - do not leak which part failed.
        audit.record(db, action="auth.login_failed", detail=f"email={payload.email}",
                     ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")

    user.last_login_at = utcnow()
    token = create_access_token(subject=user.id, role=user.role_name)
    audit.record(db, action="auth.login", actor=user,
                 ip_address=request.client.host if request.client else None)
    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.from_user(user),
    )


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Stateless JWT: logout is client-side token disposal. We audit it.
    audit.record(db, action="auth.logout", actor=user,
                 ip_address=request.client.host if request.client else None)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.from_user(user)
