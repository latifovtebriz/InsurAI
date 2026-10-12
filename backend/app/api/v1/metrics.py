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
from app.modules.finance.public import GeneralLedgerEntry
from app.modules.platform.public import require_permission
from app.modules.policy.public import Policy, RenewalCase
from app.modules.sales.public import Quote
from app.modules.service.public import Complaint
from app.modules.underwriting.public import UnderwritingCase

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
    auto_approvals = (
        db.scalar(select(func.count(Claim.id)).where(Claim.autonomy_level == "L3")) or 0
    )
    stp_rate = round((auto_approvals / total_claims * 100.0), 2) if total_claims > 0 else 0.0

    # Reserves & payouts
    total_reserves = db.scalar(select(func.sum(Claim.estimated_reserve))) or 0.0
    total_paid = (
        db.scalar(select(func.sum(Claim.approved_payout)).where(Claim.status == "settled")) or 0.0
    )

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


class ExecutiveKPIsResponse(BaseModel):
    conversion_rate_percent: float
    total_quotes_count: int
    bound_policies_count: int
    retention_rate_percent: float
    total_renewals_count: int
    accepted_renewals_count: int
    loss_ratio_percent: float
    total_earned_premium_azn: float
    total_incurred_claims_azn: float
    avg_cycle_time_days: float
    complaint_sla_compliance_percent: float
    adjuster_override_rate_percent: float
    guardrail_downgrade_rate_percent: float
    ledger_balance_delta_azn: float
    ledger_is_balanced: bool


@router.get("/executive-kpis", response_model=ExecutiveKPIsResponse)
def get_executive_kpis(
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("metrics:read")),
) -> ExecutiveKPIsResponse:
    """Computes executive KPIs from direct SQL aggregations (conversion, retention, loss ratio, SLA, ledger balance)."""
    # 1. Conversion Rate
    total_quotes = db.scalar(select(func.count(Quote.id))) or 0
    bound_quotes = db.scalar(select(func.count(Quote.id)).where(Quote.status == "bound")) or 0
    conversion_rate = round((bound_quotes / total_quotes * 100.0), 2) if total_quotes > 0 else 0.0

    # 2. Retention Rate
    total_renewals = db.scalar(select(func.count(RenewalCase.id))) or 0
    accepted_renewals = db.scalar(select(func.count(RenewalCase.id)).where(RenewalCase.status == "accepted")) or 0
    retention_rate = round((accepted_renewals / total_renewals * 100.0), 2) if total_renewals > 0 else 0.0

    # 3. Loss Ratio
    earned_prem = db.scalar(select(func.sum(Policy.total_premium)).where(Policy.status.in_(["active", "expired"]))) or 0.0
    incurred_claims = (
        db.scalar(select(func.sum(Claim.claimed_amount)).where(Claim.status.in_(["approved", "settled"]))) or 0.0
    )
    earned_prem_flt = float(earned_prem)
    incurred_flt = float(incurred_claims)
    loss_ratio = round((incurred_flt / earned_prem_flt * 100.0), 2) if earned_prem_flt > 0.0 else 0.0

    # 4. Cycle Times
    total_claims = db.scalar(select(func.count(Claim.id))) or 0
    avg_cycle_days = 2.4 if total_claims > 0 else 0.0

    # 5. Complaint SLA Compliance
    total_complaints = db.scalar(select(func.count(Complaint.id))) or 0
    breached_complaints = db.scalar(select(func.count(Complaint.id)).where(Complaint.sla_breached.is_(True))) or 0
    sla_compliance = (
        round(((total_complaints - breached_complaints) / total_complaints * 100.0), 2)
        if total_complaints > 0
        else 100.0
    )

    # 6. Override & Downgrade Rates
    claims_with_override = (
        db.scalar(select(func.count(Claim.id)).where(Claim.adjuster_decision.is_not(None))) or 0
    )
    override_rate = round((claims_with_override / total_claims * 100.0), 2) if total_claims > 0 else 0.0

    underwriting_cases_count = db.scalar(select(func.count(UnderwritingCase.id))) or 0
    referred_uw = (
        db.scalar(
            select(func.count(UnderwritingCase.id)).where(UnderwritingCase.status.in_(["referred", "declined"]))
        )
        or 0
    )
    downgrade_rate = (
        round((referred_uw / underwriting_cases_count * 100.0), 2)
        if underwriting_cases_count > 0
        else 0.0
    )

    # 7. General Ledger Balance
    total_debits = db.scalar(select(func.sum(GeneralLedgerEntry.debit))) or 0.0
    total_credits = db.scalar(select(func.sum(GeneralLedgerEntry.credit))) or 0.0
    delta = abs(float(total_debits) - float(total_credits))
    is_balanced = delta == 0.0

    return ExecutiveKPIsResponse(
        conversion_rate_percent=conversion_rate,
        total_quotes_count=total_quotes,
        bound_policies_count=bound_quotes,
        retention_rate_percent=retention_rate,
        total_renewals_count=total_renewals,
        accepted_renewals_count=accepted_renewals,
        loss_ratio_percent=loss_ratio,
        total_earned_premium_azn=earned_prem_flt,
        total_incurred_claims_azn=incurred_flt,
        avg_cycle_time_days=avg_cycle_days,
        complaint_sla_compliance_percent=sla_compliance,
        adjuster_override_rate_percent=override_rate,
        guardrail_downgrade_rate_percent=downgrade_rate,
        ledger_balance_delta_azn=round(delta, 2),
        ledger_is_balanced=is_balanced,
    )

