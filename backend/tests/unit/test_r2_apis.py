"""Unit tests for Phase 11 (Release R2) REST API endpoints: Fraud, Compliance, and Customer Service."""

from datetime import date, timedelta
from decimal import Decimal

from app.modules.claims.public import Claim
from app.modules.platform.public import create_access_token
from app.modules.policy.public import Policy
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_siu_fraud_api_flow(client: TestClient, db_session: Session) -> None:
    token = create_access_token(subject="investigator_elvin", role="siu_investigator")
    headers = {"Authorization": f"Bearer {token}"}

    # Seed policy and claim
    start = date.today() - timedelta(days=20)
    end = start + timedelta(days=365)
    policy = Policy(
        policy_number="POL-SIU-API-001",
        party_id="PARTY-SIU-01",
        asset_id="VEH-SIU-01",
        product_code="MOTOR_OD",
        product_version_id="VER-01",
        status="active",
        start_date=start,
        end_date=end,
        sum_insured=Decimal("40000.00"),
        total_premium=Decimal("1200.00"),
    )
    db_session.add(policy)
    db_session.commit()

    claim = Claim(
        claim_number="CLM-SIU-API-001",
        policy_id=policy.id,
        policy_number=policy.policy_number,
        incident_date=start + timedelta(days=2),  # Inception jump (FS-01)
        notification_date=start + timedelta(days=12),  # Late reporting (FS-02)
        claimed_amount=Decimal("15000.00"),
        status="fnol_received",
        incident_description="Night single-vehicle tree impact, no police report, unwitnessed.",
    )
    db_session.add(claim)
    db_session.commit()

    # 1. POST /api/v1/siu/assess/{claim_number}
    assess_res = client.post(
        f"/api/v1/siu/assess/{claim.claim_number}",
        json={"investigator_notes": "Night impact review"},
        headers=headers,
    )
    assert assess_res.status_code == 200
    data = assess_res.json()
    assert data["claim_number"] == claim.claim_number
    assert data["risk_score"] >= 40
    assert len(data["signals_detected"]) >= 1

    # 2. GET /api/v1/siu/cases
    cases_res = client.get("/api/v1/siu/cases", headers=headers)
    assert cases_res.status_code == 200
    cases = cases_res.json()
    assert isinstance(cases, list)


def test_compliance_aml_api_flow(client: TestClient, db_session: Session) -> None:
    token = create_access_token(subject="officer_leyla", role="compliance_officer")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. POST /api/v1/compliance/screen
    screen_res = client.post(
        "/api/v1/compliance/screen",
        json={
            "party_id": "PARTY-COMP-API-01",
            "party_name": "Viktor Anatolyevich Bout",
            "tax_id": "RU-882910492",
        },
        headers=headers,
    )
    assert screen_res.status_code == 200
    screen_data = screen_res.json()
    assert screen_data["matches_count"] >= 1
    alerts = screen_data["alerts"]
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]

    # 2. GET /api/v1/compliance/alerts
    list_res = client.get("/api/v1/compliance/alerts", headers=headers)
    assert list_res.status_code == 200
    alerts_list = list_res.json()
    assert any(a["id"] == alert_id for a in alerts_list)

    # 3. POST /api/v1/compliance/assess/{alert_id} (Agent A8 analysis)
    assess_res = client.post(f"/api/v1/compliance/assess/{alert_id}", headers=headers)
    assert assess_res.status_code == 200
    analysis = assess_res.json()
    assert analysis["auto_cleared"] is False
    assert analysis["human_signoff_required"] is True
    assert "draft_sar_report" in analysis

    # 4. POST /api/v1/compliance/alerts/{alert_id}/adjudicate (Human officer adjudication)
    adj_res = client.post(
        f"/api/v1/compliance/alerts/{alert_id}/adjudicate",
        json={
            "decision": "confirmed_hit",
            "decision_notes": "Confirmed match with OFAC SDN arms embargo database.",
        },
        headers=headers,
    )
    assert adj_res.status_code == 200
    adj_data = adj_res.json()
    assert adj_data["status"] == "success"
    assert adj_data["alert_status"] == "confirmed_hit"
    assert adj_data["decided_by"] == "officer_leyla"


def test_service_and_servicing_api_flow(client: TestClient, db_session: Session) -> None:
    # 1. POST /api/v1/service/chat - Unauthenticated FAQ
    chat_faq = client.post(
        "/api/v1/service/chat",
        json={"message": "What is the deductible amount?", "is_authenticated": False},
    )
    assert chat_faq.status_code == 200
    faq_data = chat_faq.json()
    assert "200 AZN" in faq_data["reply_text"]
    assert faq_data["data_accessed"] is False

    # 2. POST /api/v1/service/chat - Unauthenticated requesting private policy
    chat_gated = client.post(
        "/api/v1/service/chat",
        json={"message": "Show my policy and sum insured", "is_authenticated": False},
    )
    assert chat_gated.status_code == 200
    gated_data = chat_gated.json()
    assert gated_data["action_taken"] == "PROMPT_AUTHENTICATION"
    assert gated_data["data_accessed"] is False

    # 3. POST /api/v1/service/complaints
    cust_token = create_access_token(subject="cust_ali", role="customer")
    cust_headers = {"Authorization": f"Bearer {cust_token}"}
    complaint_res = client.post(
        "/api/v1/service/complaints",
        json={
            "party_id": "PARTY-CUST-01",
            "subject": "Delayed claim inspection",
            "description": "Adjuster did not show up for scheduled vehicle inspection.",
        },
        headers=cust_headers,
    )
    assert complaint_res.status_code == 200
    comp_data = complaint_res.json()
    assert comp_data["status"] == "registered"
    assert comp_data["sla_breached"] is False
    assert "initial_response_deadline" in comp_data

    # 4. POST /api/v1/service/endorsements/propose
    # Create active policy first
    start = date.today() - timedelta(days=60)
    end = start + timedelta(days=365)
    policy = Policy(
        policy_number="POL-SRV-API-001",
        party_id="PARTY-CUST-01",
        asset_id="VEH-SRV-01",
        product_code="MOTOR_OD",
        product_version_id="VER-01",
        status="active",
        start_date=start,
        end_date=end,
        sum_insured=Decimal("30000.00"),
        total_premium=Decimal("900.00"),
    )
    db_session.add(policy)
    db_session.commit()

    uw_token = create_access_token(subject="uw_samir", role="underwriter")
    uw_headers = {"Authorization": f"Bearer {uw_token}"}

    endorse_res = client.post(
        "/api/v1/service/endorsements/propose",
        json={
            "policy_number": "POL-SRV-API-001",
            "endorsement_type": "INCREASE_SUM_INSURED",
            "effective_date": date.today().isoformat(),
            "changes": {"new_sum_insured": 40000.0},
        },
        headers=uw_headers,
    )
    assert endorse_res.status_code == 200
    draft_data = endorse_res.json()
    assert draft_data["requires_underwriter_approval"] is True
    assert draft_data["autonomy_level"] == "L2"
    assert draft_data["prorata_adjustment_azn"] > 0
