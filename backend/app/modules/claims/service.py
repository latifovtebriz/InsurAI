"""Claims domain service managing FNOL, registration, A4 triage, adjuster review, and settlement."""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.config import settings
from app.modules.claims.agent import ClaimsTriageAgent
from app.modules.claims.models import Claim, ClaimDocument, ClaimReserve
from app.modules.platform.public import (
    CLAIM_WORKFLOW,
    InsurAIException,
    publish_outbox_event,
    record_audit_event,
)
from app.modules.policy.public import policy_service
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(UTC)


class ClaimsService:
    """Core domain service for the insurance claims lifecycle."""

    def submit_fnol(
        self,
        session: Session,
        policy_number: str,
        incident_date: date,
        claimed_amount: Decimal,
        incident_description: str,
        notification_date: date | None = None,
        product_code: str = "MOTOR_OD",
        documents: list[dict[str, str]] | None = None,
        actor_id: str = "customer",
    ) -> Claim:
        """
        Ingests a First Notice of Loss (FNOL) and creates initial Claim and Document records.
        """
        notif_date = notification_date or date.today()
        year = incident_date.year
        count = session.scalar(select(func.count(Claim.id))) or 0
        claim_number = f"CLM-{year}-{count + 1:04d}"

        # Resolve policy if exists
        rep = policy_service.check_policy_active(session, policy_number, incident_date)
        policy_id = rep.policy_id

        claim = Claim(
            claim_number=claim_number,
            policy_id=policy_id,
            policy_number=policy_number,
            incident_date=incident_date,
            notification_date=notif_date,
            product_code=product_code,
            status="fnol_received",
            claimed_amount=claimed_amount,
            estimated_reserve=claimed_amount,
            incident_description=incident_description,
            raw_documents=documents or [],
            autonomy_level="L2",
        )
        session.add(claim)
        session.flush()

        # Ingest document records
        if documents:
            for doc in documents:
                session.add(
                    ClaimDocument(
                        claim_id=claim.id,
                        document_type=doc.get("type", "document"),
                        file_name=doc.get("file_name", "document.txt"),
                        content_text=doc.get("content", ""),
                    )
                )

        # Preliminary reserve ledger entry
        session.add(
            ClaimReserve(
                claim_id=claim.id,
                amount=claimed_amount,
                reserve_type="initial",
                reason="Initial FNOL estimated reserve equal to claimed amount.",
            )
        )

        # Transition to registered
        new_status = CLAIM_WORKFLOW.trigger(claim.status, "register_claim")
        claim.status = new_status

        publish_outbox_event(
            session=session,
            event_type="ClaimRegistered",
            aggregate_type="claim",
            aggregate_id=claim.id,
            payload={
                "claim_number": claim_number,
                "policy_number": policy_number,
                "claimed_amount": float(claimed_amount),
                "incident_date": incident_date.isoformat(),
            },
        )
        record_audit_event(
            session=session,
            user_id=actor_id,
            action="claim.registered",
            entity_type="claim",
            entity_id=claim.id,
            after_state={"claim_number": claim_number, "status": new_status},
        )

        session.commit()
        session.refresh(claim)
        return claim

    async def triage_claim(
        self,
        session: Session,
        claim_id: str,
        actor_id: str = "A4_agent",
    ) -> Claim:
        """
        Executes Claims Triage Agent A4 on registered claim, evaluating coverage, wording, payout, and risk.
        """
        claim = session.get(Claim, claim_id)
        if not claim:
            raise InsurAIException(
                status_code=404, title="Claim Not Found", detail=f"Claim '{claim_id}' not found."
            )

        old_status = claim.status
        claim.status = CLAIM_WORKFLOW.trigger(claim.status, "start_triage")
        session.commit()

        # Gather documents text
        doc_texts = [d.get("content", "") for d in claim.raw_documents if isinstance(d, dict)]

        # Run A4 Agent
        agent = ClaimsTriageAgent(session=session)
        recommendation = await agent.triage(
            claim_number=claim.claim_number,
            policy_number=claim.policy_number,
            incident_date=claim.incident_date.isoformat(),
            claimed_amount=float(claim.claimed_amount),
            description=claim.incident_description,
            raw_documents=doc_texts,
            correlation_id=f"triage-{claim.claim_number}",
        )

        claim.triage_recommendation = recommendation
        rec_decision = recommendation.get("recommendation", "needs_human_review")
        confidence = float(recommendation.get("confidence", 0.0))
        risk_flags = recommendation.get("risk_flags", [])
        missing_info = recommendation.get("missing_information", [])

        # Check Simulated L3 Auto-Approve Bounds (Appendix G.9 & G.6)
        is_l3_eligible = (
            rec_decision == "approve"
            and confidence >= 0.85
            and claim.claimed_amount <= Decimal(str(settings.auto_approve_max_amount))
            and len(risk_flags) == 0
            and len(missing_info) == 0
        )

        if is_l3_eligible:
            claim.autonomy_level = "L3"
            claim.status = CLAIM_WORKFLOW.trigger(claim.status, "auto_approve_l3")
            payout_val = float(recommendation.get("payout", {}).get("payable", 0.0))
            claim.approved_payout = Decimal(str(payout_val))
            claim.deductible_applied = Decimal(
                str(recommendation.get("payout", {}).get("deductible", 200.0))
            )
        else:
            claim.autonomy_level = "L2"
            claim.status = CLAIM_WORKFLOW.trigger(claim.status, "submit_recommendation")

        publish_outbox_event(
            session=session,
            event_type="ClaimTriaged",
            aggregate_type="claim",
            aggregate_id=claim.id,
            payload={
                "claim_number": claim.claim_number,
                "recommendation": rec_decision,
                "autonomy_level": claim.autonomy_level,
                "status": claim.status,
            },
        )
        record_audit_event(
            session=session,
            user_id=actor_id,
            action="claim.triaged",
            entity_type="claim",
            entity_id=claim.id,
            before_state={"status": old_status},
            after_state={
                "status": claim.status,
                "recommendation": rec_decision,
                "autonomy_level": claim.autonomy_level,
            },
        )

        session.commit()
        session.refresh(claim)
        return claim

    def record_adjuster_decision(
        self,
        session: Session,
        claim_id: str,
        decision: str,  # "approve" or "reject"
        approved_payout: Decimal | None = None,
        notes: str = "",
        adjuster_id: str = "adjuster_1",
        override_reason: str | None = None,
    ) -> Claim:
        """
        Human adjuster adjudication: confirms approval or rejection with audit record.
        """
        claim = session.get(Claim, claim_id)
        if not claim:
            raise InsurAIException(
                status_code=404, title="Claim Not Found", detail=f"Claim '{claim_id}' not found."
            )

        old_status = claim.status
        if decision == "approve":
            claim.status = CLAIM_WORKFLOW.trigger(claim.status, "confirm_approval")
            claim.approved_payout = approved_payout or claim.claimed_amount
        elif decision == "reject":
            claim.status = CLAIM_WORKFLOW.trigger(claim.status, "confirm_rejection")
            claim.approved_payout = Decimal("0.00")
        else:
            raise InsurAIException(
                status_code=400,
                title="Invalid Decision",
                detail="Decision must be 'approve' or 'reject'.",
            )

        decision_data = {
            "decision": decision,
            "adjuster_id": adjuster_id,
            "decided_at": utcnow().isoformat(),
            "notes": notes,
            "override_reason": override_reason,
            "approved_payout": float(claim.approved_payout or 0.0),
        }
        claim.adjuster_decision = decision_data

        record_audit_event(
            session=session,
            user_id=adjuster_id,
            action=f"claim.{decision}d",
            entity_type="claim",
            entity_id=claim.id,
            before_state={"status": old_status},
            after_state={"status": claim.status, "decision": decision, "override": override_reason},
        )
        session.commit()
        session.refresh(claim)
        return claim

    def settle_claim(
        self,
        session: Session,
        claim_id: str,
        actor_id: str = "finance_officer",
    ) -> Claim:
        """Disburses approved claim payout and releases claims reserve."""
        claim = session.get(Claim, claim_id)
        if not claim:
            raise InsurAIException(
                status_code=404, title="Claim Not Found", detail=f"Claim '{claim_id}' not found."
            )

        old_status = claim.status
        claim.status = CLAIM_WORKFLOW.trigger(claim.status, "disburse_payment")

        # Post final reserve adjustment (reserve = approved payout)
        session.add(
            ClaimReserve(
                claim_id=claim.id,
                amount=claim.approved_payout or Decimal("0.00"),
                reserve_type="final",
                reason="Claim finalized and approved payout disbursed.",
            )
        )

        publish_outbox_event(
            session=session,
            event_type="ClaimSettled",
            aggregate_type="claim",
            aggregate_id=claim.id,
            payload={
                "claim_number": claim.claim_number,
                "approved_payout": float(claim.approved_payout or 0.0),
            },
        )
        record_audit_event(
            session=session,
            user_id=actor_id,
            action="claim.settled",
            entity_type="claim",
            entity_id=claim.id,
            before_state={"status": old_status},
            after_state={
                "status": claim.status,
                "approved_payout": float(claim.approved_payout or 0.0),
            },
        )
        session.commit()
        session.refresh(claim)
        return claim

    def get_claim_by_id(self, session: Session, claim_id: str) -> Claim | None:
        return session.get(Claim, claim_id)

    def get_claim_by_number(self, session: Session, claim_number: str) -> Claim | None:
        return session.scalars(select(Claim).where(Claim.claim_number == claim_number)).first()

    def list_claims(self, session: Session, status: str | None = None) -> list[Claim]:
        query = select(Claim)
        if status:
            query = query.where(Claim.status == status)
        return list(session.scalars(query.order_by(Claim.created_at.desc())).all())


claims_service = ClaimsService()
