from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.ai import AIStatusResponse, ExplainRequest, ExplainResponse
from app.services import audit
from app.services.ai.base import ProviderUnavailable
from app.services.ai.service import (
    build_alert_context,
    build_event_context,
    build_raw_context,
    explain,
    provider_status,
)

router = APIRouter()


@router.get("/status", response_model=AIStatusResponse)
def ai_status(_: User = Depends(get_current_user)):
    return provider_status()


@router.post("/explain", response_model=ExplainResponse)
def ai_explain(
    payload: ExplainRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if settings.ai_provider == "disabled":
        raise HTTPException(status_code=503, detail="AI explanations are disabled on this deployment")

    if payload.kind == "event":
        ctx = build_event_context(db, payload.event_id)  # type: ignore[arg-type]
        if ctx is None:
            raise HTTPException(status_code=404, detail="Event not found")
    elif payload.kind == "alert":
        ctx = build_alert_context(db, payload.alert_id)  # type: ignore[arg-type]
        if ctx is None:
            raise HTTPException(status_code=404, detail="Alert not found")
    else:
        text = payload.text or ""
        if len(text) > settings.ai_max_raw_input_chars:
            raise HTTPException(
                status_code=422,
                detail=f"raw text exceeds {settings.ai_max_raw_input_chars} characters",
            )
        ctx = build_raw_context(db, text)

    try:
        result = explain(ctx)
    except ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    audit.record(db, action="ai.explain", actor=user,
                 detail=f"kind={payload.kind} provider={result.provider}",
                 ip_address=request.client.host if request.client else None)

    return ExplainResponse(
        kind=ctx.kind,
        generated_at=datetime.now(timezone.utc).isoformat(),
        provider=result.provider,
        offline=result.offline,
        model=result.model,
        evidence=ctx.evidence,
        explanation=result.to_dict(),
    )
