import pytest
from app.modules.compliance.agent import ComplianceExplainerAgent
from app.modules.compliance.matcher import (
    ensure_watchlist_seed,
    screen_entity,
)
from app.modules.compliance.service import ComplianceService


def test_watchlist_matcher_fuzzy_and_exact(db_session):
    # Seed default watchlist
    entities = ensure_watchlist_seed(db_session)
    assert len(entities) >= 5

    # Screen Viktor Anatolyevich Bout (exact)
    matches_exact = screen_entity(
        name="Viktor Anatolyevich Bout",
        tax_id=None,
        watchlist=entities,
        threshold=0.65,
    )
    assert len(matches_exact) >= 1
    assert matches_exact[0]["matched_name"] == "Viktor Anatolyevich Bout"
    assert matches_exact[0]["match_score"] == 1.0

    # Screen with partial name / transliteration
    matches_fuzzy = screen_entity(
        name="Viktor Bout",
        tax_id=None,
        watchlist=entities,
        threshold=0.65,
    )
    assert len(matches_fuzzy) >= 1
    assert matches_fuzzy[0]["matched_name"] == "Viktor Anatolyevich Bout"

    # Screen completely unrelated name
    matches_clean = screen_entity(
        name="Aynur Mammadova",
        tax_id=None,
        watchlist=entities,
        threshold=0.65,
    )
    assert len(matches_clean) == 0


def test_agent_a8_never_clears_match():
    """Verify regulatory constraint: Agent A8 can NEVER auto-clear a watchlist hit."""
    agent = ComplianceExplainerAgent()

    # attempt_auto_clear must fail with PermissionError
    with pytest.raises(PermissionError) as exc_info:
        agent.attempt_auto_clear("CMP-20261012-TEST01")

    assert "strictly forbidden from auto-clearing sanctions match" in str(exc_info.value)
    assert "Mandatory human compliance officer review" in str(exc_info.value)


def test_agent_a8_analysis_generation(db_session):
    service = ComplianceService()

    # Screen entity that produces a hit
    alerts = service.screen_party(
        session=db_session,
        party_id="PARTY-SAR-01",
        party_name="Viktor Anatolyevich Bout",
        tax_id="RU-882910492",
    )
    assert len(alerts) >= 1
    alert = alerts[0]

    agent = ComplianceExplainerAgent()
    explanation = agent.explain_compliance_alert(session=db_session, alert=alert)

    assert explanation.alert_number == alert.alert_number
    assert explanation.matched_entity_name == "Viktor Anatolyevich Bout"
    assert explanation.auto_cleared is False
    assert explanation.human_signoff_required is True
    assert explanation.recommendation == "REFER_TO_HUMAN_COMPLIANCE_OFFICER"
    assert explanation.draft_sar_report is not None
    assert "CONFIDENTIAL COMPLIANCE SAR DRAFT" in explanation.draft_sar_report


def test_human_officer_adjudication(db_session):
    service = ComplianceService()

    alerts = service.screen_party(
        session=db_session,
        party_id="PARTY-VA-01",
        party_name="Global Maritime Logistics Trading Corp",
        tax_id="CY-99182301",
    )
    assert len(alerts) >= 1
    alert_id = alerts[0].id

    # Human officer adjudicates as confirmed_hit
    adjudicated = service.adjudicate_alert(
        session=db_session,
        alert_id=alert_id,
        decision="confirmed_hit",
        officer_id="officer-elena",
        decision_notes="Confirmed match against OFAC SDN maritime transshipment network.",
        user_id="officer-elena",
    )
    assert adjudicated.status == "confirmed_hit"
    assert adjudicated.assigned_officer_id == "officer-elena"
    assert adjudicated.officer_decision_notes is not None
    assert adjudicated.decided_at is not None

    # Test false_positive clearance by officer
    fp_alerts = service.screen_party(
        session=db_session,
        party_id="PARTY-FP-02",
        party_name="Farhad Aliyev Logistics",
        tax_id="AZ-12345678",
    )
    assert len(fp_alerts) >= 1
    fp_id = fp_alerts[0].id

    cleared = service.adjudicate_alert(
        session=db_session,
        alert_id=fp_id,
        decision="false_positive_cleared_by_officer",
        officer_id="officer-togrul",
        decision_notes="Different company, unrelated individuals.",
        user_id="officer-togrul",
    )
    assert cleared.status == "false_positive_cleared_by_officer"
    assert cleared.assigned_officer_id == "officer-togrul"
