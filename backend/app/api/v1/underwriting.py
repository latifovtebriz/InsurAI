"""Underwriting referral queue and Copilot endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.platform.public import require_permission
from app.modules.underwriting.public import (
    UnderwritingCase,
    underwriting_service,
)

router = APIRouter(prefix="/underwriting", tags=["Underwriting & Referral"])


class UnderwritingCaseSummaryResponse(BaseModel):
    id: str
    case_number: str
    quote_id: str | None
    product_code: str
    sum_insured: float
    proposed_premium: float
    status: str
    authority_tier_required: str
    rule_hits_count: int
    risk_score: float
    created_at: str


class UnderwritingCaseDetailResponse(BaseModel):
    id: str
    case_number: str
    quote_id: str | None
    policy_id: str | None
    product_code: str
    sum_insured: float
    proposed_premium: float
    status: str
    authority_tier_required: str
    rule_hits: list[dict[str, Any]]
    risk_score: float
    copilot_assessment: dict[str, Any] | None = None
    underwriter_decision: dict[str, Any] | None = None
    notes: str | None = None
    created_at: str


class UnderwriterDecisionRequest(BaseModel):
    decision: str  # approved_standard, approved_with_conditions, declined
    conditions: list[str] | None = None
    override_reason: str | None = None
    notes: str | None = None


@router.get("/cases", response_model=list[UnderwritingCaseSummaryResponse])
def list_underwriting_cases(
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("underwriting:read")),
) -> list[UnderwritingCaseSummaryResponse]:
    """Lists underwriting referral cases."""
    stmt = select(UnderwritingCase)
    if status_filter:
        stmt = stmt.where(UnderwritingCase.status == status_filter)
    stmt = stmt.order_by(UnderwritingCase.created_at.desc()).limit(limit)

    cases = db.scalars(stmt).all()
    return [
        UnderwritingCaseSummaryResponse(
            id=c.id,
            case_number=c.case_number,
            quote_id=c.quote_id,
            product_code=c.product_code,
            sum_insured=float(c.sum_insured),
            proposed_premium=float(c.proposed_premium),
            status=c.status,
            authority_tier_required=c.authority_tier_required,
            rule_hits_count=len(c.rule_hits),
            risk_score=c.risk_score,
            created_at=c.created_at.isoformat(),
        )
        for c in cases
    ]


@router.get("/cases/{case_id}", response_model=UnderwritingCaseDetailResponse)
def get_underwriting_case_detail(
    case_id: str,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("underwriting:read")),
) -> UnderwritingCaseDetailResponse:
    """Retrieves full case dossier with rule hits and copilot assessment."""
    stmt = select(UnderwritingCase).where(
        (UnderwritingCase.id == case_id) | (UnderwritingCase.case_number == case_id)
    )
    case = db.scalars(stmt).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Underwriting case '{case_id}' not found",
        )

    return UnderwritingCaseDetailResponse(
        id=case.id,
        case_number=case.case_number,
        quote_id=case.quote_id,
        policy_id=case.policy_id,
        product_code=case.product_code,
        sum_insured=float(case.sum_insured),
        proposed_premium=float(case.proposed_premium),
        status=case.status,
        authority_tier_required=case.authority_tier_required,
        rule_hits=case.rule_hits,
        risk_score=case.risk_score,
        copilot_assessment=case.copilot_assessment,
        underwriter_decision=case.underwriter_decision,
        notes=case.notes,
        created_at=case.created_at.isoformat(),
    )


@router.post("/cases/{case_id}/assess", response_model=UnderwritingCaseDetailResponse)
def run_copilot_assessment(
    case_id: str,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("underwriting:read")),
) -> UnderwritingCaseDetailResponse:
    """Triggers A2 Underwriting Copilot to analyze risk and ground recommendations in guidelines."""
    try:
        case = underwriting_service.run_copilot_assessment(db=db, case_id=case_id)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return get_underwriting_case_detail(case.id, db=db, _user=_user)


@router.post("/cases/{case_id}/decision", response_model=UnderwritingCaseDetailResponse)
def record_underwriter_decision(
    case_id: str,
    req: UnderwriterDecisionRequest,
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_permission("underwriting:write")),
) -> UnderwritingCaseDetailResponse:
    """
    Submits human underwriter decision with authority verification and G3 written rationale enforcement.
    """
    role = user.get("role", "underwriter")
    actor = user.get("sub", "underwriter")

    try:
        case = underwriting_service.record_decision(
            db=db,
            case_id=case_id,
            decision=req.decision,
            underwriter_id=actor,
            underwriter_role=role,
            conditions=req.conditions,
            override_reason=req.override_reason,
            notes=req.notes,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    return get_underwriting_case_detail(case.id, db=db, _user=user)
