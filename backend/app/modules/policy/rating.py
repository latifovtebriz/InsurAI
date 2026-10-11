"""Pure deterministic rating engine for MOTOR_OD, MOTOR_TPL, and HOME products."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class FactorApplication:
    factor_name: str
    multiplier: Decimal
    description: str


@dataclass(frozen=True)
class RatingBreakdown:
    product_code: str
    sum_insured: Decimal
    base_rate_percent: Decimal
    base_premium: Decimal
    applied_factors: list[FactorApplication]
    subtotal: Decimal
    minimum_premium: Decimal
    minimum_premium_enforced: bool
    final_premium: Decimal


@dataclass(frozen=True)
class Installment:
    installment_number: int
    due_date: date
    amount: Decimal


def quantize_money(amount: Decimal) -> Decimal:
    """Rounds amount to 2 decimal places using standard ROUND_HALF_UP."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_motor_od_premium(
    sum_insured: Decimal,
    driver_age: int,
    vehicle_age: int,
    prior_claims_count: int = 0,
    version: int = 2,
) -> RatingBreakdown:
    """
    Calculates Motor Own Damage (Kasko) premium.
    V1: 3.2% base rate, 350 min premium, age factor 1.25, vehicle age factor 1.15.
    V2: 3.4% base rate, 380 min premium, age factor 1.30, vehicle age factor 1.20.
    """
    if sum_insured <= Decimal("0"):
        raise ValueError("Sum insured must be positive.")

    if version == 1:
        base_rate = Decimal("3.20")
        min_premium = Decimal("350.00")
        age_mult = Decimal("1.25")
        veh_mult = Decimal("1.15")
    else:
        base_rate = Decimal("3.40")
        min_premium = Decimal("380.00")
        age_mult = Decimal("1.30")
        veh_mult = Decimal("1.20")

    base_prem = quantize_money(sum_insured * (base_rate / Decimal("100.00")))
    factors: list[FactorApplication] = []
    current_prem = base_prem

    # 1. Driver age factor
    if driver_age < 25:
        factors.append(
            FactorApplication(
                factor_name="driver_under_25",
                multiplier=age_mult,
                description=f"Young driver under 25 surcharge ({age_mult}x)",
            )
        )
        current_prem = quantize_money(current_prem * age_mult)

    # 2. Vehicle age factor
    if vehicle_age > 5:
        factors.append(
            FactorApplication(
                factor_name="vehicle_age_gt_5",
                multiplier=veh_mult,
                description=f"Vehicle older than 5 years surcharge ({veh_mult}x)",
            )
        )
        current_prem = quantize_money(current_prem * veh_mult)

    # 3. Bonus-malus discount/surcharge
    if prior_claims_count == 0:
        bm_mult = Decimal("0.90")
        factors.append(
            FactorApplication(
                factor_name="no_claim_discount",
                multiplier=bm_mult,
                description="10% discount for zero prior claims",
            )
        )
        current_prem = quantize_money(current_prem * bm_mult)
    elif prior_claims_count == 1:
        bm_mult = Decimal("1.15")
        factors.append(
            FactorApplication(
                factor_name="malus_1_claim",
                multiplier=bm_mult,
                description="15% surcharge for 1 prior claim",
            )
        )
        current_prem = quantize_money(current_prem * bm_mult)
    else:
        bm_mult = Decimal("1.35")
        factors.append(
            FactorApplication(
                factor_name="malus_multiple_claims",
                multiplier=bm_mult,
                description=f"35% surcharge for {prior_claims_count} prior claims",
            )
        )
        current_prem = quantize_money(current_prem * bm_mult)

    subtotal = current_prem
    if subtotal < min_premium:
        final_premium = min_premium
        min_enforced = True
    else:
        final_premium = subtotal
        min_enforced = False

    return RatingBreakdown(
        product_code="MOTOR_OD",
        sum_insured=sum_insured,
        base_rate_percent=base_rate,
        base_premium=base_prem,
        applied_factors=factors,
        subtotal=subtotal,
        minimum_premium=min_premium,
        minimum_premium_enforced=min_enforced,
        final_premium=final_premium,
    )


