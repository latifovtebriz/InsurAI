"""Reinsurance Treaties, Cessions, and Bordereaux REST API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.platform.public import require_permission
from app.modules.reinsurance.models import (
    ReinsuranceCession,
    ReinsuranceRecovery,
    ReinsuranceTreaty,
)
from app.modules.reinsurance.service import reinsurance_service

router = APIRouter(prefix="/reinsurance", tags=["Reinsurance & Treaties"])


@router.get("/treaties", summary="List active reinsurance treaties")
def list_treaties(
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("finance:read")),
) -> list[dict[str, Any]]:
    reinsurance_service.ensure_default_treaties(db)
    treaties = db.scalars(select(ReinsuranceTreaty)).all()
    return [
        {
            "id": t.id,
            "treaty_code": t.treaty_code,
            "treaty_name": t.treaty_name,
            "treaty_type": t.treaty_type,
            "product_code": t.product_code,
            "reinsurer_name": t.reinsurer_name,
            "retention_share_pct": float(t.retention_share_pct),
            "ceded_share_pct": float(t.ceded_share_pct),
            "retention_amount": float(t.retention_amount),
            "treaty_limit": float(t.treaty_limit),
            "start_date": t.start_date.isoformat(),
            "end_date": t.end_date.isoformat(),
            "is_active": t.is_active,
        }
        for t in treaties
    ]


@router.get("/cessions", summary="List premium cessions")
def list_cessions(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("finance:read")),
) -> list[dict[str, Any]]:
    cessions = db.scalars(
        select(ReinsuranceCession).order_by(ReinsuranceCession.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": c.id,
            "treaty_code": c.treaty_code,
            "policy_number": c.policy_number,
            "gross_premium": float(c.gross_premium),
            "ceded_premium": float(c.ceded_premium),
            "net_premium": float(c.net_premium),
            "cession_date": c.cession_date.isoformat(),
            "created_at": c.created_at.isoformat(),
        }
        for c in cessions
    ]


@router.get("/recoveries", summary="List claim recoveries from treaties")
def list_recoveries(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("finance:read")),
) -> list[dict[str, Any]]:
    recoveries = db.scalars(
        select(ReinsuranceRecovery).order_by(ReinsuranceRecovery.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": r.id,
            "treaty_code": r.treaty_code,
            "claim_number": r.claim_number,
            "gross_loss": float(r.gross_loss),
            "retention_deducted": float(r.retention_deducted),
            "recovered_amount": float(r.recovered_amount),
            "net_loss": float(r.net_loss),
            "status": r.status,
            "created_at": r.created_at.isoformat(),
        }
        for r in recoveries
    ]


@router.get("/bordereaux/{treaty_code}", summary="Generate structured bordereau statement")
def get_bordereau_report(
    treaty_code: str,
    period_start: str | None = Query(None, description="Start date YYYY-MM-DD"),
    period_end: str | None = Query(None, description="End date YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("finance:read")),
) -> dict[str, Any]:
    from datetime import date

    p_start = date.fromisoformat(period_start) if period_start else None
    p_end = date.fromisoformat(period_end) if period_end else None

    try:
        report = reinsurance_service.generate_bordereau_report(
            session=db,
            treaty_code=treaty_code,
            period_start=p_start,
            period_end=p_end,
        )
        return report
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
