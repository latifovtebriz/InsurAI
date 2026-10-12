"""Fraud and Special Investigation Unit (SIU) REST API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.claims.public import Claim
from app.modules.fraud.models import FraudSignalRecord, SIUCase
from app.modules.fraud.public import fraud_assistant_agent, fraud_service
from app.modules.platform.public import require_permission

router = APIRouter(prefix="/siu", tags=["Fraud & Special Investigation Unit"])


class AssessClaimRequest(BaseModel):
    investigator_notes: str = Field(
        default="", description="Optional preliminary notes from adjuster"
    )


class UpdateSIUCaseRequest(BaseModel):
    status: str = Field(description="open, under_investigation, cleared, referred_legal, closed")
    findings_summary: str = Field(description="Objective investigation findings")
    investigator_id: str = Field(description="Investigator badge or username")


@router.get("/cases", summary="List Special Investigation Unit (SIU) cases")
def list_siu_cases(
    status_filter: str | None = Query(None, description="Filter by case status"),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("fraud:read")),
) -> list[dict[str, Any]]:
    stmt = select(SIUCase)
    if status_filter:
        stmt = stmt.where(SIUCase.status == status_filter)
    stmt = stmt.order_by(SIUCase.risk_score.desc())

    cases = db.scalars(stmt).all()
    return [
        {
            "id": c.id,
            "case_number": c.case_number,
            "claim_id": c.claim_id,
            "claim_number": c.claim_number,
            "policy_number": c.policy_number,
            "risk_score": c.risk_score,
            "status": c.status,
            "investigator_id": c.investigator_id,
            "findings_summary": c.findings_summary,
            "created_at": c.created_at.isoformat(),
        }
        for c in cases
    ]


@router.get("/cases/{case_id}", summary="Get detailed SIU case with triggered fraud signals")
def get_siu_case(
    case_id: str,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("fraud:read")),
) -> dict[str, Any]:
    case = db.get(SIUCase, case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"SIU case '{case_id}' not found."
        )

    signals_stmt = select(FraudSignalRecord).where(FraudSignalRecord.claim_id == case.claim_id)
    signals = db.scalars(signals_stmt).all()

    return {
        "id": case.id,
        "case_number": case.case_number,
        "claim_id": case.claim_id,
        "claim_number": case.claim_number,
        "policy_number": case.policy_number,
        "risk_score": case.risk_score,
        "status": case.status,
        "investigator_id": case.investigator_id,
        "findings_summary": case.findings_summary,
        "created_at": case.created_at.isoformat(),
        "signals": [
            {
                "signal_code": s.signal_code,
                "signal_name": s.signal_name,
                "weight": s.weight,
                "description": s.description,
                "detected_at": s.detected_at.isoformat(),
            }
            for s in signals
        ],
    }


@router.post("/assess/{claim_number}", summary="Invoke Agent A5 Fraud Assistant on claim")
def assess_claim_siu(
    claim_number: str,
    req: AssessClaimRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("fraud:read")),
) -> dict[str, Any]:
    claim = db.scalars(select(Claim).where(Claim.claim_number == claim_number)).first()
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Claim '{claim_number}' not found."
        )

    score, signals, _ = fraud_service.evaluate_and_route_claim(db, claim.id)
    assessment = fraud_assistant_agent.assess_claim_for_siu(
        claim_number=claim.claim_number,
        risk_score=score,
        triggered_signals=signals,
        investigator_notes=req.investigator_notes,
    )
    db.commit()
    return assessment.model_dump()


@router.post("/cases/{case_id}/update", summary="Update SIU case investigation findings")
def update_siu_case(
    case_id: str,
    req: UpdateSIUCaseRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("fraud:write")),
) -> dict[str, Any]:
    try:
        user_id = user_payload.get("sub", "investigator")
        case = fraud_service.update_siu_case_status(
            session=db,
            case_id=case_id,
            status=req.status,
            findings_summary=req.findings_summary,
            investigator_id=req.investigator_id,
            user_id=user_id,
        )
        db.commit()
        return {
            "status": "success",
            "message": "SIU case updated.",
            "case_number": case.case_number,
            "case_status": case.status,
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
