"""Unit and property-based invariant tests for the finance module and double-entry ledger."""

from datetime import date
from decimal import Decimal

import pytest
from app.modules.finance.public import (
    LedgerImbalanceError,
    check_ledger_balance,
    ensure_chart_of_accounts,
    finance_service,
    quantize_money,
    validate_balanced_transaction,
)
from app.modules.policy.public import Policy
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.orm import Session


def test_chart_of_accounts_initialization(db_session: Session) -> None:
    """Verifies that the standard chart of accounts is seeded properly."""
    ensure_chart_of_accounts(db_session)
    check = check_ledger_balance(db_session)
    assert check["is_balanced"] is True
    assert check["difference"] == Decimal("0.00")


def test_balanced_transaction_validation_success() -> None:
    """Tests that a balanced set of debits and credits is accepted."""
    entries = [
        {"account_code": "1010", "debit": Decimal("150.00"), "credit": Decimal("0.00")},
        {"account_code": "1200", "debit": Decimal("0.00"), "credit": Decimal("150.00")},
    ]
    total = validate_balanced_transaction(entries)
    assert total == Decimal("150.00")


def test_unbalanced_transaction_rejected() -> None:
    """Tests that any mismatch between debits and credits raises LedgerImbalanceError."""
    entries = [
        {"account_code": "1010", "debit": Decimal("150.00"), "credit": Decimal("0.00")},
        {"account_code": "1200", "debit": Decimal("0.00"), "credit": Decimal("149.99")},
    ]
    with pytest.raises(LedgerImbalanceError, match="Ledger imbalance detected"):
        validate_balanced_transaction(entries)


def test_multi_leg_transaction_balanced(db_session: Session) -> None:
    """Tests a complex split transaction (e.g. cash + fee = receivable)."""
    ensure_chart_of_accounts(db_session)
    entries = [
        {"account_code": "1010", "debit": Decimal("95.00"), "credit": Decimal("0.00")},
        {"account_code": "5020", "debit": Decimal("5.00"), "credit": Decimal("0.00")},
        {"account_code": "1200", "debit": Decimal("0.00"), "credit": Decimal("100.00")},
    ]
    tx = finance_service.record_gl_transaction(
        session=db_session,
        reference_type="PAYMENT_RECEIVED",
        reference_id="SPLIT-01",
        description="Split payment test",
        entries=entries,
    )
    assert tx.total_amount == Decimal("100.00")
    check = check_ledger_balance(db_session)
    assert check["is_balanced"] is True
    assert check["difference"] == Decimal("0.00")


@given(
    amount1=st.decimals(min_value=Decimal("1.00"), max_value=Decimal("50000.00"), places=2),
    amount2=st.decimals(min_value=Decimal("1.00"), max_value=Decimal("50000.00"), places=2),
)
def test_hypothesis_double_entry_property(amount1: Decimal, amount2: Decimal) -> None:
    """Property test: Sum of debits strictly equals sum of credits for any randomized amounts."""
    total = quantize_money(amount1 + amount2)
    entries = [
        {"account_code": "1010", "debit": quantize_money(amount1), "credit": Decimal("0.00")},
        {"account_code": "1200", "debit": quantize_money(amount2), "credit": Decimal("0.00")},
        {"account_code": "4010", "debit": Decimal("0.00"), "credit": total},
    ]
    validated_total = validate_balanced_transaction(entries)
    assert validated_total == total


def test_policy_invoicing_and_payment_flow(db_session: Session) -> None:
    """Tests end-to-end invoice generation, payment allocation, and GL balance preservation."""
    ensure_chart_of_accounts(db_session)

    # 1. Create policy
    policy = Policy(
        policy_number="POL-FIN-001",
        party_id="PARTY-001",
        asset_id="VEH-001",
        product_code="MOTOR_OD",
        product_version_id="VER-001",
        status="pending_payment",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        sum_insured=Decimal("30000.00"),
        deductible=Decimal("200.00"),
        total_premium=Decimal("1200.00"),
        paid_premium=Decimal("0.00"),
        payment_schedule=[
            {"installment_number": 1, "due_date": "2026-01-01", "amount": "600.00"},
            {"installment_number": 2, "due_date": "2026-07-01", "amount": "600.00"},
        ],
    )
    db_session.add(policy)
    db_session.flush()

    # 2. Generate invoices
    invoices = finance_service.create_invoices_for_policy(db_session, policy.id)
    assert len(invoices) == 2
    assert invoices[0].amount == Decimal("600.00")
    assert invoices[1].amount == Decimal("600.00")

    # Verify ledger is balanced after invoicing (AR vs GWP)
    check1 = check_ledger_balance(db_session)
    assert check1["is_balanced"] is True
    assert check1["total_debits"] == Decimal("1200.00")
    assert check1["total_credits"] == Decimal("1200.00")

    # 3. Pay first installment
    payment1 = finance_service.process_incoming_payment(
        session=db_session,
        invoice_id=invoices[0].id,
        amount=Decimal("600.00"),
        payment_method="bank_transfer",
    )
    assert payment1.status == "completed"
    assert invoices[0].status == "paid"
    assert policy.paid_premium == Decimal("600.00")
    assert policy.status == "active"  # Policy activated upon first payment!

    # Verify ledger remains perfectly balanced (Cash vs AR)
    check2 = check_ledger_balance(db_session)
    assert check2["is_balanced"] is True
    assert check2["difference"] == Decimal("0.00")


