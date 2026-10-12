"""Comprehensive End-to-End Golden Journey Integration Test for Phase 12 (Release R3):
Full enterprise Property & Casualty lifecycle:
1. Sales & Quote (Agent A1)
2. Underwriting Evaluation & Sign-off (Agent A2)
3. Policy Binding & Issuance (Process P02)
4. Invoicing, Payment Intake & Balanced Ledger (Finance)
5. Reinsurance Treaty Cession (Quota Share 20%)
6. Mid-Term Endorsement & Pro-Rata Math (Agent A3, Process P06)
7. FNOL Intake, Claim Triage & Reserving (Agent A4, Clause D.2/C.2)
8. Fraud Risk Assessment & G8 Neutral Dossier (Agent A5)
9. Claim Settlement Disbursement & Reserve Clearance
10. Reinsurance Loss Recovery
11. Expiring Policy Scanning & Renewal Advisory at T-60 (Agent A7, Process P07)
12. Full System Invariant Assertions: Outbox, Audit Trail, Balanced General Ledger.
"""

from collections.abc import Generator
from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.db import get_db
from app.main import app
from app.modules.claims.public import Claim
from app.modules.finance.public import (
    check_ledger_balance,
    ensure_chart_of_accounts,
    finance_service,
)
from app.modules.fraud.public import fraud_assistant_agent, fraud_service
from app.modules.party.public import party_service
from app.modules.platform.public import (
    AuditLog,
    create_access_token,
)
from app.modules.policy.public import (
    Policy,
    renewal_advisor_agent,
    renewal_service,
)
from app.modules.product.public import product_service
from app.modules.reinsurance.public import reinsurance_service
from app.modules.sales.public import sales_service
from app.modules.service.public import (
    EndorsementDraft,
    customer_service_domain,
    policy_servicing_agent,
)
from app.modules.underwriting.public import (
    evaluate_underwriting_rules,
    underwriting_service,
)
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def lifecycle_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client bound to isolated test database session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_full_policy_lifecycle_golden_journey(
    lifecycle_client: TestClient, db_session: Session
) -> None:
    # 0. Setup Foundation Data: Chart of Accounts & Reinsurance Treaties
    ensure_chart_of_accounts(db_session)
    treaties = reinsurance_service.ensure_default_treaties(db_session)
    assert len(treaties) >= 1
    db_session.commit()

    # Create Product & Version
    product_service.create_product(db_session, "MOTOR_OD", "Motor OD", "Kasko", "motor")
    v1 = product_service.create_product_version(
        db_session,
        "MOTOR_OD",
        1,
        "MOD_V1",
        date(2026, 1, 1),
        tariffs=[],
        clauses=[],
        created_by="actuary_samir",
    )
    product_service.publish_product_version(db_session, v1.id, reviewer_id="reviewer_nigar")

    # Create Party & Vehicle
    party = party_service.create_party(
        db_session,
        party_type="individual",
        tax_id="AZE-TL-99018",
        email="tebriz@example.az",
        phone="+994501234567",
        address="Baku, Nizami 45",
        first_name="Tebriz",
        last_name="Latifov",
        kyc_status="verified",
    )
    vehicle = party_service.create_vehicle(
        db_session,
        owner_party_id=party.id,
        vin="WBA5A5C50DD123456",
        registration_number="90-TL-099",
        make="BMW",
        model="528i F10",
        manufacture_year=2022,
        engine_capacity_cc=2000,
        market_value=Decimal("45000.00"),
    )
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 1: Sales Quotation (Agent A1 & Process P01)
    # ---------------------------------------------------------
    lead = sales_service.create_lead(
        db=db_session,
        first_name="Tebriz",
        last_name="Latifov",
        email="tebriz@example.az",
        phone="+994501234567",
        product_code="MOTOR_OD",
        channel="direct_web",
    )
    assert lead.status == "new"

    # Generate Quote with deterministic rating engine
    quote = sales_service.generate_quote(
        db=db_session,
        product_code="MOTOR_OD",
        rating_inputs={
            "vehicle_value": "45000.00",
            "deductible": "200.00",
            "vehicle_age": 4,
            "driver_age": 34,
            "prior_claims_count": 0,
        },
        lead_id=lead.id,
        party_id=party.id,
    )
    assert quote.total_premium > Decimal("0.00")
    assert quote.status in ["draft", "issued", "offered"]
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 2: Underwriting Referral & Approval (Agent A2)
    # ---------------------------------------------------------
    rule_results = evaluate_underwriting_rules(
        product_code="MOTOR_OD",
        sum_insured=quote.sum_insured,
        rating_inputs={"driver_age": 34, "prior_claims_count": 0},
    )
    assert rule_results.required_authority_tier is not None
    uw_case = underwriting_service.create_case_from_quote(
        db=db_session,
        quote_id=quote.id,
        product_code="MOTOR_OD",
        sum_insured=quote.sum_insured,
        proposed_premium=quote.total_premium,
        rating_inputs={"driver_age": 34, "prior_claims_count": 0},
    )
    # Copilot A2 assists underwriter
    uw_case = underwriting_service.run_copilot_assessment(db=db_session, case_id=uw_case.id)
    assert uw_case.copilot_assessment is not None

    # Senior Underwriter approves case (L2 Human-in-the-Loop)
    underwriting_service.record_decision(
        db=db_session,
        case_id=uw_case.id,
        decision="approved",
        underwriter_id="Senior Underwriter Samir",
        underwriter_role="senior",
        notes="Clean vehicle history and premium customer profile.",
    )
    assert uw_case.status == "approved"
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 3: Policy Issuance (Process P02)
    # ---------------------------------------------------------
    start_d = date(2026, 1, 1)
    end_d = date(2026, 12, 31)
    policy = Policy(
        policy_number="POL-GOLDEN-2026-001",
        party_id=party.id,
        asset_id=vehicle.id,
        product_code="MOTOR_OD",
        product_version_id=v1.id,
        status="pending_payment",
        start_date=start_d,
        end_date=end_d,
        sum_insured=quote.sum_insured,
        deductible=quote.deductible,
        total_premium=quote.total_premium,
        paid_premium=Decimal("0.00"),
        payment_schedule=[
            {
                "installment_number": 1,
                "due_date": start_d.isoformat(),
                "amount": str(quote.total_premium),
            }
        ],
    )
    db_session.add(policy)
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 4: Invoicing, Payment Intake & Balanced Ledger (Finance)
    # ---------------------------------------------------------
    invoices = finance_service.create_invoices_for_policy(session=db_session, policy_id=policy.id)
    assert len(invoices) == 1
    invoice = invoices[0]

    # Process Payment
    payment = finance_service.process_incoming_payment(
        session=db_session,
        invoice_id=invoice.id,
        amount=invoice.amount,
        payment_method="bank_transfer",
    )
    assert payment.status == "completed"
    assert policy.status == "active"
    db_session.commit()

    # Verify General Ledger balance invariant (Debits == Credits, Δ = 0.00)
    bal_after_pay = check_ledger_balance(db_session)
    assert bal_after_pay["is_balanced"] is True
    assert bal_after_pay["difference"] == Decimal("0.00")

    # ---------------------------------------------------------
    # STEP 5: Reinsurance Treaty Cession (20% Quota Share)
    # ---------------------------------------------------------
    cessions = reinsurance_service.process_premium_cessions(
        session=db_session,
        policy_id=policy.id,
        policy_number=policy.policy_number,
        product_code="MOTOR_OD",
        gross_premium=policy.total_premium,
    )
    assert len(cessions) >= 1
    assert cessions[0].ceded_premium > Decimal("0.00")
    db_session.commit()

    bal_after_reins = check_ledger_balance(db_session)
    assert bal_after_reins["is_balanced"] is True
    assert bal_after_reins["difference"] == Decimal("0.00")

    # ---------------------------------------------------------
    # STEP 6: Mid-Term Endorsement & Pro-Rata Math (Agent A3, Process P06)
    # ---------------------------------------------------------
    halfway_date = (start_d + timedelta(days=182)).isoformat()
    # Increase valuation to 55000 AZN (+10000 AZN)
    draft_endorsement = policy_servicing_agent.process_endorsement_request(
        session=db_session,
        policy_number=policy.policy_number,
        endorsement_type="INCREASE_SUM_INSURED",
        changes={"new_sum_insured": 55000.0},
        effective_date=halfway_date,
    )
    assert draft_endorsement.requires_underwriter_approval is True
    assert draft_endorsement.autonomy_level == "L2"
    assert draft_endorsement.prorata_adjustment_azn > 0.0

    # Underwriter approves draft
    draft_record = db_session.scalars(
        select(EndorsementDraft).where(EndorsementDraft.policy_id == policy.id)
    ).first()
    assert draft_record is not None
    customer_service_domain.approve_endorsement(
        session=db_session,
        draft_id=draft_record.id,
        underwriter_name="Senior Underwriter Samir",
    )
    db_session.commit()
    assert policy.sum_insured == Decimal("55000.00")

    # ---------------------------------------------------------
    # STEP 7: FNOL Claim Intake, Triage & Reserving (Agent A4)
    # ---------------------------------------------------------
    loss_date = start_d + timedelta(days=200)
    claim = Claim(
        claim_number="CLM-GOLDEN-2026-001",
        policy_id=policy.id,
        policy_number=policy.policy_number,
        incident_date=loss_date,
        notification_date=loss_date + timedelta(days=1),
        claimed_amount=Decimal("42000.00"),  # >70% of 55000 -> CTL (Constructive Total Loss)
        status="fnol_received",
        incident_description="Night single vehicle collision on highway, extensive structural frame damage, police protocol submitted.",
    )
    db_session.add(claim)
    db_session.commit()

    # Post initial loss reserve in General Ledger
    finance_service.record_claim_reserve_movement(
        session=db_session,
        claim_id=claim.id,
        claim_number=claim.claim_number,
        reserve_amount=Decimal("42000.00"),
    )
    db_session.commit()

    bal_after_reserve = check_ledger_balance(db_session)
    assert bal_after_reserve["is_balanced"] is True

    # ---------------------------------------------------------
    # STEP 8: Fraud & SIU Triage (Agent A5 with G8 Neutral Language)
    # ---------------------------------------------------------
    score, signals, siu_case = fraud_service.evaluate_and_route_claim(
        session=db_session,
        claim_id=claim.id,
        has_police_report=True,
        incident_hour=23,
        unwitnessed_single_vehicle=True,
    )
    assert score is not None
    siu_assessment = fraud_assistant_agent.assess_claim_for_siu(
        claim_number=claim.claim_number,
        risk_score=score,
        triggered_signals=signals,
        investigator_notes="Night impact with official protocol and verified damage.",
    )
    assert siu_assessment.g8_neutral_language_verified is True
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 9: Claim Settlement Disbursement & Reserve Clearance
    # ---------------------------------------------------------
    # Net payout: 42000 - 200 (deductible) = 41800 AZN
    disbursement = finance_service.disburse_claim_payout(
        session=db_session,
        claim_id=claim.id,
        claim_number=claim.claim_number,
        payee_party_id=party.id,
        amount=Decimal("41800.00"),
        approved_by="Chief Adjuster Nigar",
    )
    assert disbursement.status == "disbursed"
    claim.status = "settled"
    claim.approved_payout = Decimal("41800.00")
    claim.deductible_applied = Decimal("200.00")
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 10: Reinsurance Loss Recovery (20% of 41800 AZN = 8360 AZN)
    # ---------------------------------------------------------
    recoveries = reinsurance_service.process_claim_recoveries(
        session=db_session,
        claim_id=claim.id,
        claim_number=claim.claim_number,
        product_code="MOTOR_OD",
        gross_loss=Decimal("41800.00"),
        incident_date=loss_date,
    )
    assert len(recoveries) >= 1
    assert recoveries[0].recovered_amount > Decimal("0.00")
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 11: Expiring Policy Scanning & Renewal Advisor (Agent A7, Process P07)
    # ---------------------------------------------------------
    scan_date = end_d - timedelta(days=45)
    renewal_cases = renewal_service.scan_expiring_policies(
        session=db_session,
        as_of_date=scan_date,
        days_ahead=60,
    )
    assert len(renewal_cases) >= 1
    rn_case = [c for c in renewal_cases if c.policy_id == policy.id][0]
    assert rn_case.claims_count >= 1

    # Agent A7 assesses renewal terms with claims surcharge
    rn_eval = renewal_advisor_agent.assess_policy_renewal(
        session=db_session,
        policy_number=policy.policy_number,
        as_of_date=scan_date,
    )
    assert rn_eval.policy_number == policy.policy_number
    assert rn_eval.underwriter_signoff_required is True

    # Policyholder accepts offer
    renewed_policy = renewal_service.accept_renewal(session=db_session, renewal_case_id=rn_case.id)
    assert renewed_policy.status == "pending_payment"
    assert renewed_policy.policy_number.startswith("POL-")
    db_session.commit()

    # ---------------------------------------------------------
    # STEP 12: Absolute Invariant Assertions
    # ---------------------------------------------------------
    # 1. Balanced General Ledger Invariant (100% debits == credits)
    final_balance = check_ledger_balance(db_session)
    assert final_balance["is_balanced"] is True
    assert final_balance["difference"] == Decimal("0.00")
    assert final_balance["total_debits"] == final_balance["total_credits"]
    assert final_balance["total_debits"] > Decimal("0.00")

    # 2. Immutable Audit Trail Completeness
    audit_events = db_session.scalars(select(AuditLog)).all()
    assert len(audit_events) >= 6
    audit_actions = [e.action for e in audit_events]
    assert "gl_transaction_recorded" in audit_actions
    assert "endorsement_applied" in audit_actions

    # 3. Executive KPIs REST Endpoint Verification
    token = create_access_token(subject="chief_exec", role="admin")
    kpi_res = lifecycle_client.get(
        "/api/v1/metrics/executive-kpis", headers={"Authorization": f"Bearer {token}"}
    )
    assert kpi_res.status_code == 200
    kpis = kpi_res.json()
    assert kpis["ledger_is_balanced"] is True
    assert kpis["ledger_balance_delta_azn"] == 0.0
    assert kpis["conversion_rate_percent"] >= 0.0
