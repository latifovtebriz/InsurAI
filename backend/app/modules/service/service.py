"""Customer service and complaint SLA management service."""

import uuid
from datetime import UTC, date, datetime, timedelta

from app.modules.platform.public import publish_outbox_event, record_audit_event
from app.modules.policy.public import Policy
from app.modules.service.models import Complaint, EndorsementDraft
from sqlalchemy import select
from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(UTC)


class CustomerServiceDomain:
    """Manages customer complaints with statutory SLA countdown and endorsement approvals."""

    def register_complaint(
        self,
        session: Session,
        party_id: str,
        subject: str,
        description: str,
        policy_id: str | None = None,
        claim_id: str | None = None,
        as_of_date: date | None = None,
        user_id: str | None = None,
    ) -> Complaint:
        """
        Registers formal customer complaint enforcing statutory SLA deadlines:
        - 5-day initial response deadline
        - 15-day final resolution deadline
        """
        start_d = as_of_date or datetime.now(UTC).date()
        init_deadline = start_d + timedelta(days=5)
        final_deadline = start_d + timedelta(days=15)

        random_suffix = uuid.uuid4().hex[:6].upper()
        cmp_num = f"CMPL-{start_d.strftime('%Y%m%d')}-{random_suffix}"

        complaint = Complaint(
            complaint_number=cmp_num,
            party_id=party_id,
            policy_id=policy_id,
            claim_id=claim_id,
            subject=subject,
            description=description,
            status="received",
            initial_response_deadline=init_deadline,
            final_resolution_deadline=final_deadline,
            sla_breached=False,
        )
        session.add(complaint)
        session.flush()

        record_audit_event(
            session=session,
            action="complaint_registered",
            entity_type="complaint",
            entity_id=complaint.id,
            after_state={
                "complaint_number": complaint.complaint_number,
                "initial_deadline": init_deadline.isoformat(),
                "final_deadline": final_deadline.isoformat(),
            },
            user_id=user_id,
        )

        publish_outbox_event(
            session=session,
            event_type="ComplaintRegisteredEvent",
            aggregate_type="complaint",
            aggregate_id=complaint.id,
            payload={
                "complaint_number": complaint.complaint_number,
                "party_id": party_id,
                "subject": subject,
            },
        )

        session.flush()
        return complaint

    def check_complaint_slas(
        self,
        session: Session,
        as_of_date: date | None = None,
    ) -> list[Complaint]:
        """Scans active complaints and flags statutory SLA breaches."""
        check_d = as_of_date or datetime.now(UTC).date()
        stmt = select(Complaint).where(
            Complaint.status.in_(["received", "under_investigation"]),
        )
        complaints = session.scalars(stmt).all()
        breached: list[Complaint] = []

        for c in complaints:
            if c.final_resolution_deadline < check_d:
                c.sla_breached = True
                c.status = "escalated_to_ombudsman"
                breached.append(c)

        session.flush()
        return breached

    def approve_endorsement(
        self,
        session: Session,
        draft_id: str,
        underwriter_name: str,
        user_id: str | None = None,
    ) -> EndorsementDraft:
        """Approves and applies endorsement draft to policy contract."""
        draft = session.get(EndorsementDraft, draft_id)
        if not draft:
            raise ValueError(f"Endorsement draft '{draft_id}' not found.")

        draft.status = "approved"
        draft.approved_by = underwriter_name

        policy = session.get(Policy, draft.policy_id)
        if policy and "new_sum_insured" in draft.proposed_changes:
            from decimal import Decimal

            policy.sum_insured = Decimal(str(draft.proposed_changes["new_sum_insured"]))
            policy.total_premium = policy.total_premium + draft.prorata_premium_adjustment

        record_audit_event(
            session=session,
            action="endorsement_applied",
            entity_type="policy",
            entity_id=draft.policy_id,
            after_state={
                "draft_number": draft.draft_number,
                "endorsement_type": draft.endorsement_type,
                "approved_by": underwriter_name,
            },
            user_id=user_id,
        )

        session.flush()
        return draft


customer_service_domain = CustomerServiceDomain()
