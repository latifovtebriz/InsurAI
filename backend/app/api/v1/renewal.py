"""Renewal Review and Agent A7 Renewal Advisor REST API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.platform.public import require_permission
from app.modules.policy.models import RenewalCase
from app.modules.policy.public import renewal_advisor_agent, renewal_service

router = APIRouter(prefix="/renewals", tags=["Policy Renewals & A7 Advisor"])


class ScanRequest(BaseModel):
    days_ahead: int = Field(default=60, description="Scanning window ahead in days")
    as_of_date: str | None = Field(default=None, description="ISO date YYYY-MM-DD")


class AssessRequest(BaseModel):
    message: str = Field(default="", description="Optional applicant message or context")
    as_of_date: str | None = Field(default=None, description="Optional ISO evaluation date YYYY-MM-DD")


class NonRenewalRequest(BaseModel):
    rationale: str = Field(description="Mandatory underwriting rationale for non-renewal")
    underwriter_name: str = Field(default="Senior Underwriter", description="Sign-off officer name")


@router.get("/cases", summary="List expiring policy renewal cases")
def list_renewal_cases(
    status_filter: str | None = Query(None, description="Filter by status"),
    breached_only: bool = Query(False, description="Filter statutory deadline breaches"),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("policy:read")),
) -> list[dict[str, Any]]:
    stmt = select(RenewalCase)
    if status_filter:
        stmt = stmt.where(RenewalCase.status == status_filter)
    if breached_only:
        stmt = stmt.where(RenewalCase.statutory_deadline_breached == True)  # noqa: E712
    stmt = stmt.order_by(RenewalCase.days_to_expiry)

    cases = db.scalars(stmt).all()
    return [
        {
            "id": c.id,
            "policy_id": c.policy_id,
            "policy_number": c.policy_number,
            "party_id": c.party_id,
            "product_code": c.product_code,
            "current_end_date": c.current_end_date.isoformat(),
            "days_to_expiry": c.days_to_expiry,
            "claims_count": c.claims_count,
            "total_claims_incurred": float(c.total_claims_incurred),
            "current_premium": float(c.current_premium),
            "proposed_premium": float(c.proposed_premium),
            "recommendation": c.recommendation,
            "status": c.status,
            "notice_deadline": c.notice_deadline.isoformat(),
            "notice_sent": c.notice_sent,
            "statutory_deadline_breached": c.statutory_deadline_breached,
            "advisor_rationale": c.advisor_rationale,
            "underwriter_approved": c.underwriter_approved,
            "approved_by": c.approved_by,
        }
        for c in cases
    ]


@router.post("/scan", summary="Run automated T-60 expiring policy scanner job")
def run_renewal_scan(
    req: ScanRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("policy:write")),
) -> dict[str, Any]:
    from datetime import date

    as_of = date.fromisoformat(req.as_of_date) if req.as_of_date else None
    cases = renewal_service.scan_expiring_policies(db, as_of_date=as_of, days_ahead=req.days_ahead)
    db.commit()
    return {
        "status": "completed",
        "scanned_cases_count": len(cases),
        "breaches_flagged_count": sum(1 for c in cases if c.statutory_deadline_breached),
    }


@router.post("/assess/{policy_number}", summary="Invoke Agent A7 Renewal Advisor on policy")
def assess_policy_renewal(
    policy_number: str,
    req: AssessRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("policy:read")),
) -> dict[str, Any]:
    from datetime import date

    as_of = date.fromisoformat(req.as_of_date) if req.as_of_date else None
    try:
        assessment = renewal_advisor_agent.assess_policy_renewal(
            session=db,
            policy_number=policy_number,
            applicant_message=req.message,
            as_of_date=as_of,
        )
        db.commit()
        return assessment.model_dump()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/cases/{case_id}/offer", summary="Issue renewal quote offer to policyholder")
def generate_offer(
    case_id: str,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("policy:write")),
) -> dict[str, Any]:
    try:
        user_id = user_payload.get("sub", "system")
        case = renewal_service.generate_renewal_offer(db, case_id, user_id=user_id)
        db.commit()
        return {
            "status": "success",
            "message": "Renewal offer issued.",
            "case_id": case.id,
            "policy_number": case.policy_number,
            "proposed_premium": float(case.proposed_premium),
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/cases/{case_id}/non-renewal", summary="Issue statutory non-renewal notice (L2 Underwriter Sign-off)")
def issue_non_renewal(
    case_id: str,
    req: NonRenewalRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("underwriting:refer")),
) -> dict[str, Any]:
    try:
        user_id = user_payload.get("sub", "system")
        case = renewal_service.issue_non_renewal_notice(
            session=db,
            renewal_case_id=case_id,
            rationale=req.rationale,
            underwriter_name=req.underwriter_name,
            user_id=user_id,
        )
        db.commit()
        return {
            "status": "success",
            "message": "Statutory non-renewal notice recorded with underwriter sign-off.",
            "case_id": case.id,
            "policy_number": case.policy_number,
            "notice_sent": case.notice_sent,
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/cases/{case_id}/accept", summary="Accept renewal terms and issue renewed policy contract")
def accept_renewal_terms(
    case_id: str,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("policy:write")),
) -> dict[str, Any]:
    try:
        user_id = user_payload.get("sub", "system")
        renewed_policy = renewal_service.accept_renewal(db, case_id, user_id=user_id)
        db.commit()
        return {
            "status": "success",
            "message": "Policy successfully renewed for next annual term.",
            "renewed_policy_number": renewed_policy.policy_number,
            "new_start_date": renewed_policy.start_date.isoformat(),
            "new_end_date": renewed_policy.end_date.isoformat(),
            "premium": float(renewed_policy.total_premium),
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
