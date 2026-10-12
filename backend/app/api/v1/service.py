"""Customer Service, Complaints, and Policy Servicing (A3/A6) REST API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.platform.public import require_permission
from app.modules.service.models import Complaint
from app.modules.service.public import (
    customer_service_agent,
    customer_service_domain,
    policy_servicing_agent,
)

router = APIRouter(prefix="/service", tags=["Customer Service & Policy Servicing"])


class CustomerChatRequest(BaseModel):
    message: str = Field(description="Customer question or inquiry")
    is_authenticated: bool = Field(default=False, description="Verification gate toggle")
    verified_party_id: str | None = Field(default=None, description="Party ID if authenticated")
    customer_identifier: str = Field(default="guest_user", description="Customer phone or email")


class CreateComplaintRequest(BaseModel):
    party_id: str = Field(description="Customer party UUID")
    subject: str = Field(description="Complaint subject")
    description: str = Field(description="Detailed description of issue")
    policy_id: str | None = Field(default=None, description="Related policy ID")
    claim_id: str | None = Field(default=None, description="Related claim ID")


class ProposeEndorsementRequest(BaseModel):
    policy_number: str = Field(description="Policy number")
    endorsement_type: str = Field(description="ADD_DRIVER, INCREASE_SUM_INSURED, ADDRESS_CHANGE")
    effective_date: str = Field(description="ISO date YYYY-MM-DD")
    changes: dict[str, Any] = Field(description="Parameter changes dict")


@router.post("/chat", summary="Customer Service Chat Assistant (Agent A6) with Verification Gate")
def customer_service_chat(
    req: CustomerChatRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    response = customer_service_agent.handle_customer_message(
        session=db,
        message=req.message,
        is_authenticated=req.is_authenticated,
        verified_party_id=req.verified_party_id,
        customer_identifier=req.customer_identifier,
    )
    return response.model_dump()


@router.get("/complaints", summary="List complaints with statutory SLA status")
def list_complaints(
    status_filter: str | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("service:read")),
) -> list[dict[str, Any]]:
    stmt = select(Complaint)
    if status_filter:
        stmt = stmt.where(Complaint.status == status_filter)
    stmt = stmt.order_by(Complaint.final_resolution_deadline)

    complaints = db.scalars(stmt).all()
    return [
        {
            "id": c.id,
            "complaint_number": c.complaint_number,
            "party_id": c.party_id,
            "subject": c.subject,
            "description": c.description,
            "status": c.status,
            "initial_response_deadline": c.initial_response_deadline.isoformat(),
            "final_resolution_deadline": c.final_resolution_deadline.isoformat(),
            "sla_breached": c.sla_breached,
            "created_at": c.created_at.isoformat(),
        }
        for c in complaints
    ]


@router.post(
    "/complaints", summary="Register customer complaint with 5/15 day statutory SLA countdown"
)
def register_complaint(
    req: CreateComplaintRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("service:write")),
) -> dict[str, Any]:
    user_id = user_payload.get("sub", "system")
    complaint = customer_service_domain.register_complaint(
        session=db,
        party_id=req.party_id,
        subject=req.subject,
        description=req.description,
        policy_id=req.policy_id,
        claim_id=req.claim_id,
        user_id=user_id,
    )
    db.commit()
    return {
        "status": "registered",
        "complaint_number": complaint.complaint_number,
        "initial_response_deadline": complaint.initial_response_deadline.isoformat(),
        "final_resolution_deadline": complaint.final_resolution_deadline.isoformat(),
        "sla_breached": complaint.sla_breached,
    }


@router.post("/endorsements/propose", summary="Propose mid-term endorsement draft (Agent A3)")
def propose_endorsement(
    req: ProposeEndorsementRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("policy:read")),
) -> dict[str, Any]:
    try:
        result = policy_servicing_agent.process_endorsement_request(
            session=db,
            policy_number=req.policy_number,
            endorsement_type=req.endorsement_type,
            changes=req.changes,
            effective_date=req.effective_date,
        )
        db.commit()
        return result.model_dump()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/endorsements/{draft_id}/approve", summary="Approve and apply endorsement to policy")
def approve_endorsement(
    draft_id: str,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("policy:write")),
) -> dict[str, Any]:
    try:
        officer = user_payload.get("sub", "underwriter")
        draft = customer_service_domain.approve_endorsement(
            session=db,
            draft_id=draft_id,
            underwriter_name=officer,
            user_id=officer,
        )
        db.commit()
        return {
            "status": "success",
            "message": "Endorsement approved and applied to active policy.",
            "draft_number": draft.draft_number,
            "policy_id": draft.policy_id,
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
