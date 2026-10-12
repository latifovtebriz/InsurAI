from datetime import date, timedelta
from decimal import Decimal

from app.modules.policy.public import Policy
from app.modules.service.customer_agent import CustomerServiceAgent
from app.modules.service.models import EndorsementDraft
from app.modules.service.service import CustomerServiceDomain
from app.modules.service.servicing_agent import PolicyServicingAgent


def test_agent_a6_verification_gate_unverified_faq(db_session):
    """Unverified users can access general FAQ without authentication."""
    agent = CustomerServiceAgent()
    resp = agent.handle_customer_message(
        session=db_session,
        message="What is the standard deductible?",
        is_authenticated=False,
    )
    assert resp.is_authenticated is False
    assert resp.data_accessed is False
    assert "200 AZN" in resp.reply_text
    assert resp.action_taken == "FAQ_LOOKUP"


def test_agent_a6_verification_gate_blocks_unverified_policy_access(db_session):
    """Unverified users requesting policy data are strictly gated."""
    agent = CustomerServiceAgent()
    resp = agent.handle_customer_message(
        session=db_session,
        message="Can you tell me about my policy details and status?",
        is_authenticated=False,
    )
    assert resp.is_authenticated is False
    assert resp.data_accessed is False
    assert resp.action_taken == "PROMPT_AUTHENTICATION"
    assert "Identity verification required" in resp.reply_text


def test_agent_a6_verified_policy_access(db_session):
    """Verified users can inspect their active policies."""
    # Seed a policy
    start = date.today() - timedelta(days=30)
    end = start + timedelta(days=365)
    policy = Policy(
        policy_number="POL-A6-TEST-001",
        party_id="PARTY-VERIFIED-01",
        asset_id="ASSET-A6-01",
        product_code="MOTOR_OD",
        product_version_id="PV-A6-01",
        status="active",
        start_date=start,
        end_date=end,
        sum_insured=Decimal("35000.00"),
        total_premium=Decimal("1200.00"),
    )
    db_session.add(policy)
    db_session.flush()

    agent = CustomerServiceAgent()
    resp = agent.handle_customer_message(
        session=db_session,
        message="Show my policy details",
        is_authenticated=True,
        verified_party_id="PARTY-VERIFIED-01",
    )
    assert resp.is_authenticated is True
    assert resp.data_accessed is True
    assert resp.action_taken == "FETCH_POLICIES"
    assert "POL-A6-TEST-001" in resp.reply_text


def test_complaint_statutory_sla_countdown_and_breach(db_session):
    """Statutory SLAs: 5-day initial response, 15-day resolution deadline."""
    domain = CustomerServiceDomain()
    base_date = date(2026, 1, 1)

    complaint = domain.register_complaint(
        session=db_session,
        party_id="PARTY-COMPLAINT-01",
        subject="Delayed payout on claim CLM-991",
        description="Payout has been delayed over 2 weeks without adjuster communication.",
        as_of_date=base_date,
    )

    assert complaint.initial_response_deadline == date(2026, 1, 6)
    assert complaint.final_resolution_deadline == date(2026, 1, 16)
    assert complaint.sla_breached is False

    # Check SLA within deadline
    breached_early = domain.check_complaint_slas(session=db_session, as_of_date=date(2026, 1, 10))
    assert len(breached_early) == 0
    assert complaint.sla_breached is False

    # Check SLA past 15-day statutory deadline
    breached_late = domain.check_complaint_slas(session=db_session, as_of_date=date(2026, 1, 17))
    assert len(breached_late) == 1
    assert complaint.sla_breached is True
    assert complaint.status == "escalated_to_ombudsman"


def test_agent_a3_midterm_endorsement_and_prorata(db_session):
    """Agent A3 drafts mid-term endorsement with exact pro-rata premium under L2 governance."""
    start = date(2026, 1, 1)
    end = date(2026, 12, 31)  # 365 days
    policy = Policy(
        policy_number="POL-A3-TEST-001",
        party_id="PARTY-A3-01",
        asset_id="ASSET-A3-01",
        product_code="MOTOR_OD",
        product_version_id="PV-A3-01",
        status="active",
        start_date=start,
        end_date=end,
        sum_insured=Decimal("40000.00"),
        total_premium=Decimal("1200.00"),
    )
    db_session.add(policy)
    db_session.flush()

    agent = PolicyServicingAgent()
    # Halfway through year (day 183): increase sum insured to 50000 AZN (+10000 AZN)
    halfway_date = (start + timedelta(days=182)).isoformat()

    draft_res = agent.process_endorsement_request(
        session=db_session,
        policy_number="POL-A3-TEST-001",
        endorsement_type="INCREASE_SUM_INSURED",
        changes={"new_sum_insured": 50000.0},
        effective_date=halfway_date,
    )

    assert draft_res.policy_number == "POL-A3-TEST-001"
    assert draft_res.endorsement_type == "INCREASE_SUM_INSURED"
    assert draft_res.requires_underwriter_approval is True
    assert draft_res.autonomy_level == "L2"
    assert draft_res.prorata_adjustment_azn > 0.0

    # Save draft into database
    draft_record = EndorsementDraft(
        draft_number="DRAFT-A3-001",
        policy_id=policy.id,
        policy_number=policy.policy_number,
        endorsement_type=draft_res.endorsement_type,
        effective_date=date.fromisoformat(halfway_date),
        proposed_changes=draft_res.proposed_changes,
        prorata_premium_adjustment=Decimal(str(draft_res.prorata_adjustment_azn)),
        status="draft",
    )
    db_session.add(draft_record)
    db_session.flush()

    # Underwriter approves draft
    domain = CustomerServiceDomain()
    approved = domain.approve_endorsement(
        session=db_session,
        draft_id=draft_record.id,
        underwriter_name="uw_senan",
    )
    assert approved.status == "approved"
    assert approved.approved_by == "uw_senan"
    assert policy.sum_insured == Decimal("50000.00")
    assert policy.total_premium > Decimal("1200.00")
