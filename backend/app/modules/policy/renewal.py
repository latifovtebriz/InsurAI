"""Policy renewal review, re-rating, statutory notice enforcement, and renewal workflow."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.modules.platform.public import publish_outbox_event, record_audit_event
from app.modules.policy.models import Policy, RenewalCase
from app.modules.policy.rating import quantize_money
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(UTC)


class RenewalService:
    """Automated renewal scanner and case management enforcing statutory notice deadlines."""

    def scan_expiring_policies(
        self,
        session: Session,
        as_of_date: date | None = None,
        days_ahead: int = 60,
    ) -> list[RenewalCase]:
        """
        Scans policies expiring within T-60 days.
        Evaluates claims frequency and severity during term, re-rates premium,
        and enforces statutory 30-day non-renewal notice deadlines.
        """
        current_date = as_of_date or datetime.now(UTC).date()
        cutoff_date = current_date + timedelta(days=days_ahead)

        stmt = select(Policy).where(
            Policy.status.in_(["active", "bound"]),
            Policy.end_date <= cutoff_date,
            Policy.end_date >= current_date,
        )
        expiring_policies = session.scalars(stmt).all()
        cases: list[RenewalCase] = []

        for policy in expiring_policies:
            # Check existing renewal case
            existing = session.scalars(
                select(RenewalCase).where(RenewalCase.policy_id == policy.id)
            ).first()

            days_to_expiry = (policy.end_date - current_date).days
            notice_deadline = policy.end_date - timedelta(days=30)

            # Query claim history during policy period
            from app.modules.claims.public import Claim

            claims_stmt = select(
                func.count(Claim.id),
                func.coalesce(func.sum(Claim.claimed_amount), Decimal("0.00")),
            ).where(
                Claim.policy_id == policy.id,
                Claim.status != "rejected",
            )
            claims_res = session.execute(claims_stmt).first()
            claims_count = int(claims_res[0] if claims_res else 0)
            claims_incurred = quantize_money(claims_res[1] if claims_res else Decimal("0.00"))

            # Calculate proposed premium and segmentation
            if claims_count == 0:
                recommendation = "STANDARD_RENEWAL"
                # 5% No-Claims Discount (NCD)
                discount_multiplier = Decimal("0.95")
                proposed_prem = quantize_money(policy.total_premium * discount_multiplier)
            elif claims_count == 1:
                recommendation = "SURCHARGED_RENEWAL"
                # 15% claim surcharge
                surcharge_multiplier = Decimal("1.15")
                proposed_prem = quantize_money(policy.total_premium * surcharge_multiplier)
            else:
                recommendation = "NON_RENEWAL"
                proposed_prem = quantize_money(policy.total_premium * Decimal("1.50"))

            # Statutory notice deadline check (Article 30-day notice rule)
            # If recommendation is NON_RENEWAL and days_to_expiry <= 30 without notice sent:
            deadline_breached = False
            if recommendation == "NON_RENEWAL" and current_date >= notice_deadline:
                deadline_breached = True

            if existing:
                # Update existing case metrics
                existing.days_to_expiry = days_to_expiry
                existing.claims_count = claims_count
                existing.total_claims_incurred = claims_incurred
                existing.proposed_premium = proposed_prem
                existing.recommendation = recommendation
                existing.statutory_deadline_breached = (
                    deadline_breached and not existing.notice_sent
                )
                cases.append(existing)
            else:
                new_case = RenewalCase(
                    policy_id=policy.id,
                    policy_number=policy.policy_number,
                    party_id=policy.party_id,
                    product_code=policy.product_code,
                    current_end_date=policy.end_date,
                    days_to_expiry=days_to_expiry,
                    claims_count=claims_count,
                    total_claims_incurred=claims_incurred,
                    current_premium=policy.total_premium,
                    proposed_premium=proposed_prem,
                    recommendation=recommendation,
                    status="pending_review",
                    notice_deadline=notice_deadline,
                    notice_sent=False,
                    statutory_deadline_breached=deadline_breached,
                    advisor_rationale=(
                        f"Automated T-60 review: {claims_count} claim(s) incurred totaling {claims_incurred} AZN. "
                        f"Recommendation: {recommendation}."
                    ),
                )
                session.add(new_case)
                cases.append(new_case)

        session.flush()
        return cases

    def generate_renewal_offer(
        self,
        session: Session,
        renewal_case_id: str,
        user_id: str | None = None,
    ) -> RenewalCase:
        """Issues renewal quotation offer to the policyholder."""
        case = session.get(RenewalCase, renewal_case_id)
        if not case:
            raise ValueError(f"Renewal case '{renewal_case_id}' not found.")

        case.status = "offer_generated"
        case.notice_sent = True
        case.statutory_deadline_breached = False

        record_audit_event(
            session=session,
            action="renewal_offer_generated",
            entity_type="renewal_case",
            entity_id=case.id,
            after_state={
                "policy_number": case.policy_number,
                "proposed_premium": str(case.proposed_premium),
                "recommendation": case.recommendation,
            },
            user_id=user_id,
        )

        publish_outbox_event(
            session=session,
            event_type="RenewalOfferGeneratedEvent",
            aggregate_type="renewal_case",
            aggregate_id=case.id,
            payload={
                "policy_number": case.policy_number,
                "proposed_premium": str(case.proposed_premium),
                "days_to_expiry": case.days_to_expiry,
            },
        )

        session.flush()
        return case

    def issue_non_renewal_notice(
        self,
        session: Session,
        renewal_case_id: str,
        rationale: str,
        underwriter_name: str,
        user_id: str | None = None,
    ) -> RenewalCase:
        """
        Issues statutory non-renewal notice. Requires underwriter sign-off (L2 governance).
        """
        case = session.get(RenewalCase, renewal_case_id)
        if not case:
            raise ValueError(f"Renewal case '{renewal_case_id}' not found.")

        case.status = "non_renewal_alert"
        case.notice_sent = True
        case.underwriter_approved = True
        case.approved_by = underwriter_name
        case.advisor_rationale = rationale
        case.statutory_deadline_breached = False

        record_audit_event(
            session=session,
            action="non_renewal_notice_issued",
            entity_type="renewal_case",
            entity_id=case.id,
            after_state={
                "policy_number": case.policy_number,
                "approved_by": underwriter_name,
                "rationale": rationale,
            },
            user_id=user_id,
        )

        publish_outbox_event(
            session=session,
            event_type="NonRenewalNoticeIssuedEvent",
            aggregate_type="renewal_case",
            aggregate_id=case.id,
            payload={
                "policy_number": case.policy_number,
                "approved_by": underwriter_name,
                "rationale": rationale,
            },
        )

        session.flush()
        return case

    def accept_renewal(
        self,
        session: Session,
        renewal_case_id: str,
        user_id: str | None = None,
    ) -> Policy:
        """Customer accepts renewal offer: creates renewed policy contract for next annual term."""
        case = session.get(RenewalCase, renewal_case_id)
        if not case:
            raise ValueError(f"Renewal case '{renewal_case_id}' not found.")

        old_policy = session.get(Policy, case.policy_id)
        if not old_policy:
            raise ValueError(f"Original policy '{case.policy_id}' not found.")

        new_start = old_policy.end_date
        new_end = new_start + timedelta(days=365)
        new_policy_num = f"{old_policy.policy_number}-R01"

        renewed_policy = Policy(
            policy_number=new_policy_num,
            party_id=old_policy.party_id,
            asset_id=old_policy.asset_id,
            product_code=old_policy.product_code,
            product_version_id=old_policy.product_version_id,
            status="pending_payment",
            start_date=new_start,
            end_date=new_end,
            sum_insured=old_policy.sum_insured,
            deductible=old_policy.deductible,
            total_premium=case.proposed_premium,
            paid_premium=Decimal("0.00"),
            payment_schedule=[
                {
                    "installment_number": 1,
                    "due_date": new_start.isoformat(),
                    "amount": str(case.proposed_premium),
                }
            ],
        )
        session.add(renewed_policy)
        session.flush()

        case.status = "accepted"

        record_audit_event(
            session=session,
            action="policy_renewed",
            entity_type="policy",
            entity_id=renewed_policy.id,
            after_state={
                "old_policy_number": old_policy.policy_number,
                "renewed_policy_number": renewed_policy.policy_number,
                "premium": str(case.proposed_premium),
            },
            user_id=user_id,
        )

        publish_outbox_event(
            session=session,
            event_type="PolicyRenewedEvent",
            aggregate_type="policy",
            aggregate_id=renewed_policy.id,
            payload={
                "renewed_policy_number": renewed_policy.policy_number,
                "original_policy_number": old_policy.policy_number,
                "total_premium": str(case.proposed_premium),
            },
        )

        session.flush()
        return renewed_policy


renewal_service = RenewalService()
