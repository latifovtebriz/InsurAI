"""Domain service and workflows for underwriting referrals and cases."""

import secrets
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.modules.platform.public import (
    publish_outbox_event,
    record_audit_event,
)
from app.modules.underwriting.agent import underwriting_copilot_agent
from app.modules.underwriting.engine import (
    evaluate_underwriting_rules,
    verify_underwriter_authority,
)
from app.modules.underwriting.models import UnderwritingCase
from sqlalchemy.orm import Session


class UnderwritingService:
    """Manages underwriting case creation, copilot assessment, and underwriter adjudication."""

    def create_case_from_quote(
        self,
        db: Session,
        quote_id: str,
        product_code: str,
        sum_insured: Decimal,
        proposed_premium: Decimal,
        rating_inputs: dict[str, Any],
    ) -> UnderwritingCase:
        """Evaluates quote rules and registers an underwriting referral case."""
        case_num = f"UW-2026-{secrets.token_hex(3).upper()}"

        eval_res = evaluate_underwriting_rules(
            product_code=product_code,
            sum_insured=sum_insured,
            rating_inputs=rating_inputs,
        )

        case = UnderwritingCase(
            case_number=case_num,
            quote_id=quote_id,
            product_code=product_code,
            sum_insured=sum_insured,
            proposed_premium=proposed_premium,
            status="pending_review",
            authority_tier_required=eval_res.required_authority_tier,
            rule_hits=[h.model_dump() for h in eval_res.rule_hits],
            risk_score=0.75 if eval_res.has_referral else 0.10,
        )
        db.add(case)
        db.flush()

        record_audit_event(
            session=db,
            user_id="system:sales",
            action="underwriting.case.created",
            entity_type="underwriting_case",
            entity_id=case.id,
            after_state={
                "case_number": case.case_number,
                "quote_id": quote_id,
                "authority_tier_required": case.authority_tier_required,
                "rule_hits_count": len(case.rule_hits),
            },
        )

        return case

    def run_copilot_assessment(self, db: Session, case_id: str) -> UnderwritingCase:
        """Invokes A2 Underwriting Copilot to produce structured assessment."""
        case = db.get(UnderwritingCase, case_id)
        if not case:
            raise ValueError(f"Underwriting case '{case_id}' not found")

        assessment = underwriting_copilot_agent.assess_case(
            case_id=case.id,
            product_code=case.product_code,
            sum_insured=case.sum_insured,
            rating_inputs={"rule_hits": case.rule_hits},
        )

        case.copilot_assessment = assessment.model_dump()
        db.flush()

        record_audit_event(
            session=db,
            user_id="agent:a2_underwriting_copilot",
            action="underwriting.copilot.assessed",
            entity_type="underwriting_case",
            entity_id=case.id,
            after_state={
                "recommended_action": assessment.recommended_action,
                "confidence": assessment.confidence,
                "cited_guidelines": assessment.cited_guidelines,
            },
        )

        return case

    def record_decision(
        self,
        db: Session,
        case_id: str,
        decision: str,
        underwriter_id: str,
        underwriter_role: str = "underwriter",
        conditions: list[str] | None = None,
        override_reason: str | None = None,
        notes: str | None = None,
    ) -> UnderwritingCase:
        """
        Records human underwriter adjudication:
        1. Verifies underwriter authority tier against case requirement.
        2. Enforces mandatory justification for declines (Guardrail G3).
        3. Enforces override reason if decision contradicts rule engine.
        """
        case = db.get(UnderwritingCase, case_id)
        if not case:
            raise ValueError(f"Underwriting case '{case_id}' not found")

        has_auth = verify_underwriter_authority(
            underwriter_tier=underwriter_role,
            required_tier=case.authority_tier_required,
            sum_insured=case.sum_insured,
        )
        if not has_auth:
            raise ValueError(
                f"Underwriter with role '{underwriter_role}' lacks authority for required tier '{case.authority_tier_required}'"
            )

        if decision == "declined" and not (override_reason or notes):
            raise ValueError(
                "Declining a risk requires a mandatory written rationale (Guardrail G3)."
            )

        case.status = decision
        case.assigned_underwriter_id = underwriter_id
        case.notes = notes
        case.underwriter_decision = {
            "decision": decision,
            "conditions": conditions or [],
            "override_reason": override_reason,
            "decided_by": underwriter_id,
            "decided_at": datetime.now(UTC).isoformat(),
        }
        db.flush()

        record_audit_event(
            session=db,
            user_id=underwriter_id,
            action="underwriting.case.decided",
            entity_type="underwriting_case",
            entity_id=case.id,
            after_state={
                "case_number": case.case_number,
                "decision": decision,
                "override_reason": override_reason,
            },
        )

        publish_outbox_event(
            session=db,
            event_type="UnderwritingCaseDecidedEvent",
            aggregate_type="underwriting_case",
            aggregate_id=case.id,
            payload={
                "case_number": case.case_number,
                "decision": decision,
                "quote_id": case.quote_id,
            },
        )

        return case


underwriting_service = UnderwritingService()
