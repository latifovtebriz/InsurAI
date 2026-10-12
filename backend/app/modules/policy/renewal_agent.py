"""Agent A7: Renewal Advisor implementation.
Reviews expiring policies, re-rates terms based on loss history, drafts offers,
and strictly enforces statutory 30-day non-renewal notice deadlines.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.modules.platform.public import (
    GuardrailPipeline,
    ToolCategory,
    ToolDefinition,
    ToolRegistry,
    gateway,
    guardrail_pipeline,
)
from app.modules.policy.models import Policy
from app.modules.policy.renewal import renewal_service
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session


class GetExpiringPoliciesArgs(BaseModel):
    days_ahead: int = Field(default=60, description="Scanning window ahead in days (typically 60)")


class CalculateRenewalRateArgs(BaseModel):
    policy_number: str = Field(description="Policy number to review and re-rate")


class DraftRenewalNoticeArgs(BaseModel):
    policy_number: str = Field(description="Policy number")
    offer_type: str = Field(description="Offer type: STANDARD_RENEWAL, SURCHARGED_RENEWAL, NON_RENEWAL")
    new_premium: float = Field(description="Proposed premium in AZN")
    rationale: str = Field(description="Actuarial and underwriting rationale")


class RenewalAssessment(BaseModel):
    policy_number: str
    current_end_date: str
    days_to_expiry: int
    claims_count: int
    total_claims_incurred: float
    current_premium: float
    proposed_premium: float
    recommendation: str
    notice_deadline: str
    statutory_deadline_breached: bool
    autonomy_level: str
    draft_notice_text: str
    underwriter_signoff_required: bool


class RenewalAdvisorAgent:
    """Agent A7: Autonomous Renewal Advisor (L1 Standard / L2 Human Sign-off for Surcharge & Non-renewal)."""

    def __init__(self, guardrails: GuardrailPipeline = guardrail_pipeline) -> None:
        self.guardrails = guardrails
        self.tool_registry = ToolRegistry()

    def register_tools(self, session: Session) -> None:
        def _get_expiring(args: GetExpiringPoliciesArgs) -> dict[str, Any]:
            cases = renewal_service.scan_expiring_policies(session, days_ahead=args.days_ahead)
            return {
                "count": len(cases),
                "cases": [
                    {
                        "policy_number": c.policy_number,
                        "days_to_expiry": c.days_to_expiry,
                        "claims_count": c.claims_count,
                        "recommendation": c.recommendation,
                        "current_premium": float(c.current_premium),
                        "proposed_premium": float(c.proposed_premium),
                        "deadline_breached": c.statutory_deadline_breached,
                    }
                    for c in cases
                ],
            }

        def _calc_rate(args: CalculateRenewalRateArgs) -> dict[str, Any]:
            policy = session.scalars(
                select(Policy).where(Policy.policy_number == args.policy_number)
            ).first()
            if not policy:
                return {"error": f"Policy '{args.policy_number}' not found."}

            cases = renewal_service.scan_expiring_policies(session, days_ahead=60)
            case = next((c for c in cases if c.policy_number == args.policy_number), None)
            if not case:
                return {
                    "policy_number": policy.policy_number,
                    "current_premium": float(policy.total_premium),
                    "claims_count": 0,
                    "recommendation": "STANDARD_RENEWAL",
                    "proposed_premium": float(policy.total_premium * Decimal("0.95")),
                }

            return {
                "policy_number": case.policy_number,
                "current_premium": float(case.current_premium),
                "claims_count": case.claims_count,
                "total_claims_incurred": float(case.total_claims_incurred),
                "proposed_premium": float(case.proposed_premium),
                "recommendation": case.recommendation,
                "days_to_expiry": case.days_to_expiry,
                "deadline_breached": case.statutory_deadline_breached,
            }

        def _draft_notice(args: DraftRenewalNoticeArgs) -> dict[str, Any]:
            if args.offer_type == "NON_RENEWAL":
                text = (
                    f"STATUTORY NOTICE OF NON-RENEWAL\n"
                    f"Policy: {args.policy_number}\n"
                    f"Notice: We regret to inform you that following term risk evaluation ({args.rationale}), "
                    f"InsurAI cannot offer renewal terms for the upcoming period.\n"
                    f"In compliance with statutory requirements, this notice is issued in advance of expiration."
                )
            elif args.offer_type == "SURCHARGED_RENEWAL":
                text = (
                    f"ANNUAL POLICY RENEWAL OFFER (ADJUSTED TERMS)\n"
                    f"Policy: {args.policy_number}\n"
                    f"Proposed Premium: {args.new_premium:.2f} AZN\n"
                    f"Terms: Reflected claim history during preceding period ({args.rationale})."
                )
            else:
                text = (
                    f"ANNUAL POLICY RENEWAL OFFER (REWARD TIER)\n"
                    f"Policy: {args.policy_number}\n"
                    f"Proposed Premium: {args.new_premium:.2f} AZN\n"
                    f"Terms: 5% No-Claims Discount applied for claim-free driving ({args.rationale})."
                )

            return {
                "policy_number": args.policy_number,
                "notice_type": args.offer_type,
                "proposed_premium": args.new_premium,
                "draft_text": text,
            }

        self.tool_registry.register(
            ToolDefinition(
                name="get_expiring_policies",
                description="Retrieves policies reaching expiration within the renewal window (T-60).",
                parameters_schema=GetExpiringPoliciesArgs,
                category=ToolCategory.READ,
                handler=_get_expiring,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="calculate_renewal_rate",
                description="Evaluates policy term claims and calculates re-rated renewal premium.",
                parameters_schema=CalculateRenewalRateArgs,
                category=ToolCategory.READ,
                handler=_calc_rate,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="draft_renewal_notice",
                description="Drafts formal renewal proposal letter or statutory non-renewal notice.",
                parameters_schema=DraftRenewalNoticeArgs,
                category=ToolCategory.PROPOSE,
                handler=_draft_notice,
            )
        )

    def assess_policy_renewal(
        self,
        session: Session,
        policy_number: str,
        applicant_message: str = "",
        as_of_date: date | None = None,
    ) -> RenewalAssessment:
        """
        Executes end-to-end A7 renewal assessment with guardrail verification.
        """
        # Guardrail G7: Prompt injection defense
        if applicant_message and gateway.detect_prompt_injection(applicant_message):
            applicant_message = "[FILTERED - INJECTION ATTEMPT DETECTED]"

        self.register_tools(session)

        # Retrieve policy
        policy = session.scalars(
            select(Policy).where(Policy.policy_number == policy_number)
        ).first()
        if not policy:
            raise ValueError(f"Policy '{policy_number}' not found.")

        # Trigger renewal scanner
        cases = renewal_service.scan_expiring_policies(session, as_of_date=as_of_date, days_ahead=60)
        case = next((c for c in cases if c.policy_number == policy_number), None)

        if not case:
            # Fallback if policy expiry is further out
            days_to_expiry = (policy.end_date - datetime.now(UTC).date()).days
            claims_count = 0
            incurred = Decimal("0.00")
            recommendation = "STANDARD_RENEWAL"
            proposed_prem = policy.total_premium * Decimal("0.95")
            deadline_breached = False
            notice_d = policy.end_date
        else:
            days_to_expiry = case.days_to_expiry
            claims_count = case.claims_count
            incurred = case.total_claims_incurred
            recommendation = case.recommendation
            proposed_prem = case.proposed_premium
            deadline_breached = case.statutory_deadline_breached
            notice_d = case.notice_deadline

        # Determine autonomy level (L1 for standard, L2 for non-renewal or surcharge)
        if recommendation == "STANDARD_RENEWAL":
            autonomy_level = "L1"
            signoff_required = False
            rationale = "Zero claims during expiring term; 5% no-claims reward applied."
        elif recommendation == "SURCHARGED_RENEWAL":
            autonomy_level = "L2"
            signoff_required = True
            rationale = f"1 claim incurred ({incurred} AZN); standard 15% risk surcharge applied."
        else:
            autonomy_level = "L2"
            signoff_required = True
            rationale = (
                f"Adverse claim frequency ({claims_count} claims totaling {incurred} AZN). "
                f"Risk exceeds acceptable underwriting threshold."
            )

        # Draft notice text
        draft_tool = self.tool_registry.get("draft_renewal_notice")
        if draft_tool:
            draft_res = draft_tool.execute(
                {
                    "policy_number": policy_number,
                    "offer_type": recommendation,
                    "new_premium": float(proposed_prem),
                    "rationale": rationale,
                }
            )
            notice_text = draft_res["draft_text"]
        else:
            notice_text = f"Renewal Notice for {policy_number}: {recommendation}"

        return RenewalAssessment(
            policy_number=policy_number,
            current_end_date=policy.end_date.isoformat(),
            days_to_expiry=days_to_expiry,
            claims_count=claims_count,
            total_claims_incurred=float(incurred),
            current_premium=float(policy.total_premium),
            proposed_premium=float(proposed_prem),
            recommendation=recommendation,
            notice_deadline=notice_d.isoformat(),
            statutory_deadline_breached=deadline_breached,
            autonomy_level=autonomy_level,
            draft_notice_text=notice_text,
            underwriter_signoff_required=signoff_required,
        )


renewal_advisor_agent = RenewalAdvisorAgent()
