"""End-to-end golden journey integration test.
Simulates full operator workflow:
1. Health & readiness checks
2. Adjuster authentication & RBAC profile check
3. Policy portfolio query
4. FNOL intake & claim registration
5. A4 Agent ReAct triage execution (with citations & payout engine)
6. Agent trace inspection
7. Adjuster review & approval with mandatory rationale
8. Claim settlement & reserve clearance
9. Audit trail verification
10. Operational metrics & eval reporting
"""

from collections.abc import Generator
from datetime import date
from decimal import Decimal

import pytest
from app.db import get_db
from app.main import app
from app.modules.party.public import party_service
from app.modules.policy.public import policy_service
from app.modules.product.public import product_service
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def e2e_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client bound to isolated test database session."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def e2e_seed_data(db_session: Session) -> dict[str, str]:
    """Sets up product, verified party, vehicle, and active bound policy."""
    # Product
    product_service.create_product(db_session, "MOTOR_OD", "Motor OD", "Kasko", "motor")
    v2 = product_service.create_product_version(
        db_session,
        "MOTOR_OD",
        2,
        "MOD_V2",
        date(2026, 1, 1),
        tariffs=[],
        clauses=[],
        created_by="actuary_samir",
    )
    product_service.publish_product_version(db_session, v2.id, reviewer_id="reviewer_nigar")

    # Party
    party = party_service.create_party(
        db_session,
        party_type="individual",
        tax_id="FIN9876543",
        email="elmir.qasimov@example.az",
        phone="+994503334455",
        address="Baku, Rashid Behbudov 15",
        first_name="Elmir",
        last_name="Qasimov",
        kyc_status="verified",
    )

    # Vehicle
    vehicle = party_service.create_vehicle(
        db_session,
        owner_party_id=party.id,
        vin="VF1KASKO202600199",
        registration_number="90-AZ-777",
        make="Hyundai",
        model="Elantra",
        manufacture_year=2023,
        engine_capacity_cc=2000,
        market_value=Decimal("38000.00"),
    )

    # Policy
    policy = policy_service.issue_policy(
        session=db_session,
        party_id=party.id,
        asset_id=vehicle.id,
        product_code="MOTOR_OD",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        sum_insured=Decimal("38000.00"),
        total_premium=Decimal("1140.00"),
        deductible=Decimal("200.00"),
    )

    return {
        "policy_number": policy.policy_number,
        "party_name": "Elmir Qasimov",
        "vehicle_plate": "90-AZ-777",
    }


