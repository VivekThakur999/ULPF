"""Auth dependencies: current user resolution and RBAC guards."""
from __future__ import annotations

from typing import Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.core.database import get_db
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
    user = db.get(User, user_id)
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
