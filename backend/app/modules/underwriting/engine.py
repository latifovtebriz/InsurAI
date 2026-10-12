"""Deterministic underwriting rule engine and authority limits matrix."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class UnderwritingRuleHit(BaseModel):
    rule_code: str
    rule_name: str
    severity: str  # info, warning, referral, knockout
    description: str
    recommended_action: str


class UnderwritingEvaluationResult(BaseModel):
    has_referral: bool
    is_knockout: bool
    required_authority_tier: str  # junior, senior, chief
    recommended_status: str  # approved_standard, approved_with_conditions, declined, referred_senior
    rule_hits: list[UnderwritingRuleHit]
    suggested_conditions: list[str]


def evaluate_underwriting_rules(
    product_code: str,
    sum_insured: Decimal,
    rating_inputs: dict[str, Any],
) -> UnderwritingEvaluationResult:
    """
    Evaluates pure deterministic underwriting rules against quote/risk parameters.
    LLM is never permitted to override these deterministic rules without human underwriter sign-off.
    """
    hits: list[UnderwritingRuleHit] = []
    conditions: list[str] = []
    required_tier = "junior"
    is_knockout = False
    has_referral = False

    val = float(sum_insured)
    d_age = int(rating_inputs.get("driver_age", 30))
    prior_claims = int(rating_inputs.get("prior_claims_count", 0))
    wall_type = str(rating_inputs.get("wall_type", "stone")).lower()

    # Authority tier assessment based on sum insured
    if val > 150000.0:
        required_tier = "chief"
        has_referral = True
    elif val > 50000.0:
        required_tier = "senior"
        has_referral = True

    # Rule UW-05: Knockout (Statutory underage or extreme capacity breach)
    if d_age < 18 or val > 300000.0:
        is_knockout = True
        has_referral = True
        required_tier = "chief"
        reason = "Driver is under statutory driving age (18)" if d_age < 18 else "Sum insured exceeds 300,000 AZN maximum capacity."
        hits.append(
            UnderwritingRuleHit(
                rule_code="UW-05",
                rule_name="Hard Capacity / Eligibility Knockout",
                severity="knockout",
                description=reason,
                recommended_action="Decline risk (requires mandatory human underwriter sign-off).",
            )
        )
        conditions.append("Risk outside statutory underwriting appetite.")

    # Rule UW-01: High Vehicle Exposure (> 100,000 AZN)
    if val > 100000.0 and not is_knockout:
        has_referral = True
        if required_tier == "junior":
            required_tier = "senior"
        hits.append(
            UnderwritingRuleHit(
                rule_code="UW-01",
                rule_name="High Exposure Vehicle",
                severity="referral",
                description=f"Sum insured ({val:,.2f} AZN) exceeds standard 100,000 AZN underwriting threshold.",
                recommended_action="Referral to Senior Underwriter. Require GPS tracker installation.",
            )
        )
        conditions.append("Mandatory telematics/GPS tracker installation condition.")

    # Rule UW-02: Young Driver (< 21)
    if d_age < 21 and not is_knockout:
        has_referral = True
        hits.append(
            UnderwritingRuleHit(
                rule_code="UW-02",
                rule_name="Young Driver Hazard",
                severity="referral",
                description=f"Primary driver age ({d_age}) is under 21 years old.",
                recommended_action="Apply minimum 10% premium surcharge or increase deductible to 500 AZN.",
            )
        )
        conditions.append("Minimum deductible increased to 500.00 AZN due to young driver risk.")

    # Rule UW-03: Repeat Claimant (>= 2 prior claims)
    if prior_claims >= 2 and not is_knockout:
        has_referral = True
        if required_tier == "junior":
            required_tier = "senior"
        hits.append(
            UnderwritingRuleHit(
                rule_code="UW-03",
                rule_name="Adverse Loss History",
                severity="referral",
                description=f"Applicant has {prior_claims} prior claims in the preceding 12 months.",
                recommended_action="Refer to Senior Underwriter. Apply loss-history loading.",
            )
        )
        conditions.append("Loss-history underwriting review required.")

    # Rule UW-04: Non-standard Property Construction (HOME)
    if product_code.upper() == "HOME" and wall_type in ["wood", "clay", "timber"]:
        has_referral = True
        hits.append(
            UnderwritingRuleHit(
                rule_code="UW-04",
                rule_name="Combustible Property Construction",
                severity="referral",
                description=f"Wall construction material '{wall_type}' poses heightened fire hazard.",
                recommended_action="Apply 25% combustible structure surcharge and verify fire extinguishers.",
            )
        )
        conditions.append("Subject to mandatory on-site fire prevention survey.")

    # Determine recommended status
    if is_knockout:
        rec_status = "declined"
    elif has_referral:
        rec_status = "approved_with_conditions" if len(conditions) > 0 else "referred_senior"
    else:
        rec_status = "approved_standard"

    return UnderwritingEvaluationResult(
        has_referral=has_referral,
        is_knockout=is_knockout,
        required_authority_tier=required_tier,
        recommended_status=rec_status,
        rule_hits=hits,
        suggested_conditions=conditions,
    )


def verify_underwriter_authority(
    underwriter_tier: str,
    required_tier: str,
    sum_insured: Decimal,
) -> bool:
    """
    Validates whether an underwriter possesses adequate authority for the requested risk.
    Tiers: junior <= 50,000 AZN; senior <= 150,000 AZN; chief unlimited.
    """
    tier_rank = {"junior": 1, "senior": 2, "chief": 3, "admin": 3}
    user_rank = tier_rank.get(underwriter_tier.lower(), 1)
    req_rank = tier_rank.get(required_tier.lower(), 1)
    return user_rank >= req_rank
