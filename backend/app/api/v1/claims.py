"""Claims management endpoints."""

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.claims.public import Claim, ClaimDocument, ClaimReserve, claims_service
from app.modules.platform.public import require_permission

router = APIRouter(prefix="/claims", tags=["Claims"])


class FNOLSubmissionRequest(BaseModel):
    policy_number: str
    incident_date: str = Field(..., description="YYYY-MM-DD")
    notification_date: str | None = Field(None, description="YYYY-MM-DD, defaults to today")
    claimed_amount: float
    incident_description: str
    product_code: str = "MOTOR_OD"
    documents: list[dict[str, str]] = Field(default_factory=list)


class AdjusterDecisionRequest(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")
    approved_payout: float | None = None
    notes: str = Field(..., description="Mandatory adjuster reasoning or justification note")
    override_reason: str | None = None


class ClaimSummaryResponse(BaseModel):
    id: str
    claim_number: str
    policy_number: str
    product_code: str
    incident_date: str
    status: str
    claimed_amount: float
    approved_payout: float | None = None
    autonomy_level: str
    recommendation: str | None = None
    confidence_score: float | None = None
    risk_flags: list[str] = Field(default_factory=list)
    created_at: str


class ClaimDetailResponse(BaseModel):
    id: str
    claim_number: str
    policy_number: str
    product_code: str
    incident_date: str
    notification_date: str
    status: str
    claimed_amount: float
    estimated_reserve: float
    approved_payout: float | None = None
    deductible_applied: float | None = None
    autonomy_level: str
    incident_description: str
    triage_recommendation: dict[str, Any] | None = None
    adjuster_decision: dict[str, Any] | None = None
    documents: list[dict[str, Any]] = Field(default_factory=list)
    reserves: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str


@router.post("/fnol", response_model=ClaimSummaryResponse, status_code=status.HTTP_201_CREATED)
def submit_fnol(
    req: FNOLSubmissionRequest,
    db: Session = Depends(get_db),
    user_claims: dict[str, Any] = Depends(require_permission("claims:create")),
) -> ClaimSummaryResponse:
    """Submits a First Notice of Loss (FNOL) and creates initial claim and reserve."""
    inc_date = date.fromisoformat(req.incident_date)
    notif_date = date.fromisoformat(req.notification_date) if req.notification_date else None

    claim = claims_service.submit_fnol(
        session=db,
        policy_number=req.policy_number,
        incident_date=inc_date,
        claimed_amount=Decimal(str(req.claimed_amount)),
        incident_description=req.incident_description,
        notification_date=notif_date,
        product_code=req.product_code,
        documents=req.documents,
        actor_id=user_claims.get("sub", "customer"),
    )

    return ClaimSummaryResponse(
        id=claim.id,
        claim_number=claim.claim_number,
        policy_number=claim.policy_number,
        product_code=claim.product_code,
        incident_date=claim.incident_date.isoformat(),
        status=claim.status,
        claimed_amount=float(claim.claimed_amount),
        approved_payout=float(claim.approved_payout) if claim.approved_payout else None,
        autonomy_level=claim.autonomy_level,
        recommendation=None,
        confidence_score=None,
        risk_flags=[],
        created_at=claim.created_at.isoformat(),
    )


@router.get("", response_model=list[ClaimSummaryResponse])
def list_claims(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None, description="Search by claim number or policy number"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("claims:read")),
) -> list[ClaimSummaryResponse]:
    """Retrieves the claims queue with filtering and pagination."""
    stmt = select(Claim)
    if status_filter:
        stmt = stmt.where(Claim.status == status_filter)
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(Claim.claim_number.ilike(term), Claim.policy_number.ilike(term)))
    stmt = stmt.order_by(Claim.created_at.desc()).offset(offset).limit(limit)

    claims = db.scalars(stmt).all()
    results: list[ClaimSummaryResponse] = []
    for c in claims:
        rec = c.triage_recommendation or {}
        results.append(
            ClaimSummaryResponse(
                id=c.id,
                claim_number=c.claim_number,
                policy_number=c.policy_number,
                product_code=c.product_code,
                incident_date=c.incident_date.isoformat(),
                status=c.status,
                claimed_amount=float(c.claimed_amount),
                approved_payout=float(c.approved_payout) if c.approved_payout else None,
                autonomy_level=c.autonomy_level,
                recommendation=rec.get("recommendation"),
                confidence_score=float(rec.get("confidence", 0.0)) if rec else None,
                risk_flags=rec.get("risk_flags", []),
                created_at=c.created_at.isoformat(),
            )
        )
    return results