def test_flagship_claims_golden_journey(
    e2e_client: TestClient,
    e2e_seed_data: dict[str, str],
) -> None:
    """Exercises the complete lifecycle from FNOL to final settlement."""
    policy_num = e2e_seed_data["policy_number"]

    # -------------------------------------------------------------------------
    # Step 1: Health probe
    # -------------------------------------------------------------------------
    health_resp = e2e_client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # -------------------------------------------------------------------------
    # Step 2: Adjuster Login
    # -------------------------------------------------------------------------
    login_resp = e2e_client.post(
        "/api/v1/auth/login",
        json={"username": "adjuster", "password": "password"},
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    token = login_data["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    me_resp = e2e_client.get("/api/v1/auth/me", headers=auth_header)
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "adjuster"

    # -------------------------------------------------------------------------
    # Step 3: Query Policy
    # -------------------------------------------------------------------------
    policy_resp = e2e_client.get(f"/api/v1/policies/{policy_num}", headers=auth_header)
    assert policy_resp.status_code == 200
    p_data = policy_resp.json()
    assert p_data["policy_number"] == policy_num
    assert p_data["sum_insured"] == 38000.0
    assert p_data["holder_info"]["full_name"] == "Elmir Qasimov"

    # -------------------------------------------------------------------------
    # Step 4: Submit FNOL
    # -------------------------------------------------------------------------
    fnol_payload = {
        "policy_number": policy_num,
        "incident_date": "2026-06-10",
        "claimed_amount": 1250.0,
        "incident_description": "Driver hit stationary barrier while parking. Left front wing deformed.",
        "product_code": "MOTOR_OD",
        "documents": [
            {
                "type": "police_protocol",
                "file_name": "traffic_police_report.pdf",
                "content": "Protocol #9912. Driver Elmir Qasimov sober, valid license, sole vehicle involved in barrier scrape.",
            }
        ],
    }
    fnol_resp = e2e_client.post("/api/v1/claims/fnol", json=fnol_payload, headers=auth_header)
    assert fnol_resp.status_code == 201
    claim_summary = fnol_resp.json()
    claim_num = claim_summary["claim_number"]
    assert claim_summary["status"] == "registered"

    # -------------------------------------------------------------------------
    # Step 5: Verify Queue Listing
    # -------------------------------------------------------------------------
    queue_resp = e2e_client.get("/api/v1/claims", headers=auth_header)
    assert queue_resp.status_code == 200
    queue = queue_resp.json()
    matching = [c for c in queue if c["claim_number"] == claim_num]
    assert len(matching) == 1

    # -------------------------------------------------------------------------
    # Step 6: Trigger A4 Agent Triage
    # -------------------------------------------------------------------------
    triage_resp = e2e_client.post(f"/api/v1/claims/{claim_num}/triage", headers=auth_header)
    assert triage_resp.status_code == 200
    triaged = triage_resp.json()
    assert triaged["triage_recommendation"] is not None
    rec = triaged["triage_recommendation"]
    assert rec["recommendation"] in ["approve", "needs_human_review"]
    assert rec["confidence"] > 0.50
    # Net payable calculation = 1250 - 200 (deductible) = 1050 AZN
    if rec.get("payout"):
        assert rec["payout"]["deductible"] == 200.0
        assert rec["payout"]["payable"] == 1050.0

    # -------------------------------------------------------------------------
    # Step 7: Inspect Execution Trace
    # -------------------------------------------------------------------------
    trace_resp = e2e_client.get(f"/api/v1/traces/triage-{claim_num}", headers=auth_header)
    assert trace_resp.status_code == 200
    trace = trace_resp.json()
    assert trace["correlation_id"] == f"triage-{claim_num}"
    assert len(trace["steps"]) > 0

    # -------------------------------------------------------------------------
    # Step 8: Adjuster Manual Adjudication
    # -------------------------------------------------------------------------
    decision_payload = {
        "decision": "approve",
        "approved_payout": 1050.0,
        "notes": "Verified parking barrier collision; deductible 200 AZN applied; payout 1050 AZN confirmed.",
        "override_reason": None,
    }
    dec_resp = e2e_client.post(
        f"/api/v1/claims/{claim_num}/decision",
        json={**decision_payload},
        headers=auth_header,
    )
    assert dec_resp.status_code == 200
    dec_data = dec_resp.json()
    assert dec_data["status"] == "approved"
    assert dec_data["approved_payout"] == 1050.0

    # -------------------------------------------------------------------------
    # Step 9: Settle Claim
    # -------------------------------------------------------------------------
    settle_resp = e2e_client.post(f"/api/v1/claims/{claim_num}/settle", headers=auth_header)
    assert settle_resp.status_code == 200
    settled_data = settle_resp.json()
    assert settled_data["status"] == "settled"

    # -------------------------------------------------------------------------
    # Step 10: Audit Trail & Operational Metrics Verification
    # -------------------------------------------------------------------------
    audit_resp = e2e_client.get(
        f"/api/v1/audit?entity_id={settled_data['id']}", headers=auth_header
    )
    assert audit_resp.status_code == 200
    actions = [a["action"] for a in audit_resp.json()]
    assert "claim.settled" in actions

    # Operational Metrics
    metrics_resp = e2e_client.get("/api/v1/metrics", headers=auth_header)
    assert metrics_resp.status_code == 200
    m = metrics_resp.json()
    assert m["total_claims"] >= 1
    assert m["total_paid_out_azn"] >= 1050.0