def test_dunning_job_escalation(db_session: Session) -> None:
    """Verifies that dunning job evaluates overdue invoices and escalates levels at T+7, T+14, T+30."""
    policy = Policy(
        policy_number="POL-DUN-001",
        party_id="PARTY-002",
        asset_id="VEH-002",
        product_code="MOTOR_OD",
        product_version_id="VER-001",
        status="pending_payment",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        sum_insured=Decimal("25000.00"),
        total_premium=Decimal("800.00"),
        payment_schedule=[{"installment_number": 1, "due_date": "2026-01-01", "amount": "800.00"}],
    )
    db_session.add(policy)
    db_session.flush()

    invoices = finance_service.create_invoices_for_policy(db_session, policy.id)
    assert len(invoices) == 1

    # Evaluate at T+8 (first reminder)
    notices1 = finance_service.run_dunning_job(db_session, as_of_date=date(2026, 1, 9))
    assert len(notices1) == 1
    assert notices1[0]["dunning_level"] == 1
    assert notices1[0]["notice_type"] == "first_reminder"

    # Evaluate at T+15 (final notice)
    notices2 = finance_service.run_dunning_job(db_session, as_of_date=date(2026, 1, 16))
    assert len(notices2) == 1
    assert notices2[0]["dunning_level"] == 2
    assert notices2[0]["notice_type"] == "final_notice"

    # Evaluate at T+35 (default cancellation notice)
    notices3 = finance_service.run_dunning_job(db_session, as_of_date=date(2026, 2, 5))
    assert len(notices3) == 1
    assert notices3[0]["dunning_level"] == 3
    assert notices3[0]["notice_type"] == "cancellation_default_notice"


def test_claims_disbursement_and_kpis(db_session: Session) -> None:
    """Tests claim reserve establishment, payout disbursement, commission, and KPI ratios."""
    ensure_chart_of_accounts(db_session)

    # 1. Premium invoiced & collected: 2000 AZN
    entries_prem = [
        {"account_code": "1010", "debit": Decimal("2000.00"), "credit": Decimal("0.00")},
        {"account_code": "4010", "debit": Decimal("0.00"), "credit": Decimal("2000.00")},
    ]
    finance_service.record_gl_transaction(
        db_session, "PREMIUM_INCOME", "POL-001", "Premium income", entries_prem
    )

    # 2. Claim reserve established: 800 AZN
    finance_service.record_claim_reserve_movement(
        db_session, "CLM-001", "CLM-2026-0001", Decimal("800.00")
    )

    # 3. Claim disbursement: 800 AZN
    disb = finance_service.disburse_claim_payout(
        db_session,
        "CLM-001",
        "CLM-2026-0001",
        "PARTY-PAYEE",
        Decimal("800.00"),
        approved_by="Adjuster Bob",
    )
    assert disb.status == "disbursed"

    # 4. Commission accrued: 200 AZN (10%)
    comm = finance_service.accrue_commission(
        db_session,
        "POL-001",
        "POL-2026-0001",
        "AGENT-001",
        Decimal("2000.00"),
        rate=Decimal("0.1000"),
    )
    assert comm.amount == Decimal("200.00")

    # 5. Check KPIs
    kpis = finance_service.get_financial_kpis(db_session)
    assert kpis["gross_written_premium"] == Decimal("2000.00")
    assert kpis["incurred_losses"] == Decimal("800.00")
    assert kpis["commissions_expense"] == Decimal("200.00")
    assert kpis["loss_ratio_pct"] == 40.0  # 800 / 2000 = 40%
    assert kpis["expense_ratio_pct"] == 10.0  # 200 / 2000 = 10%
    assert kpis["combined_ratio_pct"] == 50.0  # 40% + 10% = 50% (<100% profitable)
    assert kpis["ledger_balanced"] is True
    assert kpis["ledger_difference"] == Decimal("0.00")
