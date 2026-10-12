"""Unit tests for Finance, Renewal, and Reinsurance REST API endpoints."""

from datetime import date, timedelta
from decimal import Decimal

from app.modules.finance.public import finance_service
from app.modules.platform.public import create_access_token
from app.modules.policy.public import Policy
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_finance_api_invoices_and_payment(client: TestClient, db_session: Session) -> None:
    """Tests invoice listing and payment processing via REST API."""
    token = create_access_token(subject="fin_user", role="finance_officer")
    headers = {"Authorization": f"Bearer {token}"}

    # Create policy
    policy = Policy(
        policy_number="POL-API-FIN-01",
        party_id="PARTY-01",
        asset_id="VEH-01",
        product_code="MOTOR_OD",
        product_version_id="VER-01",
        status="pending_payment",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        sum_insured=Decimal("20000.00"),
        total_premium=Decimal("600.00"),
        payment_schedule=[{"installment_number": 1, "due_date": "2026-01-01", "amount": "600.00"}],
    )
    db_session.add(policy)
    db_session.commit()

    # Generate invoices
    finance_service.create_invoices_for_policy(db_session, policy.id)
    db_session.commit()

    # 1. GET /api/v1/finance/invoices
    res = client.get("/api/v1/finance/invoices?policy_number=POL-API-FIN-01", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["amount"] == 600.0
    inv_id = data[0]["id"]

    # 2. POST /api/v1/finance/invoices/{id}/pay
    pay_res = client.post(
        f"/api/v1/finance/invoices/{inv_id}/pay",
        json={"amount": 600.0, "payment_method": "bank_transfer"},
        headers=headers,
    )
    assert pay_res.status_code == 200
    pay_data = pay_res.json()
    assert pay_data["status"] == "success"

    # 3. GET /api/v1/finance/ledger/check
    check_res = client.get("/api/v1/finance/ledger/check", headers=headers)
    assert check_res.status_code == 200
    check_data = check_res.json()
    assert check_data["is_balanced"] is True
    assert check_data["difference"] == 0.0

    # 4. GET /api/v1/finance/kpis
    kpi_res = client.get("/api/v1/finance/kpis", headers=headers)
    assert kpi_res.status_code == 200
    kpi_data = kpi_res.json()
    assert kpi_data["gross_written_premium"] == 600.0
    assert kpi_data["cash_balance"] == 600.0


def test_renewal_api_scan_and_assess(client: TestClient, db_session: Session) -> None:
    """Tests renewal scanning and Agent A7 assessment via REST API."""
    token = create_access_token(subject="uw_user", role="underwriter")
    headers = {"Authorization": f"Bearer {token}"}

    today = date(2026, 6, 1)
    pol = Policy(
        policy_number="POL-API-REN-01",
        party_id="PARTY-02",
        asset_id="VEH-02",
        product_code="MOTOR_OD",
        product_version_id="VER-01",
        status="active",
        start_date=today - timedelta(days=320),
        end_date=today + timedelta(days=45),
        sum_insured=Decimal("25000.00"),
        total_premium=Decimal("1000.00"),
    )
    db_session.add(pol)
    db_session.commit()

    # 1. POST /api/v1/renewals/scan
    scan_res = client.post(
        "/api/v1/renewals/scan",
        json={"days_ahead": 60, "as_of_date": today.isoformat()},
        headers=headers,
    )
    assert scan_res.status_code == 200
    assert scan_res.json()["scanned_cases_count"] >= 1

    # 2. GET /api/v1/renewals/cases
    cases_res = client.get("/api/v1/renewals/cases", headers=headers)
    assert cases_res.status_code == 200
    cases_data = cases_res.json()
    assert len(cases_data) >= 1
    case_id = cases_data[0]["id"]

    # 3. POST /api/v1/renewals/assess/{policy_number}
    assess_res = client.post(
        "/api/v1/renewals/assess/POL-API-REN-01",
        json={"message": "Please review my upcoming renewal."},
        headers=headers,
    )
    assert assess_res.status_code == 200
    assess_data = assess_res.json()
    assert assess_data["policy_number"] == "POL-API-REN-01"
    assert assess_data["recommendation"] == "STANDARD_RENEWAL"
    assert assess_data["autonomy_level"] == "L1"

    # 4. POST /api/v1/renewals/cases/{case_id}/offer
    offer_res = client.post(f"/api/v1/renewals/cases/{case_id}/offer", headers=headers)
    assert offer_res.status_code == 200
    assert offer_res.json()["status"] == "success"


def test_reinsurance_api_endpoints(client: TestClient, db_session: Session) -> None:
    """Tests reinsurance treaties and bordereaux endpoints."""
    token = create_access_token(subject="fin_user", role="finance_officer")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /api/v1/reinsurance/treaties
    treaties_res = client.get("/api/v1/reinsurance/treaties", headers=headers)
    assert treaties_res.status_code == 200
    treaties = treaties_res.json()
    assert len(treaties) >= 3

    # 2. GET /api/v1/reinsurance/bordereaux/{treaty_code}
    bord_res = client.get(
        "/api/v1/reinsurance/bordereaux/TREATY-QS-MOTOR-2026",
        headers=headers,
    )
    assert bord_res.status_code == 200
    bord_data = bord_res.json()
    assert bord_data["treaty_code"] == "TREATY-QS-MOTOR-2026"
    assert "summary" in bord_data
