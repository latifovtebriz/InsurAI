"""Unit and integration tests for API v1 REST endpoints."""

from datetime import date
from decimal import Decimal

import pytest
from app.modules.party.public import party_service
from app.modules.policy.public import policy_service
from app.modules.product.public import product_service
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def auth_header(client: TestClient) -> dict[str, str]:
    """Authenticates as demo admin and returns the Bearer auth header."""
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded_policy(db_session: Session) -> str:
    """Seeds a party, product, and bound policy, returning the policy number."""
    # Seed product
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

    # Seed party
    party = party_service.create_party(
        db_session,
        party_type="individual",
        tax_id="AZE1234567",
        email="fuad@example.az",
        phone="+994501112233",
        address="Baku, Nizami st.",
        first_name="Fuad",
        last_name="Huseynov",
        kyc_status="verified",
    )
    vehicle = party_service.create_vehicle(
        db_session,
        owner_party_id=party.id,
        vin="VF1ABC12345678901",
        registration_number="10-AA-100",
        make="Toyota",
        model="Camry",
        manufacture_year=2022,
        engine_capacity_cc=2500,
        market_value=Decimal("45000.00"),
    )

    policy = policy_service.issue_policy(
        session=db_session,
        party_id=party.id,
        asset_id=vehicle.id,
        product_code="MOTOR_OD",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        sum_insured=Decimal("45000.00"),
        total_premium=Decimal("1350.00"),
        deductible=Decimal("200.00"),
    )
    return policy.policy_number


def test_auth_flow(client: TestClient) -> None:
    """Tests demo login and user profile inspection."""
    # Invalid password
    bad_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert bad_resp.status_code == 401

    # Valid demo admin login
    resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "admin"

    # Profile me
    token = data["access_token"]
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "admin"


def test_policy_endpoints(
    client: TestClient, auth_header: dict[str, str], seeded_policy: str
) -> None:
    """Tests listing and retrieving policy details."""
    # List policies
    list_resp = client.get("/api/v1/policies", headers=auth_header)
    assert list_resp.status_code == 200
    policies = list_resp.json()
    assert len(policies) >= 1
    assert any(p["policy_number"] == seeded_policy for p in policies)

    # Detail
    detail_resp = client.get(f"/api/v1/policies/{seeded_policy}", headers=auth_header)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["policy_number"] == seeded_policy
    assert detail["status"] in ["pending_payment", "active"]
    assert detail["certificate_hash"] is not None
    assert detail["holder_info"]["full_name"] == "Fuad Huseynov"


def test_claims_lifecycle_api(
    client: TestClient, auth_header: dict[str, str], seeded_policy: str
) -> None:
    """Tests FNOL intake, claims queue, triage execution, and adjuster decision via REST API."""
    # 1. Submit FNOL
    fnol_payload = {
        "policy_number": seeded_policy,
        "incident_date": "2026-05-15",
        "claimed_amount": 850.0,
        "incident_description": "Minor bumper scrape in parking garage.",
        "product_code": "MOTOR_OD",
        "documents": [
            {
                "type": "police_report",
                "file_name": "police.pdf",
                "content": "Police confirmed no third party involvement.",
            }
        ],
    }
    fnol_resp = client.post("/api/v1/claims/fnol", json=fnol_payload, headers=auth_header)
    assert fnol_resp.status_code == 201
    claim_summary = fnol_resp.json()
    claim_num = claim_summary["claim_number"]
    assert claim_num.startswith("CLM-2026-")
    assert claim_summary["status"] == "registered"

    # 2. List claims queue
    queue_resp = client.get("/api/v1/claims", headers=auth_header)
    assert queue_resp.status_code == 200
    assert any(c["claim_number"] == claim_num for c in queue_resp.json())

    # 3. Retrieve claim detail
    detail_resp = client.get(f"/api/v1/claims/{claim_num}", headers=auth_header)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["claimed_amount"] == 850.0
    assert len(detail["documents"]) == 1
    assert len(detail["reserves"]) >= 1

    # 4. Trigger Triage (simulated via A4 agent)
    triage_resp = client.post(f"/api/v1/claims/{claim_num}/triage", headers=auth_header)
    assert triage_resp.status_code == 200
    triaged_data = triage_resp.json()
    assert triaged_data["status"] in ["triage_in_progress", "awaiting_review", "approved"]

    # 5. Record Adjuster Decision
    decision_payload = {
        "decision": "approve",
        "approved_payout": 650.0,
        "notes": "Verified parking scrape, deductible 200 AZN applied properly.",
        "override_reason": None,
    }
    decision_resp = client.post(
        f"/api/v1/claims/{claim_num}/decision", json=decision_payload, headers=auth_header
    )
    assert decision_resp.status_code == 200
    assert decision_resp.json()["status"] == "approved"
    assert decision_resp.json()["approved_payout"] == 650.0

    # 6. Settle Claim
    settle_resp = client.post(f"/api/v1/claims/{claim_num}/settle", headers=auth_header)
    assert settle_resp.status_code == 200
    assert settle_resp.json()["status"] == "settled"


def test_metrics_endpoints(
    client: TestClient, auth_header: dict[str, str], seeded_policy: str
) -> None:
    """Tests operational metrics and eval report endpoints."""
    # Metrics
    m_resp = client.get("/api/v1/metrics", headers=auth_header)
    assert m_resp.status_code == 200
    m_data = m_resp.json()
    assert m_data["total_policies"] >= 1
    assert "claims_by_status" in m_data

    # Evals
    e_resp = client.get("/api/v1/metrics/evals/latest", headers=auth_header)
    assert e_resp.status_code == 200
    e_data = e_resp.json()
    assert e_data["claims_triage_dev_eval"] is not None
