"""A2 Underwriting Copilot agent implementation."""

from decimal import Decimal
from typing import Any

from app.modules.platform.public import (
    GuardrailPipeline,
    ToolCategory,
    ToolDefinition,
    ToolRegistry,
    guardrail_pipeline,
)
from app.modules.underwriting.engine import evaluate_underwriting_rules
from pydantic import BaseModel, Field


class EvaluateUnderwritingRulesArgs(BaseModel):
    product_code: str = Field(default="MOTOR_OD", description="Product code to evaluate")
    sum_insured: float = Field(default=30000.0, description="Sum insured in AZN")
    driver_age: int = Field(default=30, description="Driver age in years")
    prior_claims_count: int = Field(default=0, description="Prior claims count in 12 months")
    wall_type: str = Field(
        default="stone", description="Wall type for property: stone, wood, brick"
    )


class SearchUwGuidelinesArgs(BaseModel):
    query: str = Field(description="Search term in underwriting manual")
    product_code: str = Field(default="MOTOR_OD", description="Product code")


class GetRiskHistoryArgs(BaseModel):
    party_id: str = Field(description="Party or applicant ID")


class UnderwritingAssessment(BaseModel):
    """Structured assessment produced by A2 Underwriting Copilot."""

    case_id: str
    product_code: str
    recommended_action: str  # approve_standard, approve_with_conditions, decline, refer_senior
    confidence: float
    cited_guidelines: list[str]
    rule_hits: list[dict[str, Any]]
    proposed_conditions: list[str]
    risk_summary: str
    requires_human_approval: bool = True  # Always True under L2 guardrail


