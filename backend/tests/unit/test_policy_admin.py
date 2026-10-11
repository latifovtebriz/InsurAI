"""Unit and property-based tests for Policy Administration: Rating, Cancellations, Issuance, and Party/Product."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.modules.party.public import party_service
from app.modules.platform.public import InsurAIException
from app.modules.policy.public import (
    calculate_cancellation_refund,
    calculate_home_premium,
    calculate_motor_od_premium,
    calculate_motor_tpl_premium,
    generate_installment_schedule,
    policy_service,
)
from app.modules.product.public import (
    FourEyesViolationError,
    product_service,
)
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# 1. Rating Engine Golden Tests
# ---------------------------------------------------------------------------


def test_motor_od_rating_standard_case() -> None:
    """Tests standard Motor OD case: 30yo driver, 3yo car, 0 claims, 25,000 AZN value."""
    # V2: 3.4% base rate, age >= 25 (1.0x), car <= 5 (1.0x), 0 claims (0.90x discount)
    # Base: 25000 * 0.034 = 850.00 AZN
    # After discount: 850.00 * 0.90 = 765.00 AZN
    breakdown = calculate_motor_od_premium(
        sum_insured=Decimal("25000.00"),
        driver_age=30,
        vehicle_age=3,
        prior_claims_count=0,
        version=2,
    )
    assert breakdown.base_premium == Decimal("850.00")
    assert breakdown.final_premium == Decimal("765.00")
    assert not breakdown.minimum_premium_enforced


def test_motor_od_rating_young_driver_and_old_vehicle() -> None:
    """Tests combined surcharges: driver < 25 (1.30x) and vehicle > 5 (1.20x)."""
    # 20,000 * 0.034 = 680.00
    # 680.00 * 1.30 = 884.00
    # 884.00 * 1.20 = 1060.80
    # 0 claims: 1060.80 * 0.90 = 954.72 AZN
    breakdown = calculate_motor_od_premium(
        sum_insured=Decimal("20000.00"),
        driver_age=22,
        vehicle_age=7,
        prior_claims_count=0,
        version=2,
    )
    assert breakdown.final_premium == Decimal("954.72")


def test_motor_od_minimum_premium_enforcement() -> None:
    """Tests that low-value vehicles are subject to minimum premium floor (380.00 AZN in V2)."""
    # 5,000 * 0.034 = 170.00 AZN -> subtotal 153.00 AZN -> min 380.00 enforced
    breakdown = calculate_motor_od_premium(
        sum_insured=Decimal("5000.00"),
        driver_age=40,
        vehicle_age=2,
        prior_claims_count=0,
        version=2,
    )
    assert breakdown.minimum_premium_enforced
    assert breakdown.final_premium == Decimal("380.00")


def test_motor_od_v1_vs_v2_effective_rate_difference() -> None:
    """Verifies that 2025 (V1) and 2026 (V2) use distinct base rates and minimums."""
    v1 = calculate_motor_od_premium(Decimal("10000.00"), 30, 2, 0, version=1)
    v2 = calculate_motor_od_premium(Decimal("10000.00"), 30, 2, 0, version=2)
    # V1: 3.2% = 320 -> * 0.9 = 288 -> min 350.00 enforced
    assert v1.base_rate_percent == Decimal("3.20")
    assert v1.minimum_premium == Decimal("350.00")
    assert v1.final_premium == Decimal("350.00")

    # V2: 3.4% = 340 -> * 0.9 = 306 -> min 380.00 enforced
    assert v2.base_rate_percent == Decimal("3.40")
    assert v2.minimum_premium == Decimal("380.00")
    assert v2.final_premium == Decimal("380.00")


def test_motor_tpl_rating_tiers() -> None:
    """Tests statutory TPL tariffs across engine sizes and claims records."""
    # Small engine (1400cc) + 0 claims: 100 * 1.0 * 0.90 = 90.00 AZN
    tpl_small = calculate_motor_tpl_premium(engine_capacity_cc=1400, prior_claims_count=0)
    assert tpl_small.final_premium == Decimal("90.00")

    # Large engine (3500cc) + 2 claims: 100 * 2.5 * 1.50 = 375.00 AZN
    tpl_large = calculate_motor_tpl_premium(engine_capacity_cc=3500, prior_claims_count=2)
    assert tpl_large.final_premium == Decimal("375.00")


def test_home_rating_wooden_structure_surcharge() -> None:
    """Tests HOME property rating: concrete vs wooden."""
    # 100,000 AZN * 0.25% = 250.00 AZN
    concrete = calculate_home_premium(
        Decimal("100000.00"), construction_type="concrete", build_year=2015
    )
    assert concrete.final_premium == Decimal("250.00")

    # Wooden: 250.00 * 1.50 = 375.00 AZN
    wooden = calculate_home_premium(
        Decimal("100000.00"), construction_type="wooden", build_year=2015
    )
    assert wooden.final_premium == Decimal("375.00")


# ---------------------------------------------------------------------------
# 2. Installment Schedule & Pro-Rata Cancellation Golden Tests
# ---------------------------------------------------------------------------


def test_installment_schedule_exact_penny_sum() -> None:
    """Verifies installment rounding: sum must match total_premium exactly."""
    total = Decimal("1000.00")
    # 12 installments: 1000 / 12 = 83.33 * 12 = 999.96 -> remainder 0.04 goes to 1st installment
    schedule = generate_installment_schedule(total, 12, date(2026, 1, 1))
    assert len(schedule) == 12
    assert schedule[0].amount == Decimal("83.37")
    assert schedule[1].amount == Decimal("83.33")
    assert sum(inst.amount for inst in schedule) == total


def test_pro_rata_cancellation_mid_term() -> None:
    """Tests mid-term cancellation: 180 days remaining, admin fee deducted."""
    start = date(2026, 1, 1)
    end = date(2027, 1, 1)  # 365 days
    cancel_date = date(2026, 7, 2)  # 182 days elapsed, 183 remaining
    paid = Decimal("730.00")

    calc = calculate_cancellation_refund(
        start_date=start,
        end_date=end,
        cancellation_date=cancel_date,
        total_premium=paid,
        paid_premium=paid,
        has_prior_claims=False,
    )
    # Gross: 730 * (183 / 365) = 366.00 AZN
    # Net: 366.00 - 25.00 (admin fee) = 341.00 AZN
    assert calc.gross_refund == Decimal("366.00")
    assert calc.net_refund == Decimal("341.00")
    assert not calc.requires_manager_approval


def test_pro_rata_cancellation_clause_f1_denial_when_claims_exist() -> None:
    """Clause F.1: Mid-term refund is strictly 0 AZN if claims have been filed."""
    start = date(2026, 1, 1)
    end = date(2027, 1, 1)
    cancel_date = date(2026, 6, 1)

    calc = calculate_cancellation_refund(
        start_date=start,
        end_date=end,
        cancellation_date=cancel_date,
        total_premium=Decimal("800.00"),
        paid_premium=Decimal("800.00"),
        has_prior_claims=True,
    )
    assert calc.net_refund == Decimal("0.00")
    assert "Clause F.1 Exclusion" in calc.explanation


def test_pro_rata_cancellation_leap_year_precision() -> None:
    """Verifies that leap years (e.g. 2024, 366 days) are handled accurately."""
    start = date(2024, 1, 1)
    end = date(2025, 1, 1)
    cancel_date = date(2024, 7, 1)  # 182 days elapsed, 184 remaining

    calc = calculate_cancellation_refund(
        start_date=start,
        end_date=end,
        cancellation_date=cancel_date,
        total_premium=Decimal("732.00"),
        paid_premium=Decimal("732.00"),
    )
    assert calc.days_total == 366
    assert calc.days_elapsed == 182
    assert calc.days_remaining == 184


def test_pro_rata_cancellation_high_value_requires_manager_approval() -> None:
    """Verifies that refunds exceeding 500 AZN require managerial sign-off."""
    start = date(2026, 1, 1)
    end = date(2027, 1, 1)
    cancel_date = date(2026, 2, 1)  # Early cancellation on expensive policy
    paid = Decimal("3000.00")

    calc = calculate_cancellation_refund(
        start_date=start,
        end_date=end,
        cancellation_date=cancel_date,
        total_premium=paid,
        paid_premium=paid,
    )
    assert calc.net_refund > Decimal("500.00")
    assert calc.requires_manager_approval


# ---------------------------------------------------------------------------
# 3. Property-Based Testing (Hypothesis)
# ---------------------------------------------------------------------------


@given(
    sum_insured=st.decimals(min_value=Decimal("1000.00"), max_value=Decimal("250000.00"), places=2),
    driver_age=st.integers(min_value=18, max_value=85),
    vehicle_age=st.integers(min_value=0, max_value=25),
    claims_count=st.integers(min_value=0, max_value=5),
)
def test_hypothesis_motor_od_premium_invariants(
    sum_insured: Decimal, driver_age: int, vehicle_age: int, claims_count: int
) -> None:
    """Property: Premium is always strictly positive and >= minimum premium (380.00)."""
    breakdown = calculate_motor_od_premium(
        sum_insured, driver_age, vehicle_age, claims_count, version=2
    )
    assert breakdown.final_premium >= Decimal("380.00")
    assert breakdown.final_premium > Decimal("0.00")


@given(
    total=st.decimals(min_value=Decimal("50.00"), max_value=Decimal("50000.00"), places=2),
    count=st.sampled_from([1, 2, 4, 12]),
)
def test_hypothesis_installment_schedule_sum_invariant(total: Decimal, count: int) -> None:
    """Property: Sum of installments strictly equals total_premium down to the exact cent."""
    schedule = generate_installment_schedule(total, count, date(2026, 1, 1))
    assert sum(inst.amount for inst in schedule) == total


@given(
    paid=st.decimals(min_value=Decimal("0.00"), max_value=Decimal("10000.00"), places=2),
    days_elapsed=st.integers(min_value=0, max_value=365),
)
def test_hypothesis_cancellation_refund_invariants(paid: Decimal, days_elapsed: int) -> None:
    """Property: Refund is non-negative and never exceeds paid premium."""
    start = date(2026, 1, 1)
    end = start + timedelta(days=365)
    cancel = start + timedelta(days=days_elapsed)

    calc = calculate_cancellation_refund(start, end, cancel, paid, paid)
    assert calc.net_refund >= Decimal("0.00")
    assert calc.net_refund <= paid


# ---------------------------------------------------------------------------
# 4. Domain Service & Four-Eyes Governance Integration Tests
# ---------------------------------------------------------------------------


def test_four_eyes_publication_rule(db_session: Session) -> None:
    """Product version publication must fail if reviewer is the creator (four-eyes rule)."""
    product_service.create_product(
        session=db_session,
        product_code="TEST_PROD",
        name="Test Insurance",
        description="Test desc",
        line_of_business="motor",
    )
    v1 = product_service.create_product_version(
        session=db_session,
        product_code="TEST_PROD",
        version=1,
        version_code="TEST_V1",
        effective_from=date(2026, 1, 1),
        tariffs=[],
        clauses=[],
        created_by="actuary_alice",
    )

    # 1. Self-approval violates four-eyes principle
    with pytest.raises(FourEyesViolationError):
        product_service.publish_product_version(db_session, v1.id, reviewer_id="actuary_alice")

    # 2. Distinct reviewer succeeds
    published = product_service.publish_product_version(
        db_session, v1.id, reviewer_id="underwriter_bob"
    )
    assert published.status == "published"
    assert published.reviewed_by == "underwriter_bob"


def test_policy_issuance_kyc_guard_and_lifecycle(db_session: Session) -> None:
    """Tests P04 issuance: requires verified KYC, creates certificate, handles payment."""
    # Create product and publish version
    product_service.create_product(db_session, "MOTOR_OD", "Motor OD", "Kasko", "motor")
    v2 = product_service.create_product_version(
        db_session,
        "MOTOR_OD",
        2,
        "MOD_V2",
        date(2026, 1, 1),
        tariffs=[],
        clauses=[],
        created_by="actuary_1",
    )
    product_service.publish_product_version(db_session, v2.id, reviewer_id="reviewer_2")

    # 1. Party with pending KYC cannot bind policy
    party_pending = party_service.create_party(
        db_session,
        party_type="individual",
        tax_id="FIN12345",
        email="pending@test.com",
        phone="+994501234567",
        address="Baku",
        first_name="Ali",
        last_name="Valiyev",
        kyc_status="pending",
    )
    vehicle = party_service.create_vehicle(
        db_session,
        owner_party_id=party_pending.id,
        vin="VIN1234567890ABCD",
        registration_number="99-AA-999",
        make="Toyota",
        model="Corolla",
        manufacture_year=2022,
        engine_capacity_cc=1800,
        market_value=Decimal("25000.00"),
    )

    with pytest.raises(InsurAIException) as exc_info:
        policy_service.issue_policy(
            session=db_session,
            party_id=party_pending.id,
            asset_id=vehicle.id,
            product_code="MOTOR_OD",
            start_date=date(2026, 5, 1),
            end_date=date(2027, 5, 1),
            sum_insured=Decimal("25000.00"),
            total_premium=Decimal("850.00"),
        )
    assert "KYC Verification Required" in exc_info.value.title

    # 2. Update KYC to verified and successfully issue policy
    party_service.update_kyc_status(db_session, party_pending.id, "verified")
    policy = policy_service.issue_policy(
        session=db_session,
        party_id=party_pending.id,
        asset_id=vehicle.id,
        product_code="MOTOR_OD",
        start_date=date(2026, 5, 1),
        end_date=date(2027, 5, 1),
        sum_insured=Decimal("25000.00"),
        total_premium=Decimal("850.00"),
        initial_payment=Decimal("0.00"),
    )
    assert policy.status == "pending_payment"
    assert policy.policy_number.startswith("POL-2026-MOD-")

    # 3. Pay premium -> transitions to active
    policy_paid = policy_service.record_premium_payment(db_session, policy.id, Decimal("850.00"))
    assert policy_paid.status == "active"
    assert policy_paid.paid_premium == Decimal("850.00")

    # 4. Check policy active engine for Claims Triage A4
    report_valid = policy_service.check_policy_active(
        db_session, policy.policy_number, date(2026, 6, 15)
    )
    assert report_valid.is_active
    assert report_valid.in_force

    report_expired = policy_service.check_policy_active(
        db_session, policy.policy_number, date(2027, 6, 1)
    )
    assert not report_expired.in_force

    # 5. Cancel policy (P06)
    cancelled_policy, calc = policy_service.cancel_policy(
        db_session,
        policy.id,
        cancellation_date=date(2026, 11, 1),
        reason="Customer sold vehicle",
    )
    assert cancelled_policy.status == "cancelled"
    assert calc.net_refund > Decimal("0.00")
