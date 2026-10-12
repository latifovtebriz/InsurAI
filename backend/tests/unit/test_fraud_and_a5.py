"""Unit tests for fraud scoring, SIU routing, Guardrail G9 fairness, and Agent A5 with G8 neutral language."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from app.modules.claims.public import Claim
from app.modules.fraud.public import (
    FairnessViolationError,
    evaluate_fraud_signals,
    fraud_assistant_agent,
    fraud_service,
    sanitize_neutral_language,
    validate_neutral_language,
)
from app.modules.policy.public import Policy
from sqlalchemy.orm import Session


def test_fraud_scoring_and_signals_evaluation() -> None:
    """Tests transparent rule-based fraud scoring across signals FS-01, FS-02, FS-04."""
    today = date(2026, 3, 1)

    # 1. High risk: Inception-to-loss = 5 days (FS-01: +25), Severity = 90% (FS-02: +20), No police report (FS-04: +15)
    score, signals = evaluate_fraud_signals(
        policy_start_date=today - timedelta(days=5),
        incident_date=today,
        notification_date=today + timedelta(days=1),
        claimed_amount=Decimal("27000.00"),
        sum_insured=Decimal("30000.00"),
        prior_claims_count=0,
        has_police_report=False,
    )
    assert score == 60  # 25 + 20 + 15
    assert len(signals) == 3
    codes = [s["code"] for s in signals]
    assert "FS-01" in codes
    assert "FS-02" in codes
    assert "FS-04" in codes


def test_guardrail_g9_fairness_enforcement() -> None:
    """Guardrail G9: Asserts that passing protected demographic attributes raises FairnessViolationError."""
    today = date(2026, 3, 1)

    with pytest.raises(FairnessViolationError, match="Guardrail G9 violation"):
        evaluate_fraud_signals(
            policy_start_date=today - timedelta(days=30),
            incident_date=today,
            notification_date=today,
            claimed_amount=Decimal("5000.00"),
            sum_insured=Decimal("25000.00"),
            metadata={"gender": "male", "postal_code": "AZ1000"},
        )


def test_automatic_siu_case_routing(db_session: Session) -> None:
    """Verifies that high-risk claims (score >= 70) automatically route to SIU case."""
    today = date(2026, 3, 1)

    pol = Policy(
        policy_number="POL-FRAUD-01",
        party_id="PARTY-01",
        asset_id="VEH-01",
        product_code="MOTOR_OD",
        product_version_id="VER-01",
        status="active",
        start_date=today - timedelta(days=6),
        end_date=today + timedelta(days=359),
        sum_insured=Decimal("30000.00"),
        total_premium=Decimal("1200.00"),
    )
    claim = Claim(
        claim_number="CLM-FRAUD-01",
        policy_id=pol.id,
        policy_number=pol.policy_number,
        incident_date=today,
        notification_date=today + timedelta(days=5),  # Late notification: FS-05 (+15)
        status="registered",
        claimed_amount=Decimal("28000.00"),  # >80% sum insured: FS-02 (+20)
        incident_description="Nighttime rollover",
    )
    db_session.add_all([pol, claim])
    db_session.flush()

    # Early inception (+25) + High severity (+20) + No police report (+15) + Late FNOL (+15) = 75 points!
    score, signals, siu_case = fraud_service.evaluate_and_route_claim(
        session=db_session,
        claim_id=claim.id,
        has_police_report=False,
    )
    assert score >= 70
    assert siu_case is not None
    assert siu_case.status == "open"
    assert siu_case.claim_number == "CLM-FRAUD-01"


def test_agent_a5_guardrail_g8_neutral_language() -> None:
    """Guardrail G8: Asserts that accusatory words are strictly forbidden and sanitized into neutral phrasing."""
    # 1. Direct validation check
    is_neutral, violations = validate_neutral_language(
        "This fraudster committed insurance fraud with a staged crime."
    )
    assert is_neutral is False
    assert len(violations) >= 3

    # 2. Sanitization check
    accusatory_text = "The claimant is a fraudster who staged a fake crash to scam the company."
    sanitized = sanitize_neutral_language(accusatory_text)
    is_clean, remaining = validate_neutral_language(sanitized)
    assert is_clean is True
    assert len(remaining) == 0
    assert "fraudster" not in sanitized
    assert "scam" not in sanitized

    # 3. Agent A5 dossier output verification
    dossier = fraud_assistant_agent.assess_claim_for_siu(
        claim_number="CLM-2026-TEST",
        risk_score=75,
        triggered_signals=[{"name": "Early Claim Inception", "weight": 25}],
        investigator_notes="Suspected fraud and staged accident.",
    )
    assert dossier.g8_neutral_language_verified is True
    assert "fraud" not in dossier.neutral_findings_summary.lower()
    assert "staged" not in dossier.neutral_findings_summary.lower()
