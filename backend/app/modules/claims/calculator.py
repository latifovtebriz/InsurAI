"""Deterministic calculation and verification engines for claims (payout, deadlines, fraud signals)."""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class PayoutResult:
    claimed_amount: Decimal
    sum_insured: Decimal
    deductible: Decimal
    deductible_applied: Decimal
    is_total_loss: bool
    capped_by_sum_insured: bool
    payable: Decimal


@dataclass(frozen=True)
class NotificationDeadlineReport:
    is_within_deadline: bool
    business_days_elapsed: int
    allowed_business_days: int
    reason: str


@dataclass(frozen=True)
class FraudSignal:
    code: str
    severity: str  # "high", "medium", "low"
    description: str


def calculate_claim_payout(
    claimed_amount: Decimal,
    sum_insured: Decimal,
    deductible: Decimal = Decimal("200.00"),
    loss_type: str = "partial",
) -> PayoutResult:
    """
    Deterministic claims payout calculator enforcing:
    1. Clause D.2: Constructive Total Loss if repair >= 70% of sum insured.
    2. Clause D.3: Deductible subtracted from payable amount.
    3. Invariant: Payable is non-negative and capped by sum insured minus deductible.
    """
    if sum_insured <= Decimal("0"):
        raise ValueError("Sum insured must be positive.")
    if claimed_amount < Decimal("0"):
        raise ValueError("Claimed amount cannot be negative.")

    # 1. Check Constructive Total Loss (70% threshold per Clause D.2)
    total_loss_threshold = (sum_insured * Decimal("0.70")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    is_total_loss = (claimed_amount >= total_loss_threshold) or (loss_type.lower() == "total_loss")

    if is_total_loss:
        gross_payable = sum_insured
    else:
        gross_payable = claimed_amount

    # 2. Apply Deductible
    deductible_applied = min(deductible, gross_payable)
    net_payable = gross_payable - deductible_applied

    # 3. Cap by sum insured
    max_possible = max(Decimal("0.00"), sum_insured - deductible)
    capped = net_payable > max_possible
    payable = min(net_payable, max_possible)

    # Invariant: non-negative
    payable = max(Decimal("0.00"), payable)

    return PayoutResult(
        claimed_amount=claimed_amount,
        sum_insured=sum_insured,
        deductible=deductible,
        deductible_applied=deductible_applied,
        is_total_loss=is_total_loss,
        capped_by_sum_insured=capped,
        payable=payable,
    )


def check_notification_deadline(
    incident_date: date,
    notification_date: date,
    allowed_business_days: int = 3,
) -> NotificationDeadlineReport:
    """
    Verifies Clause C.2 notice deadline (3 business days), skipping weekends.
    """
    if notification_date < incident_date:
        return NotificationDeadlineReport(
            is_within_deadline=False,
            business_days_elapsed=0,
            allowed_business_days=allowed_business_days,
            reason="Notification date precedes incident date.",
        )

    # Count business days between incident and notification (exclusive of incident date)
    curr = incident_date + timedelta(days=1)
    business_days = 0
    while curr <= notification_date:
        if curr.weekday() < 5:  # Monday to Friday
            business_days += 1
        curr += timedelta(days=1)

    is_valid = business_days <= allowed_business_days
    if is_valid:
        reason = (
            f"Reported within {business_days} business day(s) (allowed: {allowed_business_days})."
        )
    else:
        reason = f"Notice deadline exceeded: reported after {business_days} business days (allowed: {allowed_business_days})."

    return NotificationDeadlineReport(
        is_within_deadline=is_valid,
        business_days_elapsed=business_days,
        allowed_business_days=allowed_business_days,
        reason=reason,
    )


def get_rule_based_fraud_signals(
    policy_number: str,
    incident_date: date,
    claimed_amount: Decimal,
    prior_claims_count: int = 0,
    policy_start_date: date | None = None,
    raw_texts: list[str] | None = None,
) -> list[FraudSignal]:
    """
    Evaluates heuristic rule-based fraud and risk indicators (A5 & A4 integration).
    """
    signals: list[FraudSignal] = []

    # 1. Early inception claim (within 14 days of policy start)
    if policy_start_date:
        days_active = (incident_date - policy_start_date).days
        if 0 <= days_active <= 14:
            signals.append(
                FraudSignal(
                    code="EARLY_INCEPTION_CLAIM",
                    severity="high",
                    description=f"Incident occurred only {days_active} days after policy inception.",
                )
            )

    # 2. High frequency claimant
    if prior_claims_count >= 2:
        signals.append(
            FraudSignal(
                code="REPEAT_CLAIMANT",
                severity="medium",
                description=f"Policyholder has filed {prior_claims_count} prior claims.",
            )
        )

    # 3. Exact round sum between 5,000 and 20,000 AZN (excluding total loss threshold claims)
    if Decimal("5000.00") <= claimed_amount < Decimal("20000.00") and (
        claimed_amount % Decimal("1000.00") == Decimal("0.00")
    ):
        signals.append(
            FraudSignal(
                code="SUSPICIOUS_ROUND_SUM",
                severity="low",
                description=f"Claimed amount ({claimed_amount} AZN) is an exact round thousands figure without itemized cents.",
            )
        )

    # 4. Text indicators: alcohol / DUI (Clause B.3 exclusion)
    combined_text = " ".join(raw_texts or []).lower()
    if re.search(r"\b(alcohol|drunk|intoxicated|ethanol|1\.\d\s*g/l|dui)\b", combined_text):
        signals.append(
            FraudSignal(
                code="ALCOHOL_INTOXICATION_INDICATOR",
                severity="high",
                description="Evidence indicates possible driver alcohol intoxication (Clause B.3 exclusion).",
            )
        )

    # 5. Text indicators: ambiguous liability or third-party causation
    if re.search(
        r"\b(municipal|tree branch|falling tree|disputed|conflicting|rotted|subrogation)\b",
        combined_text,
    ):
        signals.append(
            FraudSignal(
                code="AMBIGUOUS_LIABILITY_OR_CAUSE",
                severity="medium",
                description="Evidence indicates potential municipal negligence or disputed liability requiring human review.",
            )
        )

    # 6. Prompt injection indicators (G7)
    if re.search(
        r"(ignore\s+(all\s+)?previous|you\s+are\s+now|system\s+override|approve\s+this\s+claim)",
        combined_text,
        re.I,
    ):
        signals.append(
            FraudSignal(
                code="PROMPT_INJECTION_ATTEMPT",
                severity="high",
                description="Adversarial prompt injection pattern detected in input documents.",
            )
        )

    return signals
