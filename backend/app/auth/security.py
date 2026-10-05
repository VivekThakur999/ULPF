"""Password hashing and JWT helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# --- Passwords (bcrypt directly; no passlib to avoid version drift) ---


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT ---


def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    # 1. Try decoding with local secret key (Mode B / Local Auth)
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as err:
        # 2. If Supabase JWT secret is configured (Mode A / Connected Auth), try verifying Supabase JWT
        if settings.supabase_jwt_secret:
            try:
                return jwt.decode(
                    token,
                    settings.supabase_jwt_secret,
                    algorithms=["HS256"],
                    options={"verify_aud": False},
                )
            except jwt.PyJWTError:
                pass
        raise err
