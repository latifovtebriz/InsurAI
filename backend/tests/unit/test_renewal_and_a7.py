"""Unit tests for Policy Renewal workflow, statutory notice deadlines, and Agent A7 Renewal Advisor."""

from datetime import date, timedelta
from decimal import Decimal

from app.modules.claims.public import Claim
from app.modules.policy.public import (
    Policy,
    renewal_advisor_agent,
    renewal_service,
)
from sqlalchemy.orm import Session


def test_renewal_t60_scanning_and_segmentation(db_session: Session) -> None:
    """Tests T-60 scanning and segmentation: clean risk (0 claims) gets 5% discount, 1 claim gets surcharge."""
    today = date(2026, 6, 1)

    # 1. Clean policy expiring in 45 days
    pol_clean = Policy(
        policy_number="POL-EXP-CLEAN",
        party_id="PARTY-01",
        asset_id="VEH-01",
        product_code="MOTOR_OD",
        product_version_id="VER-01",
        status="active",
        start_date=today - timedelta(days=320),
        end_date=today + timedelta(days=45),
        sum_insured=Decimal("30000.00"),
        total_premium=Decimal("1000.00"),
    )
    # 2. Claim-burdened policy expiring in 25 days (inside statutory 30-day window!)
    pol_bad = Policy(
        policy_number="POL-EXP-ADVERSE",
        party_id="PARTY-02",
        asset_id="VEH-02",
        product_code="MOTOR_OD",
        product_version_id="VER-01",
        status="active",
        start_date=today - timedelta(days=340),
        end_date=today + timedelta(days=25),
        sum_insured=Decimal("30000.00"),
        total_premium=Decimal("1000.00"),
    )
    db_session.add_all([pol_clean, pol_bad])
    db_session.flush()

    # Add 2 claims to pol_bad
    clm1 = Claim(
        claim_number="CLM-REV-01",
        policy_id=pol_bad.id,
        policy_number=pol_bad.policy_number,
        incident_date=today - timedelta(days=100),
        notification_date=today - timedelta(days=98),
        status="approved",
        claimed_amount=Decimal("4000.00"),
        incident_description="Front crash",
    )
    clm2 = Claim(
        claim_number="CLM-REV-02",
        policy_id=pol_bad.id,
        policy_number=pol_bad.policy_number,
        incident_date=today - timedelta(days=50),
        notification_date=today - timedelta(days=49),
        status="approved",
        claimed_amount=Decimal("6000.00"),
        incident_description="Rear impact",
    )
    db_session.add_all([clm1, clm2])
    db_session.flush()

    cases = renewal_service.scan_expiring_policies(db_session, as_of_date=today, days_ahead=60)
    assert len(cases) == 2

    clean_case = next(c for c in cases if c.policy_number == "POL-EXP-CLEAN")
    assert clean_case.claims_count == 0
    assert clean_case.recommendation == "STANDARD_RENEWAL"
    assert clean_case.proposed_premium == Decimal("950.00")  # 5% discount
    assert clean_case.statutory_deadline_breached is False

    adverse_case = next(c for c in cases if c.policy_number == "POL-EXP-ADVERSE")
    assert adverse_case.claims_count == 2
    assert adverse_case.recommendation == "NON_RENEWAL"
    # Days to expiry = 25, which is <= 30 statutory notice deadline, notice not sent yet!
    assert adverse_case.statutory_deadline_breached is True


def test_agent_a7_renewal_advisor_assessment(db_session: Session) -> None:
    """Verifies Agent A7 assessment, tool invocation, and L1 vs L2 governance determination."""
    today = date(2026, 6, 1)

    policy = Policy(
        policy_number="POL-A7-001",
        party_id="PARTY-03",
        asset_id="VEH-03",
        product_code="MOTOR_OD",
        product_version_id="VER-01",
        status="active",
        start_date=today - timedelta(days=310),
        end_date=today + timedelta(days=55),
        sum_insured=Decimal("20000.00"),
        total_premium=Decimal("800.00"),
    )
    db_session.add(policy)
    db_session.flush()

    assessment = renewal_advisor_agent.assess_policy_renewal(
        session=db_session,
        policy_number="POL-A7-001",
    )

    assert assessment.policy_number == "POL-A7-001"
    assert assessment.recommendation == "STANDARD_RENEWAL"
    assert assessment.autonomy_level == "L1"
    assert assessment.underwriter_signoff_required is False
    assert assessment.proposed_premium == 760.0  # 800 * 0.95 = 760
    assert "ANNUAL POLICY RENEWAL OFFER" in assessment.draft_notice_text


def test_renewal_workflow_issuance_and_acceptance(db_session: Session) -> None:
    """Tests issuing a renewal offer and customer acceptance, generating renewed policy contract."""
    today = date(2026, 6, 1)

    policy = Policy(
        policy_number="POL-RENEW-BASE",
        party_id="PARTY-04",
        asset_id="VEH-04",
        product_code="MOTOR_OD",
        product_version_id="VER-01",
        status="active",
        start_date=today - timedelta(days=320),
        end_date=today + timedelta(days=45),
        sum_insured=Decimal("35000.00"),
        deductible=Decimal("200.00"),
        total_premium=Decimal("1200.00"),
    )
    db_session.add(policy)
    db_session.flush()

    cases = renewal_service.scan_expiring_policies(db_session, as_of_date=today, days_ahead=60)
    case = cases[0]

    # Issue offer
    offered_case = renewal_service.generate_renewal_offer(db_session, case.id)
    assert offered_case.status == "offer_generated"
    assert offered_case.notice_sent is True

    # Accept renewal
    renewed_pol = renewal_service.accept_renewal(db_session, case.id)
    assert renewed_pol.policy_number == "POL-RENEW-BASE-R01"
    assert renewed_pol.status == "pending_payment"
    assert renewed_pol.start_date == policy.end_date
    assert renewed_pol.total_premium == Decimal("1140.00")  # 1200 * 0.95
