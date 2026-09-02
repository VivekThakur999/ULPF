from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.models.user import ALL_ROLES


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(default="", max_length=255)
    password: str = Field(min_length=8, max_length=256)
    role: str = Field(default="VIEWER")

    def validated_role(self) -> str:
        if self.role not in ALL_ROLES:
            raise ValueError(f"role must be one of {ALL_ROLES}")
        return self.role


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=256)
    role: str | None = None
    is_active: bool | None = None


class AuditLogOut(BaseModel):
    id: str
    ts: object
    actor_email: str | None
    action: str
    target_type: str | None
    target_id: str | None
    detail: str
    ip_address: str | None

    class Config:
        from_attributes = True
