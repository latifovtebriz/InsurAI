"""Fraud evaluation and SIU case management services."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.modules.claims.public import Claim
from app.modules.fraud.engine import evaluate_fraud_signals
from app.modules.fraud.models import FraudSignalRecord, SIUCase
from app.modules.platform.public import publish_outbox_event, record_audit_event
from app.modules.policy.public import Policy
from sqlalchemy import select
from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(UTC)


class FraudService:
    """Service orchestrating fraud risk evaluation and Special Investigation Unit case workflows."""

    def evaluate_and_route_claim(
        self,
        session: Session,
        claim_id: str,
        user_id: str | None = None,
        has_police_report: bool = True,
        incident_hour: int | None = None,
        unwitnessed_single_vehicle: bool = False,
    ) -> tuple[int, list[dict[str, Any]], SIUCase | None]:
        """
        Runs fraud scoring on a claim. If score >= 70, automatically creates and routes an SIU case.
        """
        claim = session.get(Claim, claim_id)
        if not claim:
            raise ValueError(f"Claim with id '{claim_id}' not found.")

        policy = session.scalars(
            select(Policy).where(Policy.policy_number == claim.policy_number)
        ).first()

        start_d = policy.start_date if policy else claim.incident_date
        sum_ins = policy.sum_insured if policy else Decimal("30000.00")

        # Prior claims count for this policy
        prior_claims = session.scalars(
            select(Claim).where(
                Claim.policy_number == claim.policy_number,
                Claim.id != claim.id,
                Claim.status != "rejected",
            )
        ).all()

        score, signals = evaluate_fraud_signals(
            policy_start_date=start_d,
            incident_date=claim.incident_date,
            notification_date=claim.notification_date,
            claimed_amount=claim.claimed_amount,
            sum_insured=sum_ins,
            prior_claims_count=len(prior_claims),
            has_police_report=has_police_report,
            incident_hour=incident_hour,
            unwitnessed_single_vehicle=unwitnessed_single_vehicle,
        )

        # Record signals in DB
        for s in signals:
            sig_rec = FraudSignalRecord(
                claim_id=claim.id,
                claim_number=claim.claim_number,
                signal_code=s["code"],
                signal_name=s["name"],
                weight=s["weight"],
                description=s["description"],
            )
            session.add(sig_rec)

        siu_case: SIUCase | None = None

        # Route to SIU if high risk (score >= 70)
        if score >= 70:
            existing = session.scalars(select(SIUCase).where(SIUCase.claim_id == claim.id)).first()

            if existing:
                existing.risk_score = score
                siu_case = existing
            else:
                random_suffix = uuid.uuid4().hex[:6].upper()
                case_num = f"SIU-{datetime.now(UTC).strftime('%Y%m%d')}-{random_suffix}"

                siu_case = SIUCase(
                    case_number=case_num,
                    claim_id=claim.id,
                    claim_number=claim.claim_number,
                    policy_id=policy.id if policy else "UNKNOWN",
                    policy_number=claim.policy_number,
                    risk_score=score,
                    status="open",
                )
                session.add(siu_case)
                session.flush()

                record_audit_event(
                    session=session,
                    action="siu_case_routed",
                    entity_type="siu_case",
                    entity_id=siu_case.id,
                    after_state={
                        "case_number": case_num,
                        "claim_number": claim.claim_number,
                        "risk_score": score,
                        "signals_count": len(signals),
                    },
                    user_id=user_id,
                )

                publish_outbox_event(
                    session=session,
                    event_type="SIUCaseCreatedEvent",
                    aggregate_type="claim",
                    aggregate_id=claim.id,
                    payload={
                        "case_number": case_num,
                        "claim_number": claim.claim_number,
                        "risk_score": score,
                    },
                )

        session.flush()
        return score, signals, siu_case

    def update_siu_case_status(
        self,
        session: Session,
        case_id: str,
        status: str,
        findings_summary: str,
        investigator_id: str,
        user_id: str | None = None,
    ) -> SIUCase:
        """Updates SIU case status and records investigator findings."""
        case = session.get(SIUCase, case_id)
        if not case:
            raise ValueError(f"SIU case '{case_id}' not found.")

        old_status = case.status
        case.status = status
        case.findings_summary = findings_summary
        case.investigator_id = investigator_id

        record_audit_event(
            session=session,
            action="siu_case_updated",
            entity_type="siu_case",
            entity_id=case.id,
            before_state={"status": old_status},
            after_state={"status": status, "investigator": investigator_id},
            user_id=user_id,
        )

        session.flush()
        return case


fraud_service = FraudService()
