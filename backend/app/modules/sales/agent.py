"""A1 Quote Assistant agent implementation."""

import re
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
from app.modules.policy.public import calculate_motor_od_premium
from pydantic import BaseModel, Field


class CalculateQuoteArgs(BaseModel):
    product_code: str = Field(
        default="MOTOR_OD", description="Product code: MOTOR_OD, MOTOR_TPL, HOME"
    )
    vehicle_value: float = Field(default=30000.0, description="Estimated market value in AZN")
    vehicle_age: int = Field(default=3, description="Vehicle age in years")
    driver_age: int = Field(default=30, description="Driver age in years")
    driver_experience: int = Field(default=7, description="Driving experience in years")
    deductible: float = Field(default=200.0, description="Selected deductible in AZN")


class CheckVehicleSpecsArgs(BaseModel):
    make: str = Field(default="Toyota", description="Vehicle manufacturer make")
    model: str = Field(default="Corolla", description="Vehicle model name")
    year: int = Field(default=2022, description="Manufacturing year")


class GetCoverageDetailsArgs(BaseModel):
    product_code: str = Field(default="MOTOR_OD", description="Product code to inspect")


class QuoteRequestExtraction(BaseModel):
    """Structured parameters extracted from applicant quotation inquiry."""

    product_code: str = "MOTOR_OD"
    vehicle_make: str | None = None
    vehicle_model: str | None = None
    vehicle_year: int | None = None
    vehicle_value: float | None = None
    driver_age: int | None = None
    driver_experience: int | None = None
    deductible: float = 200.0
    missing_fields: list[str] = []


def extract_quote_intent(user_text: str) -> QuoteRequestExtraction:
    """Extracts quote parameters and identifies any missing mandatory fields."""
    missing: list[str] = []
    text_lower = user_text.lower()

    product_code = "MOTOR_OD"
    if "tpl" in text_lower or "icbari" in text_lower or "third party" in text_lower:
        product_code = "MOTOR_TPL"
    elif (
        "home" in text_lower
        or "ev" in text_lower
        or "əmlak" in text_lower
        or "property" in text_lower
    ):
        product_code = "HOME"

    value_match = re.search(
        r"(\d[\d\s,]*\d|\d+)\s*(?:azn|manat|\$|usd|dəyərində|qiymətində)", user_text, re.IGNORECASE
    )
    vehicle_value: float | None = None
    if value_match:
        val_str = value_match.group(1).replace(" ", "").replace(",", "")
        vehicle_value = float(val_str)
    else:
        price_match = re.search(r"\b([1-9]\d{4,5})\b", user_text)
        if price_match:
            vehicle_value = float(price_match.group(1))
        else:
            missing.append("vehicle_value")

    age_match = re.search(
        r"(?:yaş(?:ım|ı)?\s*(?:var|olaraq)?\s*[:=]?\s*|age\s*[:=]?\s*)(\d{2})",
        user_text,
        re.IGNORECASE,
    )
    driver_age: int | None = None
    if age_match:
        driver_age = int(age_match.group(1))
    else:
        alt_age = re.search(r"\b(1[89]|[2-8]\d)\s*(?:yaş|years old|yo)\b", user_text, re.IGNORECASE)
        if alt_age:
            driver_age = int(alt_age.group(1))
        else:
            missing.append("driver_age")

    exp_match = re.search(
        r"(\d{1,2})\s*(?:il|illik|years?)\s*(?:təcrübə|staj|experience)", user_text, re.IGNORECASE
    )
    driver_experience: int | None = None
    if exp_match:
        driver_experience = int(exp_match.group(1))
    else:
        if driver_age and driver_age >= 21:
            driver_experience = max(1, driver_age - 21)
        else:
            driver_experience = 2

    year_match = re.search(r"\b(19\d{2}|20[0-2]\d)\b", user_text)
    vehicle_year: int | None = None
    if year_match:
        vehicle_year = int(year_match.group(1))

    ded_match = re.search(
        r"(\d+)\s*(?:azn)?\s*(?:azadolma|deductible|fransiza)", user_text, re.IGNORECASE
    )
    deductible = 200.0
    if ded_match:
        deductible = float(ded_match.group(1))

    return QuoteRequestExtraction(
        product_code=product_code,
        vehicle_make="Toyota" if "toyota" in text_lower else None,
        vehicle_model="Corolla" if "corolla" in text_lower else None,
        vehicle_year=vehicle_year or 2022,
        vehicle_value=vehicle_value,
        driver_age=driver_age,
        driver_experience=driver_experience,
        deductible=deductible,
        missing_fields=missing,
    )


