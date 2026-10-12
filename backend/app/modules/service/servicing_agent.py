"""Agent A3: Policy Servicing Assistant for endorsements and mid-term changes (P06)."""

import uuid
from datetime import date
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
from app.modules.policy.public import Policy, quantize_money
from app.modules.service.models import EndorsementDraft
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session


class GetPolicyDetailsArgs(BaseModel):
    policy_number: str = Field(description="Policy number to review")


class CalculateProrataArgs(BaseModel):
    policy_number: str = Field(description="Policy number")
    new_sum_insured: float = Field(description="Updated vehicle/property valuation in AZN")
    effective_date: str = Field(description="ISO effective date YYYY-MM-DD")


class ProposeEndorsementArgs(BaseModel):
    policy_number: str = Field(description="Policy number")
    endorsement_type: str = Field(description="ADD_DRIVER, INCREASE_SUM_INSURED, ADDRESS_CHANGE")
    changes: dict[str, Any] = Field(description="Dictionary of requested parameter changes")
    premium_adjustment: float = Field(description="Prorated additional or return premium")


class EndorsementDraftResult(BaseModel):
    policy_number: str
    endorsement_type: str
    effective_date: str
    prorata_adjustment_azn: float
    proposed_changes: dict[str, Any]
    draft_status: str
    autonomy_level: str
    requires_underwriter_approval: bool
    summary_explanation: str


class PolicyServicingAgent:
    """Agent A3: Policy Servicing Assistant handling mid-term policy changes and endorsement drafting."""

    def __init__(self, guardrails: GuardrailPipeline = guardrail_pipeline) -> None:
        self.guardrails = guardrails
        self.tool_registry = ToolRegistry()

    def register_tools(self, session: Session) -> None:
        def _policy_handler(args: GetPolicyDetailsArgs) -> dict[str, Any]:
            policy = session.scalars(
                select(Policy).where(Policy.policy_number == args.policy_number)
            ).first()
            if not policy:
                return {"error": f"Policy '{args.policy_number}' not found."}
            return {
                "policy_number": policy.policy_number,
                "product_code": policy.product_code,
                "status": policy.status,
                "sum_insured": float(policy.sum_insured),
                "total_premium": float(policy.total_premium),
                "start_date": policy.start_date.isoformat(),
                "end_date": policy.end_date.isoformat(),
            }

        def _prorata_handler(args: CalculateProrataArgs) -> dict[str, Any]:
            policy = session.scalars(
                select(Policy).where(Policy.policy_number == args.policy_number)
            ).first()
            if not policy:
                return {"error": "Policy not found"}

            eff_d = date.fromisoformat(args.effective_date)
            remaining_days = max(0, (policy.end_date - eff_d).days)
            total_days = max(1, (policy.end_date - policy.start_date).days)
            remaining_fraction = Decimal(str(remaining_days)) / Decimal(str(total_days))

            # Additional sum insured creates proportional additional premium
            delta_val = Decimal(str(args.new_sum_insured)) - policy.sum_insured
            if delta_val <= Decimal("0.00"):
                additional_prem = Decimal("0.00")
            else:
                annual_rate = policy.total_premium / policy.sum_insured
                additional_prem = quantize_money(delta_val * annual_rate * remaining_fraction)

            return {
                "policy_number": args.policy_number,
                "remaining_days": remaining_days,
                "prorata_additional_premium": float(additional_prem),
            }

        def _propose_handler(args: ProposeEndorsementArgs) -> dict[str, Any]:
            return {
                "policy_number": args.policy_number,
                "endorsement_type": args.endorsement_type,
                "adjustment": args.premium_adjustment,
                "status": "draft_created",
            }

        self.tool_registry.register(
            ToolDefinition(
                name="get_policy_details",
                description="Retrieves current policy parameters, term dates, and premium.",
                parameters_schema=GetPolicyDetailsArgs,
                category=ToolCategory.READ,
                handler=_policy_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="calculate_prorata",
                description="Calculates exact pro-rata premium adjustment down to remaining term days.",
                parameters_schema=CalculateProrataArgs,
                category=ToolCategory.READ,
                handler=_prorata_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="propose_endorsement",
                description="Drafts endorsement record for underwriter adjudication.",
                parameters_schema=ProposeEndorsementArgs,
                category=ToolCategory.PROPOSE,
                handler=_propose_handler,
            )
        )

    def process_endorsement_request(
        self,
        session: Session,
        policy_number: str,
        endorsement_type: str,
        changes: dict[str, Any],
        effective_date: str,
    ) -> EndorsementDraftResult:
        """
        Drafts endorsement change, calculates pro-rata adjustment, and prepares underwriter proposal.
        """
        # Guardrail G7
        for v in changes.values():
            if isinstance(v, str) and gateway.detect_prompt_injection(v):
                raise ValueError(
                    "Prompt injection attempt detected in endorsement parameter payload."
                )

        self.register_tools(session)

        policy = session.scalars(
            select(Policy).where(Policy.policy_number == policy_number)
        ).first()
        if not policy:
            raise ValueError(f"Policy '{policy_number}' not found.")

        prorata_tool = self.tool_registry.get("calculate_prorata")
        new_val = float(changes.get("new_sum_insured", float(policy.sum_insured)))
        prorata_res = (
            prorata_tool.execute(
                {
                    "policy_number": policy_number,
                    "new_sum_insured": new_val,
                    "effective_date": effective_date,
                }
            )
            if prorata_tool
            else {}
        )

        adj_amt = prorata_res.get("prorata_additional_premium", 0.0)

        # Persist EndorsementDraft in DB
        eff_date_val = date.fromisoformat(effective_date)
        random_suffix = uuid.uuid4().hex[:6].upper()
        draft = EndorsementDraft(
            draft_number=f"END-{policy_number[-6:]}-{endorsement_type[:4]}-{random_suffix}",
            policy_id=policy.id,
            policy_number=policy.policy_number,
            endorsement_type=endorsement_type,
            effective_date=eff_date_val,
            proposed_changes=changes,
            prorata_premium_adjustment=quantize_money(Decimal(str(adj_amt))),
            status="draft",
        )
        session.add(draft)
        session.flush()

        explanation = (
            f"Endorsement {endorsement_type} drafted for policy {policy_number}. "
            f"Effective date: {effective_date}. "
            f"Calculated pro-rata additional premium: {adj_amt:.2f} AZN. "
            f"Underwriter sign-off required prior to policy update."
        )

        return EndorsementDraftResult(
            policy_number=policy_number,
            endorsement_type=endorsement_type,
            effective_date=effective_date,
            prorata_adjustment_azn=adj_amt,
            proposed_changes=changes,
            draft_status="draft",
            autonomy_level="L2",
            requires_underwriter_approval=True,
            summary_explanation=explanation,
        )


policy_servicing_agent = PolicyServicingAgent()
