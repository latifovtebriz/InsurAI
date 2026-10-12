"""Agent A6: Customer Service Assistant with Identity Verification Gating."""

import re
from typing import Any

from app.modules.platform.public import (
    GuardrailPipeline,
    ToolCategory,
    ToolDefinition,
    ToolRegistry,
    gateway,
    guardrail_pipeline,
)
from app.modules.policy.public import Policy
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

FAQ_KNOWLEDGE_BASE = {
    "payment": "You can pay insurance premiums via online bank transfer, credit card, or at corporate partner branches in 1 lump sum or 4 equal installments.",
    "claim_reporting": "Per Clause C.2, traffic accidents must be reported within 3 business days from incident occurrence along with official police documentation.",
    "cancellation": "Policies can be cancelled mid-term with pro-rata premium refunds calculated strictly down to the exact day (Clause F.1), provided no claims occurred during the period.",
    "deductible": "The standard deductible (franshiza) is 200 AZN per claim incident under standard Motor Own Damage terms.",
    "contact": "InsurAI 24/7 Assistance Hotline: +994 12 555-0199 or email support@insurai.az.",
}


class VerifyCustomerArgs(BaseModel):
    identifier: str = Field(description="Phone number or registered email")
    tax_id: str = Field(description="National ID / FIN code / Tax ID")


class LookupFAQArgs(BaseModel):
    query: str = Field(description="General customer inquiry topic")


class GetCustomerPoliciesArgs(BaseModel):
    party_id: str = Field(description="Verified party UUID")


class CreateServiceTicketArgs(BaseModel):
    customer_identifier: str = Field(description="Customer phone or email")
    category: str = Field(
        description="Inquiry category: policy_info, billing, claim_status, complaint"
    )
    summary: str = Field(description="Customer issue summary")


class CustomerChatResponse(BaseModel):
    reply_text: str
    is_authenticated: bool
    verified_party_id: str | None = None
    data_accessed: bool = False
    action_taken: str | None = None


