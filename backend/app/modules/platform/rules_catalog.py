"""Platform business rules catalog with stable codes and effective dating."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class BusinessRuleDefinition(BaseModel):
    """Business rule definition with stable code and metadata."""

    code: str
    name: str
    description: str
    module: str
    value_type: str  # "decimal", "int", "str", "bool"
    value: Any
    unit: str | None = None
    effective_from: str = "2026-01-01"
    effective_to: str | None = None


BUSINESS_RULES_CATALOG: list[BusinessRuleDefinition] = [
    # Underwriting
    BusinessRuleDefinition(
        code="UW.REFER.VEHICLE_VALUE",
        name="Underwriting Referral: High Vehicle Value Threshold",
        description="Vehicles with market value exceeding this limit require senior underwriter review.",
        module="underwriting",
        value_type="decimal",
        value=Decimal("100000.00"),
        unit="AZN",
    ),
    BusinessRuleDefinition(
        code="UW.REFER.DRIVER_AGE_MIN",
        name="Underwriting Referral: Young Driver Floor",
        description="Drivers younger than this age require underwriter review and risk loading.",
        module="underwriting",
        value_type="int",
        value=21,
        unit="years",
    ),
    BusinessRuleDefinition(
        code="UW.REFER.CLAIM_HISTORY_MAX",
        name="Underwriting Referral: Maximum Prior Claims",
        description="Prospects with more prior claims in 2 years require manual underwriting.",
        module="underwriting",
        value_type="int",
        value=2,
        unit="claims",
    ),
    # Claims
    BusinessRuleDefinition(
        code="CLAIMS.NOTIFICATION_DAYS_LIMIT",
        name="Claims: Timely Notice Statutory Deadline",
        description="Claims must be reported to the insurer within this number of business days of loss.",
        module="claims",
        value_type="int",
        value=3,
        unit="business_days",
    ),
    BusinessRuleDefinition(
        code="CLAIMS.TOTAL_LOSS_RATIO",
        name="Claims: Constructive Total Loss Ratio",
        description="Threshold where repair cost to market value constitutes a constructive total loss.",
        module="claims",
        value_type="decimal",
        value=Decimal("0.70"),
        unit="ratio",
    ),
    BusinessRuleDefinition(
        code="CLAIMS.AUTO_APPROVE_MAX_AMOUNT",
        name="Claims: Simulated L3 Auto-Approval Max Payout",
        description="Maximum net payable amount eligible for simulated autonomous L3 settlement.",
        module="claims",
        value_type="decimal",
        value=Decimal("500.00"),
        unit="AZN",
    ),
    BusinessRuleDefinition(
        code="CLAIMS.AUTO_APPROVE_MIN_CONFIDENCE",
        name="Claims: Simulated L3 Auto-Approval Min Confidence",
        description="Minimum AI confidence score required for simulated autonomous L3 settlement.",
        module="claims",
        value_type="decimal",
        value=Decimal("0.85"),
        unit="score",
    ),
    BusinessRuleDefinition(
        code="CLAIMS.MIN_DEDUCTIBLE_MOTOR_OD",
        name="Claims: Standard Motor OD Deductible",
        description="Default unconditional deductible applied to motor own damage partial claims.",
        module="claims",
        value_type="decimal",
        value=Decimal("200.00"),
        unit="AZN",
    ),
    # Policy Servicing & Finance
    BusinessRuleDefinition(
        code="POLICY.CANCELLATION.ADMIN_FEE",
        name="Policy: Cancellation Administrative Fee",
        description="Administrative fee deducted from unearned pro-rata premium on policyholder cancellation.",
        module="policy",
        value_type="decimal",
        value=Decimal("25.00"),
        unit="AZN",
    ),
    BusinessRuleDefinition(
        code="POLICY.REFUND_APPROVAL_LIMIT",
        name="Policy: Refund Approval Limit",
        description="Refunds exceeding this threshold require four-eyes senior management sign-off.",
        module="policy",
        value_type="decimal",
        value=Decimal("500.00"),
        unit="AZN",
    ),
    BusinessRuleDefinition(
        code="FINANCE.DUNNING_NOTICE_1_DAYS",
        name="Finance: First Dunning Reminder Trigger",
        description="Days after installment due date before first payment reminder is issued.",
        module="finance",
        value_type="int",
        value=7,
        unit="days",
    ),
    BusinessRuleDefinition(
        code="FINANCE.DUNNING_NOTICE_2_DAYS",
        name="Finance: Second Dunning Warning Trigger",
        description="Days after installment due date before formal warning notice is issued.",
        module="finance",
        value_type="int",
        value=14,
        unit="days",
    ),
    BusinessRuleDefinition(
        code="FINANCE.CANCELLATION_NOTICE_DAYS",
        name="Finance: Statutory Non-Payment Cancellation Notice",
        description="Days after payment default before policy cancellation notice takes legal effect.",
        module="finance",
        value_type="int",
        value=30,
        unit="days",
    ),
    # Customer Service & Compliance
    BusinessRuleDefinition(
        code="SERVICE.COMPLAINT_SLA_INITIAL_DAYS",
        name="Service: Complaint Initial Response SLA",
        description="Mandatory timeframe to deliver formal initial acknowledgment of a complaint.",
        module="service",
        value_type="int",
        value=5,
        unit="business_days",
    ),
    BusinessRuleDefinition(
        code="SERVICE.COMPLAINT_SLA_FINAL_DAYS",
        name="Service: Complaint Final Resolution SLA",
        description="Mandatory statutory deadline to resolve and reply to customer complaints.",
        module="service",
        value_type="int",
        value=15,
        unit="business_days",
    ),
    BusinessRuleDefinition(
        code="COMPLIANCE.SANCTIONS_FUZZY_THRESHOLD",
        name="Compliance: Sanctions Name Matching Similarity Cutoff",
        description="Minimum Jaro-Winkler / Levenshtein fuzzy score to trigger compliance case review.",
        module="compliance",
        value_type="decimal",
        value=Decimal("0.85"),
        unit="score",
    ),
    # Reinsurance
    BusinessRuleDefinition(
        code="REINSURANCE.SURPLUS_RETENTION_LIMIT",
        name="Reinsurance: Motor Surplus Retention Ceiling",
        description="Maximum primary retention for single motor vehicle risk before surplus cession.",
        module="reinsurance",
        value_type="decimal",
        value=Decimal("50000.00"),
        unit="AZN",
    ),
]


def get_rule_by_code(code: str) -> BusinessRuleDefinition:
    """Retrieves business rule by its stable code."""
    for rule in BUSINESS_RULES_CATALOG:
        if rule.code == code:
            return rule
    raise KeyError(f"Business rule '{code}' not found in catalog")
