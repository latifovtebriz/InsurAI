"""Domain services and workflows for sales, leads, and quotations."""

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.modules.platform.public import (
    publish_outbox_event,
    record_audit_event,
)
from app.modules.policy.public import (
    RatingBreakdown,
    calculate_home_premium,
    calculate_motor_od_premium,
    calculate_motor_tpl_premium,
    generate_installment_schedule,
)
from app.modules.sales.models import Lead, Quote
from sqlalchemy import select
from sqlalchemy.orm import Session


def check_kyc_lite_status(
    tax_id: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> dict[str, Any]:
    """
    KYC-lite screening hook (stub interface for Phase 9, full screening arrives in Phase 11).
    Performs deterministic format validation and blocklist mock checks.
    """
    if tax_id and "BLOCK" in tax_id.upper():
        return {
            "passed": False,
            "status": "requires_screening",
            "details": f"Tax ID {tax_id} flagged for compliance review.",
        }

    return {
        "passed": True,
        "status": "verified_lite",
        "details": "KYC-lite pre-bind checks passed successfully.",
    }


class SalesService:
    """Manages lead generation, rating calculation, and quote lifecycle."""

    def create_lead(
        self,
        db: Session,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        product_code: str,
        channel: str = "web",
        notes: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> Lead:
        """Captures a prospective customer lead."""
        lead_num = f"LEAD-2026-{secrets.token_hex(3).upper()}"
        lead = Lead(
            lead_number=lead_num,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            product_code=product_code,
            channel=channel,
            status="new",
            notes=notes,
            extra_data=extra_data or {},
        )
        db.add(lead)
        db.flush()
        return lead

    def generate_quote(
        self,
        db: Session,
        product_code: str,
        rating_inputs: dict[str, Any],
        lead_id: str | None = None,
        party_id: str | None = None,
    ) -> Quote:
        """
        Executes deterministic rating engine and generates an itemized Quote valid for 30 days.
        """
        code = product_code.upper()
        breakdown_obj: RatingBreakdown

        if code == "MOTOR_OD":
            sum_insured = Decimal(str(rating_inputs.get("vehicle_value", 30000)))
            deductible = Decimal(str(rating_inputs.get("deductible", 200)))
            v_age = int(rating_inputs.get("vehicle_age", 3))
            d_age = int(rating_inputs.get("driver_age", 30))
            prior_claims = int(rating_inputs.get("prior_claims_count", 0))

            breakdown_obj = calculate_motor_od_premium(
                sum_insured=sum_insured,
                driver_age=d_age,
                vehicle_age=v_age,
                prior_claims_count=prior_claims,
            )
        elif code == "MOTOR_TPL":
            deductible = Decimal("0.00")
            engine_cc = int(rating_inputs.get("engine_displacement_cc", 1800))
            prior_claims = int(rating_inputs.get("prior_claims_count", 0))

            breakdown_obj = calculate_motor_tpl_premium(
                engine_capacity_cc=engine_cc,
                prior_claims_count=prior_claims,
            )
            sum_insured = breakdown_obj.sum_insured
        elif code == "HOME":
            sum_insured = Decimal(str(rating_inputs.get("property_value", 150000)))
            deductible = Decimal(str(rating_inputs.get("deductible", 500)))
            construction_type = str(
                rating_inputs.get("construction_type", rating_inputs.get("wall_type", "stone"))
            )
            build_year = int(rating_inputs.get("build_year", 2010))

            breakdown_obj = calculate_home_premium(
                sum_insured=sum_insured,
                construction_type=construction_type,
                build_year=build_year,
            )
        else:
            raise ValueError(f"Unsupported product code for rating: '{product_code}'")

        breakdown = {
            "product_code": breakdown_obj.product_code,
            "base_premium": float(breakdown_obj.base_premium),
            "final_premium": float(breakdown_obj.final_premium),
            "subtotal": float(breakdown_obj.subtotal),
            "minimum_premium": float(breakdown_obj.minimum_premium),
            "total_payable": float(breakdown_obj.final_premium),
            "factors_applied": [
                {
                    "name": f.factor_name,
                    "multiplier": float(f.multiplier),
                    "reason": f.description,
                }
                for f in breakdown_obj.applied_factors
            ],
        }

        today = datetime.now(UTC).date()
        annual_sched = generate_installment_schedule(
            total_premium=breakdown_obj.final_premium,
            installments_count=1,
            start_date=today,
        )
        quarterly_sched = generate_installment_schedule(
            total_premium=breakdown_obj.final_premium,
            installments_count=4,
            start_date=today,
        )

        installment_options = [
            {
                "plan": "annual_lump_sum",
                "installments_count": 1,
                "schedule": [
                    {
                        "seq": inst.installment_number,
                        "due_date": inst.due_date.isoformat(),
                        "amount": float(inst.amount),
                    }
                    for inst in annual_sched
                ],
            },
            {
                "plan": "quarterly_installments",
                "installments_count": 4,
                "schedule": [
                    {
                        "seq": inst.installment_number,
                        "due_date": inst.due_date.isoformat(),
                        "amount": float(inst.amount),
                    }
                    for inst in quarterly_sched
                ],
            },
        ]

        quote_num = f"QTE-2026-{secrets.token_hex(3).upper()}"
        from datetime import timedelta

        valid_until = today + timedelta(days=30)

        quote = Quote(
            quote_number=quote_num,
            lead_id=lead_id,
            party_id=party_id,
            product_code=code,
            status="offered",
            sum_insured=sum_insured,
            deductible=deductible,
            total_premium=breakdown_obj.final_premium,
            rating_inputs=rating_inputs,
            breakdown=breakdown,
            installment_options=installment_options,
            valid_until=valid_until,
        )
        db.add(quote)
        db.flush()

        # Audit
        record_audit_event(
            session=db,
            user_id="system:sales",
            action="sales.quote.created",
            entity_type="quote",
            entity_id=quote.id,
            after_state={
                "quote_number": quote.quote_number,
                "product_code": quote.product_code,
                "total_premium": float(quote.total_premium),
                "sum_insured": float(quote.sum_insured),
            },
        )

        # Outbox
        publish_outbox_event(
            session=db,
            event_type="QuoteCreatedEvent",
            aggregate_type="quote",
            aggregate_id=quote.id,
            payload={
                "quote_number": quote.quote_number,
                "product_code": quote.product_code,
                "total_premium": float(quote.total_premium),
            },
        )

        return quote

    def accept_quote(self, db: Session, quote_id: str, actor_id: str = "customer") -> Quote:
        """Customer accepts quote; verifies validity date and KYC-lite before confirming acceptance."""
        quote = db.get(Quote, quote_id)
        if not quote:
            stmt = select(Quote).where(Quote.quote_number == quote_id)
            quote = db.scalars(stmt).first()
            if not quote:
                raise ValueError(f"Quote '{quote_id}' not found")

        if quote.status not in ["offered", "approved_by_uw"]:
            raise ValueError(
                f"Quote {quote.quote_number} is in status '{quote.status}', cannot accept."
            )

        if quote.valid_until < datetime.now(UTC).date():
            quote.status = "expired"
            db.flush()
            raise ValueError(f"Quote {quote.quote_number} expired on {quote.valid_until}.")

        kyc = check_kyc_lite_status()
        if not kyc["passed"]:
            raise ValueError(f"KYC-lite pre-bind failed: {kyc['details']}")

        quote.status = "accepted"
        db.flush()

        record_audit_event(
            session=db,
            user_id=actor_id,
            action="sales.quote.accepted",
            entity_type="quote",
            entity_id=quote.id,
            after_state={"quote_number": quote.quote_number, "status": quote.status},
        )

        publish_outbox_event(
            session=db,
            event_type="QuoteAcceptedEvent",
            aggregate_type="quote",
            aggregate_id=quote.id,
            payload={
                "quote_number": quote.quote_number,
                "total_premium": float(quote.total_premium),
            },
        )

        return quote

    def refer_to_underwriting(
        self,
        db: Session,
        quote_id: str,
        reason: str,
        uw_case_id: str | None = None,
    ) -> Quote:
        """Transitions quote status to referred_to_uw when underwriting triggers hit."""
        quote = db.get(Quote, quote_id)
        if not quote:
            raise ValueError(f"Quote '{quote_id}' not found")

        quote.status = "referred_to_uw"
        if uw_case_id:
            quote.underwriting_case_id = uw_case_id
        db.flush()

        record_audit_event(
            session=db,
            user_id="system:underwriting_engine",
            action="sales.quote.referred",
            entity_type="quote",
            entity_id=quote.id,
            after_state={"quote_number": quote.quote_number, "referral_reason": reason},
        )
        return quote


sales_service = SalesService()
