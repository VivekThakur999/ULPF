from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_analyst
from app.core.database import get_db
from app.models.ingestion import RawLog
from app.models.template import Template, TemplateMatch
from app.models.user import User
from app.schemas.templates import (
    MineRequest,
    MineResponse,
    TemplateDetailOut,
    TemplateExampleOut,
    TemplateListOut,
    TemplateOut,
)
from app.services import audit
from app.services.templates.service import mine_templates

router = APIRouter()


@router.post("/mine", response_model=MineResponse)
def mine(
    payload: MineRequest,
    request: Request,
    db: Session = Depends(get_db),
    analyst: User = Depends(require_analyst),
):
    summary = mine_templates(
        db, source=payload.source, time_from=payload.time_from,
        time_to=payload.time_to, limit=payload.limit or 20_000,
    )
    audit.record(db, action="templates.mine", actor=analyst,
                 detail=f"scanned={summary.records_scanned} templates={summary.templates_total}",
                 ip_address=request.client.host if request.client else None)
    return MineResponse(**summary.to_dict())


@router.get("", response_model=TemplateListOut)
def list_templates(
    source: str | None = None,
    min_frequency: int = Query(default=1, ge=1),
    time_from: datetime | None = None,
    time_to: datetime | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = select(Template).where(Template.occurrences >= min_frequency)
    if time_from:
        stmt = stmt.where(Template.last_seen >= time_from)
    if time_to:
        stmt = stmt.where(Template.first_seen <= time_to)

    rows = db.execute(stmt.order_by(desc(Template.occurrences))).scalars().all()
    # source_distribution is a JSON map; filtering in Python keeps this
    # portable across SQLite and PostgreSQL without dialect-specific JSON ops.
    if source:
        rows = [r for r in rows if source in (r.source_distribution or {})]

    total = len(rows)
    covered_events = sum(r.occurrences for r in rows)
    sources: set[str] = set()
    for r in rows:
        sources.update((r.source_distribution or {}).keys())
    avg_vars = round(sum(r.variable_count for r in rows) / total, 2) if total else 0.0

    page = rows[offset: offset + limit]
    return TemplateListOut(
        total=total,
        items=[TemplateOut.model_validate(r) for r in page],
        covered_events=covered_events,
        unique_sources=len(sources),
        avg_variables=avg_vars,
    )


@router.get("/{template_id}", response_model=TemplateDetailOut)
def get_template(template_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    row = db.get(Template, template_id) or _by_key(db, template_id)
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateDetailOut.model_validate(row)


@router.get("/{template_id}/examples", response_model=list[TemplateExampleOut])
def template_examples(
    template_id: str,
    limit: int = Query(default=20, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.get(Template, template_id) or _by_key(db, template_id)
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    matches = db.execute(
        select(TemplateMatch)
        .where(TemplateMatch.template_id == row.id)
        .order_by(TemplateMatch.ts.desc())
        .offset(offset).limit(limit)
    ).scalars().all()
    raw_ids = [m.raw_log_id for m in matches]
    raws = {r.id: r for r in db.execute(select(RawLog).where(RawLog.id.in_(raw_ids))).scalars().all()}

    out = []
    for m in matches:
        raw = raws.get(m.raw_log_id)
        out.append(TemplateExampleOut(
            raw_log_id=m.raw_log_id, source=m.source,
            ts=m.ts.isoformat() if m.ts else None,
            raw=raw.content if raw else "",
            variables=m.variables,
        ))
    return out


def _by_key(db: Session, key: str) -> Template | None:
    return db.execute(select(Template).where(Template.template_key == key)).scalars().first()
