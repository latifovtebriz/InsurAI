"""Domain entities and dataclasses across bounded contexts (DDD Section 3.10)."""

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

# ==============================================================================
# Common Enums
# ==============================================================================


class LineOfBusiness(StrEnum):
    MOTOR_OD = "MOTOR_OD"
    MOTOR_TPL = "MOTOR_TPL"
    HOME = "HOME"


class PolicyStatus(StrEnum):
    DRAFT = "draft"
    QUOTED = "quoted"
    UNDERWRITING_REVIEW = "underwriting_review"
    BOUND = "bound"
    PENDING_PAYMENT = "pending_payment"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    RENEWED = "renewed"


class ClaimStatus(StrEnum):
    FNOL_RECEIVED = "fnol_received"
    REGISTERED = "registered"
    TRIAGE_IN_PROGRESS = "triage_in_progress"
    AWAITING_REVIEW = "awaiting_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SETTLED = "settled"
    CLOSED = "closed"


class RecommendationType(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


# ==============================================================================
# Party Bounded Context
# ==============================================================================


class Vehicle(BaseModel):
    id: str
    vin: str
    make: str
    model: str
    year: int
    plate_number: str
    engine_capacity_cc: int
    market_value: Decimal


class Property(BaseModel):
    id: str
    cadastral_code: str
    address: str
    build_year: int
    construction_type: str
    area_sqm: float
    estimated_value: Decimal


class Party(BaseModel):
    id: str
    party_type: str  # "individual" or "organization"
    full_name: str
    tax_id: str  # FIN or TIN (Synthetic)
    email: str
    phone: str
    birth_date: date | None = None
    license_issue_date: date | None = None
    vehicles: list[Vehicle] = Field(default_factory=list)
    properties: list[Property] = Field(default_factory=list)


# ==============================================================================
# Policy Bounded Context
# ==============================================================================


class Policy(BaseModel):
    id: str
    policy_number: str
    party_id: str
    product_code: str
    product_version: int
    status: PolicyStatus
    start_date: date
    end_date: date
    sum_insured: Decimal
    deductible: Decimal
    total_premium: Decimal
    payment_status: str = "paid"  # "paid", "pending", "overdue"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ==============================================================================
# Claims Bounded Context
# ==============================================================================


class ClaimDocument(BaseModel):
    id: str
    doc_type: str  # "incident_report", "repair_estimate", "police_report", "photo"
    title: str
    content_text: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class PayoutCalculation(BaseModel):
    claimed_amount: Decimal
    deductible_applied: Decimal
    depreciation_applied: Decimal = Decimal("0.00")
    salvage_deduction: Decimal = Decimal("0.00")
    capped_by_sum_insured: bool = False
    is_total_loss: bool = False
    payable_amount: Decimal


class Claim(BaseModel):
    id: str
    claim_number: str
    policy_id: str
    policy_number: str
    incident_date: datetime
    notification_date: datetime
    status: ClaimStatus
    description: str
    claimed_amount: Decimal
    reserve_amount: Decimal = Decimal("0.00")
    deductible: Decimal = Decimal("0.00")
    approved_payout: Decimal | None = None
    documents: list[ClaimDocument] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


# ==============================================================================
# Sales & Underwriting Context
# ==============================================================================


class Quote(BaseModel):
    id: str
    quote_number: str
    party_id: str
    product_code: str
    requested_sum_insured: Decimal
    base_premium: Decimal
    final_premium: Decimal
    valid_until: date
    status: str = "quoted"  # "quoted", "accepted", "expired"


class UnderwritingCase(BaseModel):
    id: str
    case_number: str
    quote_id: str
    trigger_rule_codes: list[str]
    status: str = "pending"  # "pending", "approved", "rejected"
    underwriter_notes: str | None = None


# ==============================================================================
# Finance & Compliance Context
# ==============================================================================


class Invoice(BaseModel):
    id: str
    invoice_number: str
    policy_id: str
    installment_number: int
    amount_due: Decimal
    due_date: date
    status: str = "paid"  # "pending", "paid", "overdue"


class WatchlistEntry(BaseModel):
    id: str
    full_name: str
    list_type: str  # "sanctions", "pep", "adverse_media"
    country: str
    aliases: list[str] = Field(default_factory=list)
    tax_id: str | None = None
