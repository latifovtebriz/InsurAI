"""Unit tests for reinsurance treaties, cessions, loss recoveries, and bordereaux."""

from datetime import date
from decimal import Decimal

from app.modules.finance.public import check_ledger_balance, ensure_chart_of_accounts
from app.modules.reinsurance.public import (
    reinsurance_service,
)
from sqlalchemy.orm import Session


def test_reinsurance_treaties_seeding(db_session: Session) -> None:
    """Verifies that market reinsurance treaties are seeded properly."""
    treaties = reinsurance_service.ensure_default_treaties(db_session)
    assert len(treaties) >= 3
    qs = next(
        t for t in treaties if t.treaty_type == "QUOTA_SHARE" and t.product_code == "MOTOR_OD"
    )
    assert qs.ceded_share_pct == Decimal("0.2000")
    assert qs.retention_share_pct == Decimal("0.8000")

    xol = next(
        t for t in treaties if t.treaty_type == "EXCESS_OF_LOSS" and t.product_code == "MOTOR_OD"
    )
    assert xol.retention_amount == Decimal("50000.00")
    assert xol.treaty_limit == Decimal("500000.00")


def test_premium_cession_and_gl_journal(db_session: Session) -> None:
    """Tests 20% Quota Share premium cession calculation and double-entry balanced posting."""
    ensure_chart_of_accounts(db_session)

    cessions = reinsurance_service.process_premium_cessions(
        session=db_session,
        policy_id="POL-REINS-001",
        policy_number="POL-2026-QS-001",
        product_code="MOTOR_OD",
        gross_premium=Decimal("1000.00"),
        cession_date=date(2026, 2, 1),
    )
    assert len(cessions) == 1
    c = cessions[0]
    assert c.gross_premium == Decimal("1000.00")
    assert c.ceded_premium == Decimal("200.00")  # 20% of 1000
    assert c.net_premium == Decimal("800.00")  # 80% retained

    # Check ledger balance
    check = check_ledger_balance(db_session)
    assert check["is_balanced"] is True
    assert check["difference"] == Decimal("0.00")


def test_claim_loss_recoveries_qs_and_xol(db_session: Session) -> None:
    """Tests claim recovery calculation under Quota Share and Excess of Loss treaties."""
    ensure_chart_of_accounts(db_session)

    # 1. Standard claim: 10,000 AZN (below XOL attachment point of 50k)
    recs1 = reinsurance_service.process_claim_recoveries(
        session=db_session,
        claim_id="CLM-001",
        claim_number="CLM-2026-0001",
        product_code="MOTOR_OD",
        gross_loss=Decimal("10000.00"),
        incident_date=date(2026, 3, 1),
    )
    # Only QS attaches
    assert len(recs1) == 1
    assert recs1[0].treaty_code == "TREATY-QS-MOTOR-2026"
    assert recs1[0].recovered_amount == Decimal("2000.00")  # 20% of 10,000

    # 2. Catastrophic large loss: 80,000 AZN (exceeds XOL retention of 50k by 30k)
    recs2 = reinsurance_service.process_claim_recoveries(
        session=db_session,
        claim_id="CLM-002",
        claim_number="CLM-2026-0002",
        product_code="MOTOR_OD",
        gross_loss=Decimal("80000.00"),
        incident_date=date(2026, 3, 15),
    )
    # Both QS and XOL attach
    assert len(recs2) == 2
    qs_rec = next(r for r in recs2 if "QS" in r.treaty_code)
    xol_rec = next(r for r in recs2 if "XOL" in r.treaty_code)

    assert qs_rec.recovered_amount == Decimal("16000.00")  # 20% of 80k
    assert xol_rec.recovered_amount == Decimal("30000.00")  # 80k - 50k retention = 30k

    # Check ledger balance
    check = check_ledger_balance(db_session)
    assert check["is_balanced"] is True
    assert check["difference"] == Decimal("0.00")


def test_bordereau_report_generation(db_session: Session) -> None:
    """Verifies that bordereaux reporting correctly aggregates cessions and recoveries."""
    ensure_chart_of_accounts(db_session)

    reinsurance_service.process_premium_cessions(
        session=db_session,
        policy_id="POL-01",
        policy_number="POL-2026-BORD-01",
        product_code="MOTOR_OD",
        gross_premium=Decimal("2500.00"),
        cession_date=date(2026, 1, 15),
    )
    reinsurance_service.process_claim_recoveries(
        session=db_session,
        claim_id="CLM-01",
        claim_number="CLM-2026-BORD-01",
        product_code="MOTOR_OD",
        gross_loss=Decimal("5000.00"),
        incident_date=date(2026, 2, 10),
    )

    report = reinsurance_service.generate_bordereau_report(
        session=db_session,
        treaty_code="TREATY-QS-MOTOR-2026",
    )
    assert report["treaty_code"] == "TREATY-QS-MOTOR-2026"
    assert report["summary"]["cessions_count"] >= 1
    assert report["summary"]["total_gross_premium"] == Decimal("2500.00")
    assert report["summary"]["total_ceded_premium"] == Decimal("500.00")
    assert report["summary"]["total_recovered_claims"] == Decimal("1000.00")
