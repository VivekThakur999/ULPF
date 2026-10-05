"""Auth dependencies: current user resolution and RBAC guards."""
from __future__ import annotations

from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.core.config import settings
from app.core.database import get_db
from app.models.common import utcnow
from app.models.user import ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# role -> rank; higher rank implies all lower privileges
_RANK = {ROLE_VIEWER: 1, ROLE_ANALYST: 2, ROLE_ADMIN: 3}

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise _CREDENTIALS_EXC

    user_id = payload.get("sub")
    if not user_id:
        raise _CREDENTIALS_EXC

    email_claim = payload.get("email")
    email = email_claim.lower().strip() if isinstance(email_claim, str) and email_claim.strip() else None

    user = db.get(User, user_id)
    if user is None:
        user = db.query(User).filter(
            (User.supabase_user_id == user_id) |
            ((User.email == email) if email else False)
        ).first()

    # If user doesn't exist in local DB but has valid Supabase Auth payload with email -> auto-provision
    if user is None and email:
        app_meta = payload.get("app_metadata") or {}
        user_meta = payload.get("user_metadata") or {}
        raw_role = (
            app_meta.get("role")
            or user_meta.get("role")
            or payload.get("role")
            or ROLE_VIEWER
        )
        role = str(raw_role).upper()
        if role not in (ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER):
            role = ROLE_ADMIN if email == settings.first_admin_email.lower() else ROLE_VIEWER

        full_name = str(user_meta.get("full_name") or user_meta.get("name") or "")

        user = User(
            email=email,
            full_name=full_name,
            password_hash=None,
            supabase_user_id=user_id,
            role_name=role,
            is_active=True,
            last_login_at=utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user is not None:
        needs_commit = False
        if not user.supabase_user_id and (payload.get("aud") == "authenticated" or "supabase" in payload.get("iss", "")):
            user.supabase_user_id = user_id
            needs_commit = True

        app_meta = payload.get("app_metadata") or {}
        user_meta = payload.get("user_metadata") or {}
        claimed_role = app_meta.get("role") or user_meta.get("role")
        if claimed_role and str(claimed_role).upper() in (ROLE_ADMIN, ROLE_ANALYST, ROLE_VIEWER):
            norm_role = str(claimed_role).upper()
            if user.role_name != norm_role:
                user.role_name = norm_role
                needs_commit = True

        if needs_commit:
            db.commit()
            db.refresh(user)

    if user is None or not user.is_active:
        raise HTTPException(status_code=403, detail="User inactive or not found")
    return user


def require_roles(*roles: str):
    """Dependency factory. Passing a single role means "this role or higher"."""
    allowed: Iterable[str]
    if len(roles) == 1:
        min_rank = _RANK[roles[0]]
        allowed = {r for r, rank in _RANK.items() if rank >= min_rank}
    else:
        allowed = set(roles)

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role_name not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role in {sorted(allowed)}; you are {user.role_name}",
            )
        return user

    return _guard


require_admin = require_roles(ROLE_ADMIN)
require_analyst = require_roles(ROLE_ANALYST)  # analyst or admin
require_viewer = require_roles(ROLE_VIEWER)    # any authenticated user