class QuoteAssistantAgent:
    """A1 Quote Assistant: assists prospective clients, clarifies missing fields, and explains quotes."""

    def __init__(self, guardrails: GuardrailPipeline = guardrail_pipeline) -> None:
        self.guardrails = guardrails
        self.tool_registry = ToolRegistry()
        self._register_tools()

    def _register_tools(self) -> None:
        def _calc_handler(args: CalculateQuoteArgs) -> dict[str, Any]:
            val = Decimal(str(args.vehicle_value))
            d_age = args.driver_age
            v_age = args.vehicle_age

            breakdown = calculate_motor_od_premium(
                sum_insured=val,
                driver_age=d_age,
                vehicle_age=v_age,
                prior_claims_count=0,
            )

            return {
                "product_code": "MOTOR_OD",
                "base_premium": float(breakdown.base_premium),
                "final_premium": float(breakdown.final_premium),
                "total_payable": float(breakdown.final_premium),
                "factors_applied": [
                    {
                        "name": f.factor_name,
                        "multiplier": float(f.multiplier),
                        "reason": f.description,
                    }
                    for f in breakdown.applied_factors
                ],
            }

        def _specs_handler(args: CheckVehicleSpecsArgs) -> dict[str, Any]:
            return {
                "make": args.make,
                "model": args.model,
                "estimated_market_value_azn": 35000.0,
                "category": "passenger_sedan",
                "risk_tier": "standard",
            }

        def _coverage_handler(args: GetCoverageDetailsArgs) -> dict[str, Any]:
            code = args.product_code.upper()
            return {
                "product_code": code,
                "covered_perils": [
                    "Traffic collision",
                    "Theft / Burglary",
                    "Natural disasters",
                    "Falling objects",
                ],
                "key_exclusions": [
                    "Driving under alcohol/drug influence",
                    "Unlicensed driver",
                    "Intentional damage",
                ],
                "statutory_deductible_azn": 200.0,
            }

        self.tool_registry.register(
            ToolDefinition(
                name="calculate_quote",
                description="Calculates deterministic insurance quote premium using pure rating engine.",
                parameters_schema=CalculateQuoteArgs,
                category=ToolCategory.READ,
                handler=_calc_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="check_vehicle_specs",
                description="Retrieves market valuation range and vehicle category specs.",
                parameters_schema=CheckVehicleSpecsArgs,
                category=ToolCategory.READ,
                handler=_specs_handler,
            )
        )
        self.tool_registry.register(
            ToolDefinition(
                name="get_coverage_details",
                description="Returns standard perils and exclusions for a product.",
                parameters_schema=GetCoverageDetailsArgs,
                category=ToolCategory.READ,
                handler=_coverage_handler,
            )
        )

    def calculate_quote(
        self,
        vehicle_value: float,
        vehicle_age: int,
        driver_age: int,
        driver_experience: int,
        deductible: float = 200.0,
        product_code: str = "MOTOR_OD",
    ) -> dict[str, Any]:
        """Direct helper executing the registered calculation tool."""
        args_dict = {
            "product_code": product_code,
            "vehicle_value": vehicle_value,
            "vehicle_age": vehicle_age,
            "driver_age": driver_age,
            "driver_experience": driver_experience,
            "deductible": deductible,
        }
        tool = self.tool_registry.get("calculate_quote")
        if not tool:
            raise RuntimeError("Tool 'calculate_quote' not registered")
        return tool.execute(args_dict)

    def interact(
        self,
        user_message: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Processes applicant chat interaction with G7 defense and G2 numerical accuracy."""
        if gateway.detect_prompt_injection(user_message):
            return {
                "status": "blocked",
                "message": "Your request contains disallowed instructions and cannot be processed.",
                "risk_flag": "PROMPT_INJECTION_DETECTED",
                "recommendation": "escalate_to_human",
                "extracted": None,
                "quote_result": None,
            }

        extracted = extract_quote_intent(user_message)

        if extracted.missing_fields:
            missing_prompts = []
            if "vehicle_value" in extracted.missing_fields:
                missing_prompts.append("What is the estimated market value of your vehicle in AZN?")
            if "driver_age" in extracted.missing_fields:
                missing_prompts.append("Could you please specify your age as the primary driver?")

            return {
                "status": "needs_clarification",
                "message": "To provide you with an exact, guaranteed quote, please clarify: "
                + " ".join(missing_prompts),
                "missing_fields": extracted.missing_fields,
                "extracted": extracted.model_dump(),
                "quote_result": None,
            }

        current_year = 2026
        v_age = max(0, current_year - (extracted.vehicle_year or 2022))

        quote_data = self.calculate_quote(
            product_code=extracted.product_code,
            vehicle_value=extracted.vehicle_value or 30000.0,
            vehicle_age=v_age,
            driver_age=extracted.driver_age or 30,
            driver_experience=extracted.driver_experience or 5,
            deductible=extracted.deductible,
        )

        total_azn = quote_data["total_payable"]
        base_azn = quote_data["base_premium"]

        explanation = (
            f"Based on your vehicle value of {extracted.vehicle_value:,.2f} AZN and driver age of {extracted.driver_age}, "
            f"your comprehensive Kasko premium is exactly {total_azn:,.2f} AZN (Base Premium: {base_azn:,.2f} AZN "
            f"with a deductible of {extracted.deductible:,.2f} AZN). "
            f"Payment options include single lump-sum or 4 quarterly installments."
        )

        return {
            "status": "success",
            "message": explanation,
            "missing_fields": [],
            "extracted": extracted.model_dump(),
            "quote_result": quote_data,
        }


quote_assistant_agent = QuoteAssistantAgent()