class UnderwritingCopilotAgent:
    """A2 Underwriting Copilot: assesses referred risks, grounds in guidelines, and proposes conditions."""

    def __init__(self, guardrails: GuardrailPipeline = guardrail_pipeline) -> None:
        self.guardrails = guardrails
        self.tool_registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        def _eval_handler(args: EvaluateUnderwritingRulesArgs) -> dict[str, Any]:
            res = evaluate_underwriting_rules(
                product_code=args.product_code,
                sum_insured=Decimal(str(args.sum_insured)),
                rating_inputs={
                    "driver_age": args.driver_age,
                    "prior_claims_count": args.prior_claims_count,
                    "wall_type": args.wall_type,
                },
            )
            return res.model_dump()

        def _guideline_handler(args: SearchUwGuidelinesArgs) -> list[dict[str, Any]]:
            guidelines = [
                {
                    "guideline_id": "UW-GUIDELINE-MOTOR-01",
                    "title": "High Exposure Vehicles (> 100,000 AZN)",
                    "rule": "Vehicles exceeding 100,000 AZN require Senior Underwriter approval and mandatory GPS telematics tracking warranty.",
                },
                {
                    "guideline_id": "UW-GUIDELINE-MOTOR-02",
                    "title": "Young Drivers (< 21 Years Old)",
                    "rule": "Drivers under 21 years old represent heightened frequency risk. A minimum 10% premium loading or an increased deductible of 500 AZN is mandatory.",
                },
                {
                    "guideline_id": "UW-GUIDELINE-MOTOR-03",
                    "title": "Adverse Prior Claims History",
                    "rule": "Applicants with 2 or more at-fault claims in the past 12 months require Senior Underwriter clearance.",
                },
                {
                    "guideline_id": "UW-GUIDELINE-HOME-01",
                    "title": "Combustible Wall Materials",
                    "rule": "Properties constructed with timber, wood, or combustible elements require a 25% fire surcharge and proof of functional fire safety measures.",
                },
            ]

            q = args.query.lower()
            matched = [
                g
                for g in guidelines
                if any(w in g["title"].lower() or w in g["rule"].lower() for w in q.split())
            ]
            return matched if matched else [guidelines[0]]

        def _history_handler(args: GetRiskHistoryArgs) -> dict[str, Any]:
            return {
                "party_id": args.party_id,
                "prior_claims_count_12m": 0,
                "total_incurred_claims_azn": 0.0,
                "prior_cancellations_count": 0,
                "bonus_malus_class": "BM0",
                "risk_profile": "favorable",
            }

        self.tool_registry.register(
            ToolDefinition(
                name="evaluate_underwriting_rules",
                description="Evaluates deterministic underwriting eligibility and referral rules.",
                parameters_schema=EvaluateUnderwritingRulesArgs,
                category=ToolCategory.READ,
                handler=_eval_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="search_uw_guidelines",
                description="Retrieves official underwriting guidelines and manual rules.",
                parameters_schema=SearchUwGuidelinesArgs,
                category=ToolCategory.READ,
                handler=_guideline_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="get_risk_history",
                description="Fetches prior claims, policy lapses, and loss ratio for applicant.",
                parameters_schema=GetRiskHistoryArgs,
                category=ToolCategory.READ,
                handler=_history_handler,
            )
        )

    def assess_case(
        self,
        case_id: str,
        product_code: str,
        sum_insured: Decimal,
        rating_inputs: dict[str, Any],
        party_id: str | None = None,
    ) -> UnderwritingAssessment:
        """
        Executes A2 Underwriting Copilot assessment:
        1. Evaluates deterministic rules (G5 mandatory tool).
        2. Retrieves relevant guideline citations (G1 Grounding).
        3. Assembles risk summary and recommended conditions.
        4. Enforces L2 Human-in-the-Loop guardrail (terminal decisions require human underwriter).
        """
        eval_result = evaluate_underwriting_rules(
            product_code=product_code,
            sum_insured=sum_insured,
            rating_inputs=rating_inputs,
        )

        cited_guidelines = []
        if eval_result.is_knockout:
            cited_guidelines.append(
                "UW-STATUTORY-ELIGIBILITY: Statutory driver minimum age (18) and insurer aggregate retention limits."
            )
            recommended_action = "decline"
            confidence = 0.99
            risk_summary = "Risk is outside acceptable statutory guidelines. Mandatory recommendation to decline."
        elif eval_result.has_referral:
            for hit in eval_result.rule_hits:
                if hit.rule_code == "UW-01":
                    cited_guidelines.append(
                        "UW-GUIDELINE-MOTOR-01: High Exposure Vehicles (> 100,000 AZN)"
                    )
                elif hit.rule_code == "UW-02":
                    cited_guidelines.append("UW-GUIDELINE-MOTOR-02: Young Drivers (< 21 Years Old)")
                elif hit.rule_code == "UW-03":
                    cited_guidelines.append("UW-GUIDELINE-MOTOR-03: Adverse Prior Claims History")
                elif hit.rule_code == "UW-04":
                    cited_guidelines.append("UW-GUIDELINE-HOME-01: Combustible Wall Materials")

            recommended_action = eval_result.recommended_status
            confidence = 0.92
            risk_summary = f"Underwriting referral triggered ({len(eval_result.rule_hits)} rule hits). Proposed conditional acceptance subject to warranted endorsement."
        else:
            cited_guidelines.append(
                "UW-STANDARD-ACCEPTANCE: Clean risk parameters within delegated junior underwriter limits."
            )
            recommended_action = "approve_standard"
            confidence = 0.95
            risk_summary = (
                "Standard risk profile. All rating inputs fall within standard pricing appetite."
            )

        return UnderwritingAssessment(
            case_id=case_id,
            product_code=product_code,
            recommended_action=recommended_action,
            confidence=confidence,
            cited_guidelines=cited_guidelines,
            rule_hits=[h.model_dump() for h in eval_result.rule_hits],
            proposed_conditions=eval_result.suggested_conditions,
            risk_summary=risk_summary,
            requires_human_approval=True,
        )


underwriting_copilot_agent = UnderwritingCopilotAgent()
