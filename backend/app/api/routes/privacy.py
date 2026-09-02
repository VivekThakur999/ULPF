from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.privacy import PiiSetting
from app.models.user import User
from app.schemas.privacy import (
    PiiPreviewRequest,
    PiiPreviewResponse,
    PiiSettingsOut,
    PiiSettingsUpdate,
)
from app.services import audit
from app.services.privacy.pii import mask, pseudonymize

router = APIRouter()


def _get_or_create(db: Session) -> PiiSetting:
    row = db.get(PiiSetting, "default")
    if not row:
        row = PiiSetting(id="default")
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/settings", response_model=PiiSettingsOut)
def get_settings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return _get_or_create(db)


@router.put("/settings", response_model=PiiSettingsOut)
def update_settings(
    payload: PiiSettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        payload.validate_mode()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    row = _get_or_create(db)
    before = {c: getattr(row, c) for c in
              ("mode", "protect_ip", "protect_email", "protect_username", "protect_host",
               "scope", "token_length")}
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    row.updated_by = admin.id
    db.commit()
    db.refresh(row)
    after = {c: getattr(row, c) for c in before}
    audit.record(db, action="privacy.settings_update", actor=admin,
                 target_type="pii_settings", target_id="default",
                 detail=f"{before} -> {after}",
                 ip_address=request.client.host if request.client else None)
    return row


@router.post("/preview", response_model=PiiPreviewResponse)
def preview(
    payload: PiiPreviewRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = _get_or_create(db)
    kind = payload.kind if payload.kind in ("ip", "email", "username", "host") else "ip"
    if row.mode == "OFF":
        out, note = payload.value, "PII protection is OFF - value passes through unchanged"
    elif row.mode == "MASK":
        out, note = mask(payload.value, kind), "partial masking (not reversible, not correlatable)"
    else:
        out = pseudonymize(payload.value, kind, scope=row.scope, token_length=row.token_length)
        note = (f"deterministic HMAC pseudonym in scope '{row.scope}'. "
                "Same input always yields this token, enabling correlation without "
                "exposing the raw identifier.")
    return PiiPreviewResponse(input=payload.value, kind=kind, mode=row.mode, output=out, note=note)
