from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.source import LogSource
from app.models.user import User
from app.schemas.source import SourceCreate, SourceOut, SourceUpdate
from app.services import audit
from app.services.ingestion.adapters import adapter_catalog

router = APIRouter()


@router.get("/adapters")
def list_adapters(_: User = Depends(get_current_user)):
    """Adapter capability catalog - what actually works in the MVP vs interface-only."""
    return {"adapters": adapter_catalog()}


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(LogSource).order_by(LogSource.name).all()


@router.post("", response_model=SourceOut, status_code=201)
def create_source(
    payload: SourceCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    try:
        payload.validate_enums()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if db.query(LogSource).filter(LogSource.name == payload.name).first():
        raise HTTPException(status_code=409, detail="A source with that name exists")
    src = LogSource(**payload.model_dump())
    db.add(src)
    db.commit()
    db.refresh(src)
    audit.record(db, action="source.create", actor=admin, target_type="source",
                 target_id=src.id, detail=f"adapter={src.adapter}",
                 ip_address=request.client.host if request.client else None)
    return src


@router.put("/{source_id}", response_model=SourceOut)
def update_source(
    source_id: str,
    payload: SourceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    src = db.get(LogSource, source_id)
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(src, k, v)
    db.commit()
    db.refresh(src)
    audit.record(db, action="source.update", actor=admin, target_type="source",
                 target_id=src.id, ip_address=request.client.host if request.client else None)
    return src


@router.delete("/{source_id}", status_code=204)
def delete_source(
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    src = db.get(LogSource, source_id)
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(src)
    db.commit()
    audit.record(db, action="source.delete", actor=admin, target_type="source",
                 target_id=source_id, ip_address=request.client.host if request.client else None)
