"""System operational metrics and AI evaluation reporting endpoints."""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.claims.public import Claim
from app.modules.platform.public import require_permission
from app.modules.policy.public import Policy

router = APIRouter(prefix="/metrics", tags=["Metrics & Evals"])


class OperationalMetricsResponse(BaseModel):
    total_policies: int
    active_policies: int
    total_claims: int
    claims_by_status: dict[str, int]
    auto_approval_count: int
    auto_approval_rate_percent: float
    total_reserve_azn: float
    total_paid_out_azn: float


class EvalSummaryResponse(BaseModel):
    extraction_eval: dict[str, Any] | None = None
    retrieval_eval: dict[str, Any] | None = None
    claims_triage_dev_eval: dict[str, Any] | None = None
    claims_triage_test_eval: dict[str, Any] | None = None


@router.get("", response_model=OperationalMetricsResponse)
def get_operational_metrics(
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("metrics:read")),
) -> OperationalMetricsResponse:
    """Retrieves operational core metrics: claims counts, STP rate, and reserves."""
    # Policy counts
    total_policies = db.scalar(select(func.count(Policy.id))) or 0
    active_policies = db.scalar(select(func.count(Policy.id)).where(Policy.status == "active")) or 0

    # Claims counts
    total_claims = db.scalar(select(func.count(Claim.id))) or 0
    claims_by_status: dict[str, int] = {}
    rows = db.execute(select(Claim.status, func.count(Claim.id)).group_by(Claim.status)).all()
    for st, count in rows:
        claims_by_status[st] = count

    # L3 auto-approval rate
    auto_approvals = db.scalar(select(func.count(Claim.id)).where(Claim.autonomy_level == "L3")) or 0
    stp_rate = round((auto_approvals / total_claims * 100.0), 2) if total_claims > 0 else 0.0

    # Reserves & payouts
    total_reserves = db.scalar(select(func.sum(Claim.estimated_reserve))) or 0.0
    total_paid = db.scalar(select(func.sum(Claim.approved_payout)).where(Claim.status == "settled")) or 0.0

    return OperationalMetricsResponse(
        total_policies=total_policies,
        active_policies=active_policies,
        total_claims=total_claims,
        claims_by_status=claims_by_status,
        auto_approval_count=auto_approvals,
        auto_approval_rate_percent=stp_rate,
        total_reserve_azn=float(total_reserves),
        total_paid_out_azn=float(total_paid),
    )


@router.get("/evals/latest", response_model=EvalSummaryResponse)
def get_latest_eval_reports(
    _user: dict[str, Any] = Depends(require_permission("metrics:read")),
) -> EvalSummaryResponse:
    """Returns the latest evaluation benchmark results and safety metrics."""
    reports_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "evals" / "reports"

    def _load_json(file_name: str) -> dict[str, Any] | None:
        p = reports_dir / file_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
                return None
            except Exception:
                return None
        return None

    return EvalSummaryResponse(
        extraction_eval=_load_json("extraction_dev.json"),
        retrieval_eval=_load_json("retrieval_40_report.json"),
        claims_triage_dev_eval=_load_json("claims_a4_dev.json"),
        claims_triage_test_eval=_load_json("claims_a4_test.json"),
    )
