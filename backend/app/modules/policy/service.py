"""Policy Administration domain service: issuance (P04), payments, cancellations (P06), and coverage validation."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.modules.party.public import party_service
from app.modules.platform.public import (
    POLICY_WORKFLOW,
    InsurAIException,
    publish_outbox_event,
    record_audit_event,
)
from app.modules.policy.cancellation import (
    RefundCalculation,
    calculate_cancellation_refund,
)
from app.modules.policy.models import Policy, PolicyCertificate
from app.modules.policy.rating import generate_installment_schedule
from app.modules.product.public import product_service
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class PolicyStatusReport:
    exists: bool
    is_active: bool
    in_force: bool
    policy_id: str | None
    policy_number: str
    product_code: str | None
    product_version_id: str | None
    sum_insured: Decimal | None
    deductible: Decimal | None
    reasons: list[str]


class PolicyService:
    """Service managing the policy contract lifecycle, issuance, payments, and cancellations."""

    def issue_policy(
        self,
        session: Session,
        party_id: str,
        asset_id: str,
        product_code: str,
        start_date: date,
        end_date: date,
        sum_insured: Decimal,
        total_premium: Decimal,
        deductible: Decimal = Decimal("200.00"),
        installments_count: int = 1,
        initial_payment: Decimal = Decimal("0.00"),
        actor_id: str = "system",
    ) -> Policy:
        """
        Executes Process P04 (Policy Issuance):
        1. Pre-bind KYC check on party.
        2. Freezes active product version as of start_date.
        3. Generates unique policy number.
        4. Calculates installment schedule.
        5. Issues document certificate with SHA-256 hash.
        6. Emits PolicyIssued event to outbox and audit log.
        """
        # 1. Pre-bind check: KYC status
        party = party_service.get_party_by_id(session, party_id)
        if not party:
            raise InsurAIException(
                status_code=404,
                title="Party Not Found",
                detail=f"Party '{party_id}' does not exist.",
            )
        if party.kyc_status != "verified":
            raise InsurAIException(
                status_code=400,
                title="KYC Verification Required",
                detail=f"Party '{party_id}' KYC status is '{party.kyc_status}'. Must be 'verified' to bind policy.",
            )

        # 2. Product version in force (frozen version)
        product_version = product_service.get_active_version(session, product_code, start_date)
        if not product_version:
            raise InsurAIException(
                status_code=400,
                title="No Product Version In Force",
                detail=f"No published product version found for '{product_code}' as of inception date {start_date}.",
            )

        # 3. Policy Number generation: POL-{YEAR}-{PREFIX}-{SEQUENCE}
        year = start_date.year
        prefix_map = {"MOTOR_OD": "MOD", "MOTOR_TPL": "MTPL", "HOME": "HOM"}
        prefix = prefix_map.get(product_code, "GEN")
        count = (
            session.scalar(select(func.count(Policy.id)).where(Policy.product_code == product_code))
            or 0
        )
        policy_number = f"POL-{year}-{prefix}-{count + 1:04d}"

        # 4. Schedule generation
        schedule = generate_installment_schedule(total_premium, installments_count, start_date)
        schedule_dicts = [
            {
                "installment_number": inst.installment_number,
                "due_date": inst.due_date.isoformat(),
                "amount": float(inst.amount),
            }
            for inst in schedule
        ]

        # 5. Determine initial status
        initial_status = "active" if initial_payment >= schedule[0].amount else "pending_payment"

        policy = Policy(
            policy_number=policy_number,
            party_id=party_id,
            asset_id=asset_id,
            product_code=product_code,
            product_version_id=product_version.id,
            status=initial_status,
            start_date=start_date,
            end_date=end_date,
            sum_insured=sum_insured,
            deductible=deductible,
            total_premium=total_premium,
            paid_premium=initial_payment,
            payment_schedule=schedule_dicts,
        )
        session.add(policy)
        session.flush()

        # 6. Issue Certificate
        cert_payload = {
            "policy_number": policy_number,
            "party_name": f"{party.first_name} {party.last_name}"
            if party.first_name
            else party.company_name,
            "product_code": product_code,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "sum_insured": float(sum_insured),
            "total_premium": float(total_premium),
            "issued_at": utcnow().isoformat(),
        }
        cert_hash = hashlib.sha256(json.dumps(cert_payload, sort_keys=True).encode()).hexdigest()
        certificate = PolicyCertificate(
            policy_id=policy.id,
            certificate_number=f"CERT-{policy_number}",
            document_hash=cert_hash,
            content_json=cert_payload,
        )
        session.add(certificate)

        # 7. Outbox and Audit
        publish_outbox_event(
            session=session,
            event_type="PolicyIssued",
            aggregate_type="policy",
            aggregate_id=policy.id,
            payload={
                "policy_number": policy_number,
                "product_code": product_code,
                "party_id": party_id,
                "total_premium": float(total_premium),
                "status": initial_status,
            },
        )
        record_audit_event(
            session=session,
            user_id=actor_id,
            action="policy.issued",
            entity_type="policy",
            entity_id=policy.id,
            after_state={"status": initial_status, "policy_number": policy_number},
        )

        session.commit()
        session.refresh(policy)
        return policy

    def record_premium_payment(
        self,
        session: Session,
        policy_id: str,
        amount: Decimal,
        actor_id: str = "system",
    ) -> Policy:
        """Applies premium payment and transitions status to active if criteria are met."""
        policy = session.get(Policy, policy_id)
        if not policy:
            raise InsurAIException(
                status_code=404, title="Policy Not Found", detail=f"Policy '{policy_id}' not found."
            )

        old_status = policy.status
        policy.paid_premium += amount

        # State transition to active if in pending_payment
        if policy.status == "pending_payment" and policy.paid_premium > Decimal("0.00"):
            new_status = POLICY_WORKFLOW.trigger(policy.status, "confirm_payment")
            policy.status = new_status

        record_audit_event(
            session=session,
            user_id=actor_id,
            action="policy.payment_recorded",
            entity_type="policy",
            entity_id=policy.id,
            before_state={
                "paid_premium": float(policy.paid_premium - amount),
                "status": old_status,
            },
            after_state={"paid_premium": float(policy.paid_premium), "status": policy.status},
        )
        session.commit()
        session.refresh(policy)
        return policy

    def cancel_policy(
        self,
        session: Session,
        policy_id: str,
        cancellation_date: date,
        reason: str,
        has_prior_claims: bool = False,
        actor_id: str = "system",
    ) -> tuple[Policy, RefundCalculation]:
        """Executes Process P06: deterministic pro-rata refund and policy cancellation."""
        policy = session.get(Policy, policy_id)
        if not policy:
            raise InsurAIException(
                status_code=404, title="Policy Not Found", detail=f"Policy '{policy_id}' not found."
            )

        # Calculate refund
        calc = calculate_cancellation_refund(
            start_date=policy.start_date,
            end_date=policy.end_date,
            cancellation_date=cancellation_date,
            total_premium=policy.total_premium,
            paid_premium=policy.paid_premium,
            has_prior_claims=has_prior_claims,
        )

        old_status = policy.status
        new_status = POLICY_WORKFLOW.trigger(policy.status, "cancel_policy")
        policy.status = new_status
        policy.cancellation_date = cancellation_date
        policy.cancellation_reason = reason
        policy.refund_amount = calc.net_refund

        publish_outbox_event(
            session=session,
            event_type="PolicyCancelled",
            aggregate_type="policy",
            aggregate_id=policy.id,
            payload={
                "policy_number": policy.policy_number,
                "cancellation_date": cancellation_date.isoformat(),
                "refund_amount": float(calc.net_refund),
                "requires_approval": calc.requires_manager_approval,
            },
        )
        record_audit_event(
            session=session,
            user_id=actor_id,
            action="policy.cancelled",
            entity_type="policy",
            entity_id=policy.id,
            before_state={"status": old_status},
            after_state={"status": new_status, "refund": float(calc.net_refund)},
        )
        session.commit()
        session.refresh(policy)
        return policy, calc

    def check_policy_active(
        self,
        session: Session,
        policy_number: str,
        incident_date: date,
    ) -> PolicyStatusReport:
        """
        Policy status checker engine used by Claims Triage Agent A4.
        Verifies policy existence, active status, and date-in-force.
        """
        policy = session.scalars(
            select(Policy).where(Policy.policy_number == policy_number)
        ).first()
        if not policy:
            return PolicyStatusReport(
                exists=False,
                is_active=False,
                in_force=False,
                policy_id=None,
                policy_number=policy_number,
                product_code=None,
                product_version_id=None,
                sum_insured=None,
                deductible=None,
                reasons=[f"Policy '{policy_number}' was not found in records."],
            )

        reasons: list[str] = []
        is_active = policy.status == "active"
        if not is_active:
            reasons.append(f"Policy status is '{policy.status}', not 'active'.")

        in_force = policy.start_date <= incident_date <= policy.end_date
        if not in_force:
            if incident_date < policy.start_date:
                reasons.append(
                    f"Incident date {incident_date} occurred prior to inception {policy.start_date}."
                )
            elif incident_date > policy.end_date:
                reasons.append(
                    f"Incident date {incident_date} occurred after policy expiration {policy.end_date}."
                )

        if is_active and in_force:
            reasons.append("Policy is verified active and valid for the specified incident date.")

        return PolicyStatusReport(
            exists=True,
            is_active=is_active,
            in_force=in_force,
            policy_id=policy.id,
            policy_number=policy.policy_number,
            product_code=policy.product_code,
            product_version_id=policy.product_version_id,
            sum_insured=policy.sum_insured,
            deductible=policy.deductible,
            reasons=reasons,
        )


policy_service = PolicyService()
