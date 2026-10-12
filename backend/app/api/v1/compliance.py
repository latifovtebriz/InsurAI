"""Compliance and Sanctions Screening REST API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.compliance.models import ComplianceAlert
from app.modules.compliance.public import (
    compliance_explainer_agent,
    compliance_service,
)
from app.modules.platform.public import require_permission

router = APIRouter(prefix="/compliance", tags=["Compliance & AML Screening"])


class ScreenPartyRequest(BaseModel):
    party_id: str = Field(description="Party UUID")
    party_name: str = Field(description="Full legal name of person or company")
    tax_id: str | None = Field(default=None, description="Optional FIN code or corporate tax ID")


class AdjudicateAlertRequest(BaseModel):
    decision: str = Field(
        description="confirmed_hit, false_positive_cleared_by_officer, under_review"
    )
    decision_notes: str = Field(description="Mandatory written justification by compliance officer")


@router.get("/alerts", summary="List AML/sanctions compliance alerts")
def list_compliance_alerts(
    status_filter: str | None = Query(None, description="Filter by alert status"),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("compliance:read")),
) -> list[dict[str, Any]]:
    stmt = select(ComplianceAlert)
    if status_filter:
        stmt = stmt.where(ComplianceAlert.status == status_filter)
    stmt = stmt.order_by(ComplianceAlert.match_score.desc())

    alerts = db.scalars(stmt).all()
    return [
        {
            "id": a.id,
            "alert_number": a.alert_number,
            "party_id": a.party_id,
            "party_name": a.party_name,
            "matched_entity_id": a.matched_entity_id,
            "matched_entity_name": a.matched_entity_name,
            "match_score": float(a.match_score),
            "match_reasons": a.match_reasons,
            "status": a.status,
            "assigned_officer_id": a.assigned_officer_id,
            "officer_decision_notes": a.officer_decision_notes,
            "decided_at": a.decided_at.isoformat() if a.decided_at else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


@router.post("/screen", summary="Run sanctions and watchlist screening on a party")
def screen_party(
    req: ScreenPartyRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("compliance:write")),
) -> dict[str, Any]:
    user_id = user_payload.get("sub", "system")
    alerts = compliance_service.screen_party(
        session=db,
        party_id=req.party_id,
        party_name=req.party_name,
        tax_id=req.tax_id,
        user_id=user_id,
    )
    db.commit()
    return {
        "status": "completed",
        "matches_count": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "alert_number": a.alert_number,
                "matched_name": a.matched_entity_name,
                "score": float(a.match_score),
            }
            for a in alerts
        ],
    }


@router.post("/assess/{alert_id}", summary="Invoke Agent A8 Compliance Explainer on alert")
def assess_alert_with_a8(
    alert_id: str,
    party_tax_id: str | None = Query(None, description="Optional party tax ID"),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("compliance:read")),
) -> dict[str, Any]:
    alert = db.get(ComplianceAlert, alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Alert '{alert_id}' not found."
        )

    explanation = compliance_explainer_agent.explain_compliance_alert(
        session=db,
        alert=alert,
        party_tax_id=party_tax_id,
    )
    return explanation.model_dump()


@router.post(
    "/alerts/{alert_id}/adjudicate", summary="Human Compliance Officer adjudication decision"
)
def adjudicate_alert(
    alert_id: str,
    req: AdjudicateAlertRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("compliance:write")),
) -> dict[str, Any]:
    try:
        officer_id = user_payload.get("sub", "compliance_officer")
        alert = compliance_service.adjudicate_alert(
            session=db,
            alert_id=alert_id,
            decision=req.decision,
            officer_id=officer_id,
            decision_notes=req.decision_notes,
            user_id=officer_id,
        )
        db.commit()
        return {
            "status": "success",
            "message": "Compliance alert successfully adjudicated by officer.",
            "alert_number": alert.alert_number,
            "alert_status": alert.status,
            "decided_by": alert.assigned_officer_id,
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