@router.get("/{claim_number}", response_model=ClaimDetailResponse)
def get_claim_detail(
    claim_number: str,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("claims:read")),
) -> ClaimDetailResponse:
    """Retrieves full claim details, evidence documents, reserves, and A4 recommendation."""
    claim = claims_service.get_claim_by_number(db, claim_number)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_number}' not found",
        )

    # Documents
    docs_stmt = select(ClaimDocument).where(ClaimDocument.claim_id == claim.id)
    docs = db.scalars(docs_stmt).all()
    doc_dicts = [
        {
            "id": d.id,
            "document_type": d.document_type,
            "file_name": d.file_name,
            "content_preview": (d.content_text[:200] + "...") if len(d.content_text) > 200 else d.content_text,
            "content_text": d.content_text,
            "created_at": d.created_at.isoformat(),
        }
        for d in docs
    ]

    # Reserves
    res_stmt = select(ClaimReserve).where(ClaimReserve.claim_id == claim.id).order_by(ClaimReserve.created_at.asc())
    reserves = db.scalars(res_stmt).all()
    reserve_dicts = [
        {
            "id": r.id,
            "amount": float(r.amount),
            "reserve_type": r.reserve_type,
            "reason": r.reason,
            "created_at": r.created_at.isoformat(),
        }
        for r in reserves
    ]

    return ClaimDetailResponse(
        id=claim.id,
        claim_number=claim.claim_number,
        policy_number=claim.policy_number,
        product_code=claim.product_code,
        incident_date=claim.incident_date.isoformat(),
        notification_date=claim.notification_date.isoformat(),
        status=claim.status,
        claimed_amount=float(claim.claimed_amount),
        estimated_reserve=float(claim.estimated_reserve),
        approved_payout=float(claim.approved_payout) if claim.approved_payout else None,
        deductible_applied=float(claim.deductible_applied) if claim.deductible_applied else None,
        autonomy_level=claim.autonomy_level,
        incident_description=claim.incident_description,
        triage_recommendation=claim.triage_recommendation,
        adjuster_decision=claim.adjuster_decision,
        documents=doc_dicts,
        reserves=reserve_dicts,
        created_at=claim.created_at.isoformat(),
    )


@router.post("/{claim_number}/triage", response_model=ClaimDetailResponse)
async def trigger_triage(
    claim_number: str,
    db: Session = Depends(get_db),
    user_claims: dict[str, Any] = Depends(require_permission("claims:review")),
) -> ClaimDetailResponse:
    """Executes Claims Triage Agent A4 on the claim."""
    claim = claims_service.get_claim_by_number(db, claim_number)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_number}' not found",
        )

    actor_id = user_claims.get("sub", "A4_agent")
    updated_claim = await claims_service.triage_claim(db, claim.id, actor_id=actor_id)
    return get_claim_detail(updated_claim.claim_number, db, user_claims)


@router.post("/{claim_number}/decision", response_model=ClaimDetailResponse)
def record_adjuster_decision(
    claim_number: str,
    req: AdjusterDecisionRequest,
    db: Session = Depends(get_db),
    user_claims: dict[str, Any] = Depends(require_permission("claims:adjudicate")),
) -> ClaimDetailResponse:
    """Records human adjuster adjudication decision with mandatory reasoning note."""
    claim = claims_service.get_claim_by_number(db, claim_number)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_number}' not found",
        )

    adjuster_id = user_claims.get("sub", "adjuster_1")
    payout = Decimal(str(req.approved_payout)) if req.approved_payout is not None else None

    updated_claim = claims_service.record_adjuster_decision(
        session=db,
        claim_id=claim.id,
        decision=req.decision,
        approved_payout=payout,
        notes=req.notes,
        adjuster_id=adjuster_id,
        override_reason=req.override_reason,
    )
    return get_claim_detail(updated_claim.claim_number, db, user_claims)


@router.post("/{claim_number}/settle", response_model=ClaimDetailResponse)
def settle_claim(
    claim_number: str,
    db: Session = Depends(get_db),
    user_claims: dict[str, Any] = Depends(require_permission("claims:settle")),
) -> ClaimDetailResponse:
    """Disburses approved claim payout and completes settlement."""
    claim = claims_service.get_claim_by_number(db, claim_number)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim '{claim_number}' not found",
        )

    actor_id = user_claims.get("sub", "finance_officer")
    updated_claim = claims_service.settle_claim(db, claim.id, actor_id=actor_id)
    return get_claim_detail(updated_claim.claim_number, db, user_claims)