def calculate_motor_tpl_premium(
    engine_capacity_cc: int,
    prior_claims_count: int = 0,
) -> RatingBreakdown:
    """Calculates Motor Third-Party Liability (TPL) statutory tariff."""
    base_rate_fee = Decimal("100.00")
    min_premium = Decimal("90.00")

    factors: list[FactorApplication] = []

    # 1. Engine capacity coefficient
    if engine_capacity_cc <= 1500:
        cap_mult = Decimal("1.00")
    elif engine_capacity_cc <= 2000:
        cap_mult = Decimal("1.50")
    elif engine_capacity_cc <= 3000:
        cap_mult = Decimal("2.00")
    else:
        cap_mult = Decimal("2.50")

    factors.append(
        FactorApplication(
            factor_name="engine_capacity",
            multiplier=cap_mult,
            description=f"Engine capacity {engine_capacity_cc}cc multiplier ({cap_mult}x)",
        )
    )
    current_prem = quantize_money(base_rate_fee * cap_mult)

    # 2. Bonus-malus
    if prior_claims_count == 0:
        bm_mult = Decimal("0.90")
        factors.append(
            FactorApplication(
                factor_name="bonus_malus_preferred",
                multiplier=bm_mult,
                description="Bonus discount (0.90x)",
            )
        )
        current_prem = quantize_money(current_prem * bm_mult)
    elif prior_claims_count == 1:
        bm_mult = Decimal("1.20")
        factors.append(
            FactorApplication(
                factor_name="bonus_malus_standard",
                multiplier=bm_mult,
                description="Malus surcharge 1 claim (1.20x)",
            )
        )
        current_prem = quantize_money(current_prem * bm_mult)
    else:
        bm_mult = Decimal("1.50")
        factors.append(
            FactorApplication(
                factor_name="bonus_malus_high_risk",
                multiplier=bm_mult,
                description="Malus surcharge multiple claims (1.50x)",
            )
        )
        current_prem = quantize_money(current_prem * bm_mult)

    subtotal = current_prem
    if subtotal < min_premium:
        final_premium = min_premium
        min_enforced = True
    else:
        final_premium = subtotal
        min_enforced = False

    return RatingBreakdown(
        product_code="MOTOR_TPL",
        sum_insured=Decimal("50000.00"),  # Statutory coverage limit
        base_rate_percent=Decimal("0.20"),
        base_premium=base_rate_fee,
        applied_factors=factors,
        subtotal=subtotal,
        minimum_premium=min_premium,
        minimum_premium_enforced=min_enforced,
        final_premium=final_premium,
    )


def calculate_home_premium(
    sum_insured: Decimal,
    construction_type: str,
    build_year: int,
) -> RatingBreakdown:
    """Calculates Residential Property (HOME) insurance premium."""
    if sum_insured <= Decimal("0"):
        raise ValueError("Sum insured must be positive.")

    base_rate = Decimal("0.25")  # 0.25%
    min_premium = Decimal("120.00")
    base_prem = quantize_money(sum_insured * (base_rate / Decimal("100.00")))

    factors: list[FactorApplication] = []
    current_prem = base_prem

    # 1. Construction type multiplier
    if construction_type.lower() == "wooden":
        wood_mult = Decimal("1.50")
        factors.append(
            FactorApplication(
                factor_name="wooden_construction",
                multiplier=wood_mult,
                description="High fire risk surcharge for wooden structure (1.50x)",
            )
        )
        current_prem = quantize_money(current_prem * wood_mult)

    # 2. Historic / aging building surcharge
    if build_year < 1970:
        hist_mult = Decimal("1.20")
        factors.append(
            FactorApplication(
                factor_name="pre_1970_building",
                multiplier=hist_mult,
                description="Aging plumbing and wiring risk surcharge (1.20x)",
            )
        )
        current_prem = quantize_money(current_prem * hist_mult)

    subtotal = current_prem
    if subtotal < min_premium:
        final_premium = min_premium
        min_enforced = True
    else:
        final_premium = subtotal
        min_enforced = False

    return RatingBreakdown(
        product_code="HOME",
        sum_insured=sum_insured,
        base_rate_percent=base_rate,
        base_premium=base_prem,
        applied_factors=factors,
        subtotal=subtotal,
        minimum_premium=min_premium,
        minimum_premium_enforced=min_enforced,
        final_premium=final_premium,
    )


def generate_installment_schedule(
    total_premium: Decimal,
    installments_count: int,
    start_date: date,
) -> list[Installment]:
    """
    Generates installment schedule ensuring mathematical invariant:
    The sum of all installments strictly equals total_premium down to the exact cent.
    """
    if installments_count not in (1, 2, 4, 12):
        raise ValueError("installments_count must be 1, 2, 4, or 12.")
    if total_premium < Decimal("0"):
        raise ValueError("total_premium cannot be negative.")

    count_dec = Decimal(installments_count)
    # Floor division to 2 decimal places
    base_installment = (total_premium / count_dec).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Calculate remainder so installments sum exactly to total_premium
    total_scheduled = base_installment * count_dec
    remainder = total_premium - total_scheduled

    days_step = 365 // installments_count

    schedule: list[Installment] = []
    for i in range(installments_count):
        due = start_date + timedelta(days=i * days_step)
        # Add any penny remainder to the first installment
        amt = base_installment + (remainder if i == 0 else Decimal("0.00"))
        schedule.append(
            Installment(
                installment_number=i + 1,
                due_date=due,
                amount=amt,
            )
        )

    # Invariant verification
    assert sum(inst.amount for inst in schedule) == total_premium, (
        "Installments must sum to total_premium."
    )
    return schedule
