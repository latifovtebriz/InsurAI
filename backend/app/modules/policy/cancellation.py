"""Deterministic pro-rata cancellation and refund calculator (P06 & Clause F.1)."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class RefundCalculation:
    days_total: int
    days_elapsed: int
    days_remaining: int
    unearned_ratio: Decimal
    gross_refund: Decimal
    admin_fee: Decimal
    net_refund: Decimal
    has_prior_claims: bool
    requires_manager_approval: bool
    explanation: str


def calculate_cancellation_refund(
    start_date: date,
    end_date: date,
    cancellation_date: date,
    total_premium: Decimal,
    paid_premium: Decimal,
    has_prior_claims: bool = False,
    admin_fee: Decimal = Decimal("25.00"),
) -> RefundCalculation:
    """
    Calculates pro-rata refund upon mid-term policy cancellation per Clause F.1.
    Invariants:
      1. If prior claims have been filed, refund is strictly 0.00 AZN (Clause F.1).
      2. Net refund can never exceed total paid premium.
      3. If net refund > 500 AZN, manager sign-off is required.
      4. Accurate day counting accounts for leap years.
    """
    if end_date <= start_date:
        raise ValueError("Policy end_date must be strictly after start_date.")
    if paid_premium < Decimal("0"):
        raise ValueError("Paid premium cannot be negative.")

    days_total = (end_date - start_date).days

    # Cancellation before start date (pre-inception cancellation)
    if cancellation_date <= start_date:
        days_elapsed = 0
        days_remaining = days_total
        unearned_ratio = Decimal("1.0000")
        gross_refund = paid_premium
        net_refund = max(Decimal("0.00"), gross_refund - admin_fee)
        return RefundCalculation(
            days_total=days_total,
            days_elapsed=0,
            days_remaining=days_total,
            unearned_ratio=unearned_ratio,
            gross_refund=gross_refund,
            admin_fee=admin_fee,
            net_refund=net_refund,
            has_prior_claims=has_prior_claims,
            requires_manager_approval=net_refund > Decimal("500.00"),
            explanation="Pre-inception cancellation: 100% refund of paid premium minus admin fee.",
        )

    # Cancellation at or after expiration
    if cancellation_date >= end_date:
        days_elapsed = days_total
        days_remaining = 0
        return RefundCalculation(
            days_total=days_total,
            days_elapsed=days_total,
            days_remaining=0,
            unearned_ratio=Decimal("0.0000"),
            gross_refund=Decimal("0.00"),
            admin_fee=Decimal("0.00"),
            net_refund=Decimal("0.00"),
            has_prior_claims=has_prior_claims,
            requires_manager_approval=False,
            explanation="Policy term has expired; zero unearned premium remains.",
        )

    days_elapsed = (cancellation_date - start_date).days
    days_remaining = days_total - days_elapsed

    # Invariant: Clause F.1 denial if claims exist
    if has_prior_claims:
        return RefundCalculation(
            days_total=days_total,
            days_elapsed=days_elapsed,
            days_remaining=days_remaining,
            unearned_ratio=Decimal("0.0000"),
            gross_refund=Decimal("0.00"),
            admin_fee=Decimal("0.00"),
            net_refund=Decimal("0.00"),
            has_prior_claims=True,
            requires_manager_approval=False,
            explanation="Clause F.1 Exclusion: No refund permitted when prior claims exist on the policy.",
        )

    # Daily pro-rata ratio
    unearned_ratio = (Decimal(days_remaining) / Decimal(days_total)).quantize(
        Decimal("0.0001"), rounding=ROUND_HALF_UP
    )

    # Gross refund based on paid premium
    gross_refund = (paid_premium * (Decimal(days_remaining) / Decimal(days_total))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # Net refund after administrative fee deduction
    net_refund = max(Decimal("0.00"), gross_refund - admin_fee)

    # Invariant guarantee: refund cannot exceed paid premium
    net_refund = min(net_refund, paid_premium)

    requires_approval = net_refund > Decimal("500.00")

    explanation = (
        f"Pro-rata refund for {days_remaining}/{days_total} remaining days "
        f"({gross_refund} AZN gross - {admin_fee} AZN admin fee = {net_refund} AZN net)."
    )

    return RefundCalculation(
        days_total=days_total,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        unearned_ratio=unearned_ratio,
        gross_refund=gross_refund,
        admin_fee=admin_fee,
        net_refund=net_refund,
        has_prior_claims=False,
        requires_manager_approval=requires_approval,
        explanation=explanation,
    )
