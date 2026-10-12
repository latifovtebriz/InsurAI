"""Integration tests for Sales and Underwriting REST API endpoints."""

from decimal import Decimal

from app.modules.underwriting.public import underwriting_service
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_sales_and_underwriting_api_lifecycle(client: TestClient, db_session: Session) -> None:
    # 1. Login as underwriter
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "underwriter", "password": "password"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Quote via API
    quote_payload = {
        "product_code": "MOTOR_OD",
        "vehicle_value": 35000.0,
        "vehicle_age": 2,
        "driver_age": 30,
        "prior_claims_count": 0,
        "deductible": 200.0,
    }
    q_resp = client.post("/api/v1/sales/quotes", json=quote_payload, headers=headers)
    assert q_resp.status_code == 201
    q_data = q_resp.json()
    quote_num = q_data["quote_number"]
    assert q_data["status"] == "offered"
    assert q_data["total_premium"] > 0

    # 3. List Quotes
    list_resp = client.get("/api/v1/sales/quotes", headers=headers)
    assert list_resp.status_code == 200
    assert any(q["quote_number"] == quote_num for q in list_resp.json())

    # 4. Chat with A1 Quote Assistant
    chat_resp = client.post(
        "/api/v1/sales/chat",
        json={"message": "Can I get a quote for a 2023 Toyota Corolla valued at 35,000 AZN? I am 30 years old with 8 years driving experience."},
        headers=headers,
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["status"] == "success"
    assert "premium is exactly" in chat_data["message"]

    # 5. Create Underwriting Case for Referral
    uw_case = underwriting_service.create_case_from_quote(
        db=db_session,
        quote_id=quote_num,
        product_code="MOTOR_OD",
        sum_insured=Decimal("110000.00"),  # High exposure referral
        proposed_premium=Decimal("3850.00"),
        rating_inputs={"driver_age": 28, "prior_claims_count": 0},
    )
    db_session.commit()

    # 6. List Underwriting Cases
    uw_list = client.get("/api/v1/underwriting/cases", headers=headers)
    assert uw_list.status_code == 200
    assert any(c["case_number"] == uw_case.case_number for c in uw_list.json())

    # 7. Run A2 Copilot Assessment
    assess_resp = client.post(f"/api/v1/underwriting/cases/{uw_case.id}/assess", headers=headers)
    assert assess_resp.status_code == 200
    assess_data = assess_resp.json()
    assert assess_data["copilot_assessment"] is not None
    assert len(assess_data["copilot_assessment"]["cited_guidelines"]) > 0

    # 8. Submit Underwriter Decision (login as admin/senior underwriter for senior tier approval)
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    dec_payload = {
        "decision": "approved_with_conditions",
        "conditions": ["Mandatory GPS tracker installation."],
        "notes": "Approved with telematic tracker warranty.",
    }
    dec_resp = client.post(
        f"/api/v1/underwriting/cases/{uw_case.id}/decision",
        json=dec_payload,
        headers=admin_headers,
    )
    assert dec_resp.status_code == 200
    dec_data = dec_resp.json()
    assert dec_data["status"] == "approved_with_conditions"
    assert dec_data["underwriter_decision"]["decision"] == "approved_with_conditions"
