from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.models.privacy import PII_MODES


class PiiSettingsOut(BaseModel):
    mode: str
    protect_ip: bool
    protect_email: bool
    protect_username: bool
    protect_host: bool
    scope: str
    token_length: int
    store_reverse_map: bool

    class Config:
        from_attributes = True


class PiiSettingsUpdate(BaseModel):
    mode: Optional[str] = None
    protect_ip: Optional[bool] = None
    protect_email: Optional[bool] = None
    protect_username: Optional[bool] = None
    protect_host: Optional[bool] = None
    scope: Optional[str] = Field(default=None, max_length=64)
    token_length: Optional[int] = Field(default=None, ge=4, le=16)

    def validate_mode(self) -> None:
        if self.mode is not None and self.mode not in PII_MODES:
            raise ValueError(f"mode must be one of {PII_MODES}")


class PiiPreviewRequest(BaseModel):
    value: str = Field(min_length=1, max_length=256)
    kind: str = Field(default="ip")  # ip | email | username | host


class PiiPreviewResponse(BaseModel):
    input: str
    kind: str
    mode: str
    output: str
    note: str