class CustomerServiceAgent:
    """Agent A6: Customer Service Assistant with strict identity verification gating."""

    def __init__(self, guardrails: GuardrailPipeline = guardrail_pipeline) -> None:
        self.guardrails = guardrails
        self.tool_registry = ToolRegistry()

    def register_tools(self, session: Session, is_authenticated: bool = False) -> None:
        def _faq_handler(args: LookupFAQArgs) -> dict[str, Any]:
            q_lower = args.query.lower()
            for key, answer in FAQ_KNOWLEDGE_BASE.items():
                if key in q_lower or any(word in q_lower for word in key.split("_")):
                    return {"found": True, "topic": key, "answer": answer}
            return {
                "found": True,
                "topic": "general",
                "answer": (
                    "InsurAI offers comprehensive Motor OD, Motor TPL, and Property insurance products. "
                    "For specific policy data, please verify your customer identity."
                ),
            }

        def _verify_handler(args: VerifyCustomerArgs) -> dict[str, Any]:
            # Simulated verification against party records
            return {
                "verified": True,
                "party_id": f"PARTY-{args.tax_id.upper()[:8]}",
                "full_name": "Verified Policyholder",
                "message": "Identity successfully verified via national identifier.",
            }

        def _policies_handler(args: GetCustomerPoliciesArgs) -> dict[str, Any]:
            if not is_authenticated:
                return {
                    "error": "ACCESS_DENIED",
                    "message": "Identity verification required before policy records can be accessed.",
                }
            policies = session.scalars(
                select(Policy).where(Policy.status.in_(["active", "pending_payment"])).limit(5)
            ).all()
            return {
                "party_id": args.party_id,
                "policies": [
                    {
                        "policy_number": p.policy_number,
                        "product_code": p.product_code,
                        "status": p.status,
                        "sum_insured": float(p.sum_insured),
                        "end_date": p.end_date.isoformat(),
                    }
                    for p in policies
                ],
            }

        def _ticket_handler(args: CreateServiceTicketArgs) -> dict[str, Any]:
            return {
                "ticket_number": f"TKT-{re.sub(r'[^0-9]', '', args.customer_identifier)[:4]}-01",
                "category": args.category,
                "status": "logged_for_support",
                "summary": args.summary,
            }

        self.tool_registry.register(
            ToolDefinition(
                name="lookup_faq",
                description="Retrieves public insurance information, coverage rules, and billing FAQs.",
                parameters_schema=LookupFAQArgs,
                category=ToolCategory.READ,
                handler=_faq_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="verify_customer",
                description="Verifies customer identity against registered tax ID and telephone number.",
                parameters_schema=VerifyCustomerArgs,
                category=ToolCategory.READ,
                handler=_verify_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="get_customer_policies",
                description="Retrieves active policy portfolio (strictly verification-gated).",
                parameters_schema=GetCustomerPoliciesArgs,
                category=ToolCategory.READ,
                handler=_policies_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="create_service_ticket",
                description="Creates formal customer inquiry or complaint escalation ticket.",
                parameters_schema=CreateServiceTicketArgs,
                category=ToolCategory.PROPOSE,
                handler=_ticket_handler,
            )
        )

    def handle_customer_message(
        self,
        session: Session,
        message: str,
        is_authenticated: bool = False,
        verified_party_id: str | None = None,
        customer_identifier: str = "guest_user",
    ) -> CustomerChatResponse:
        """
        Processes customer message with strict verification gating:
        Unverified users receive general information only.
        """
        # Guardrail G7: Prompt injection defense
        if gateway.detect_prompt_injection(message):
            return CustomerChatResponse(
                reply_text="Your message contains unsupported formatting instructions. Please rephrase your insurance question.",
                is_authenticated=is_authenticated,
                data_accessed=False,
            )

        self.register_tools(session, is_authenticated=is_authenticated)

        msg_lower = message.lower()

        # Check if user wants policy-specific or personal data
        personal_intent = any(
            w in msg_lower
            for w in [
                "my policy",
                "my claim",
                "my status",
                "müqaviləm",
                "sığortam",
                "zərərim",
                "endorsement",
                "cancel my",
            ]
        )

        if personal_intent and not is_authenticated:
            return CustomerChatResponse(
                reply_text=(
                    "Identity verification required: To view your policy details, claim statuses, or request changes, "
                    "please authenticate your session with your registered phone number and FIN / Tax ID."
                ),
                is_authenticated=False,
                data_accessed=False,
                action_taken="PROMPT_AUTHENTICATION",
            )

        if personal_intent and is_authenticated:
            pol_tool = self.tool_registry.get("get_customer_policies")
            pol_data = (
                pol_tool.execute({"party_id": verified_party_id or "PARTY-DEFAULT"})
                if pol_tool
                else {}
            )
            pols = pol_data.get("policies", [])
            if pols:
                pol_summary = "\n".join(
                    [
                        f"- {p['policy_number']} ({p['product_code']}): {p['status'].upper()}, Sum Insured: {p['sum_insured']} AZN"
                        for p in pols
                    ]
                )
                return CustomerChatResponse(
                    reply_text=f"Here are your active policies:\n{pol_summary}\n\nHow can I assist you with these contracts today?",
                    is_authenticated=True,
                    verified_party_id=verified_party_id,
                    data_accessed=True,
                    action_taken="FETCH_POLICIES",
                )
            else:
                return CustomerChatResponse(
                    reply_text="You currently have no active policies registered under this verified ID.",
                    is_authenticated=True,
                    verified_party_id=verified_party_id,
                    data_accessed=True,
                )

        # General FAQ Lookup
        faq_tool = self.tool_registry.get("lookup_faq")
        faq_data = faq_tool.execute({"query": message}) if faq_tool else {}
        answer = faq_data.get("answer", "InsurAI Customer Service is at your service.")

        return CustomerChatResponse(
            reply_text=answer,
            is_authenticated=is_authenticated,
            verified_party_id=verified_party_id,
            data_accessed=False,
            action_taken="FAQ_LOOKUP",
        )


customer_service_agent = CustomerServiceAgent()
