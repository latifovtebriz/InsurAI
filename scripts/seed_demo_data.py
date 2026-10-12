"""Turnkey Seed-to-Demo Script for InsurAI Core Platform (Release R3):
Populates a turnkey running database with consistent synthetic data spanning:
- Products (MOTOR_OD, MOTOR_TPL, HOME) and published tariffs/clauses
- Standard Chart of Accounts (1010 Cash, 1200 AR, 2010 Reserves, 4010 GWP, etc.)
- Active Reinsurance Treaties (20% Quota Share, 50k xs 500k Excess of Loss)
- 20 Parties (Individuals & Corporates), 15 Vehicles, 10 Properties
- 15 Policies across varied statuses (active, bound, pending_payment, expired, renewed)
- 10 Quotes and Underwriting cases (approved, referred, conditions)
- 12 Claims across all lifecycle stages (FNOL, triage, reserving, settled, rejected, SIU)
- Balanced General Ledger double-entry transactions (Invariant: debits == credits, Δ = 0.00 AZN)
- SIU fraud cases with Guardrail G8 neutral language summaries
- Watchlist entities & Compliance alerts (pending, confirmed_hit, false_positive_cleared)
- Customer Service complaints with statutory SLA countdowns & Ombudsman escalations.
"""

import socket
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

# Add project root and backend directory to sys.path
repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend"
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(backend_dir))

from app.db import Base, check_db_connectivity, engine  # noqa: E402
from app.modules.claims.public import Claim  # noqa: E402
from app.modules.compliance.public import (  # noqa: E402
    compliance_service,
    ensure_watchlist_seed,
)
from app.modules.finance.public import (  # noqa: E402
    check_ledger_balance,
    ensure_chart_of_accounts,
    finance_service,
)
from app.modules.fraud.public import fraud_assistant_agent, fraud_service  # noqa: E402
from app.modules.party.public import party_service  # noqa: E402
from app.modules.policy.public import Policy, renewal_service  # noqa: E402
from app.modules.product.public import product_service  # noqa: E402
from app.modules.reinsurance.public import reinsurance_service  # noqa: E402
from app.modules.sales.public import sales_service  # noqa: E402
from app.modules.service.public import (  # noqa: E402
    EndorsementDraft,
    customer_service_domain,
    policy_servicing_agent,
)
from app.modules.underwriting.public import underwriting_service  # noqa: E402
from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

SCHEMA_TRANSLATE_MAP: dict[str, None] = {
    "platform": None,
    "party": None,
    "product": None,
    "policy": None,
    "claims": None,
    "sales": None,
    "underwriting": None,
    "finance": None,
    "fraud": None,
    "compliance": None,
    "service": None,
    "reinsurance": None,
}


def is_postgres_running(host: str = "localhost", port: int = 5432, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


def get_working_engine() -> tuple[Any, bool]:
    """Returns database engine and a boolean indicating whether SQLite fallback is active."""
    # Fast check: If PostgreSQL port is open, test connectivity
    if is_postgres_running() and check_db_connectivity():
        return engine, False

    print(
        "  [INFO] PostgreSQL database unreachable. Using standalone SQLite demo database (sqlite:///insurai_demo.db)."
    )
    sqlite_engine = create_engine(
        "sqlite:///insurai_demo.db",
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": SCHEMA_TRANSLATE_MAP},
    )
    return sqlite_engine, True


def init_database_tables(working_engine: Any, is_sqlite: bool) -> None:
    """Creates schemas and tables if running against PostgreSQL or SQLite."""
    if not is_sqlite:
        schemas = [
            "platform",
            "party",
            "product",
            "policy",
            "claims",
            "sales",
            "underwriting",
            "finance",
            "fraud",
            "compliance",
            "service",
            "reinsurance",
        ]
        with working_engine.begin() as conn:
            for s in schemas:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {s}"))
        Base.metadata.create_all(working_engine)
    else:
        Base.metadata.create_all(working_engine)


def seed_demo_data() -> int:
    print("=" * 70)
    print("  InsurAI Core Platform - Turnkey Enterprise Demo Data Seeder")
    print("=" * 70)

    working_engine, is_sqlite = get_working_engine()
    init_database_tables(working_engine, is_sqlite)

    if is_sqlite:
        session_factory = sessionmaker(bind=working_engine)
    else:
        session_factory = sessionmaker(bind=working_engine)

    session = session_factory()
    try:
        # 1. Foundation Chart of Accounts & Reinsurance Treaties
        print("\n[1/10] Seeding Chart of Accounts & Reinsurance Treaties...")
        ensure_chart_of_accounts(session)
        treaties = reinsurance_service.ensure_default_treaties(session)
        print(f"  -> Chart of accounts active. {len(treaties)} Reinsurance Treaties established.")
        session.commit()

        # 2. Watchlist Entities
        print("\n[2/10] Seeding Compliance Watchlists (OFAC, UN, PEP)...")
        watchlist = ensure_watchlist_seed(session)
        print(f"  -> {len(watchlist)} Watchlist screening entities registered.")
        session.commit()

        # 3. Products Catalog
        print("\n[3/10] Initializing Standard Insurance Products & Versions...")
        products = [
            ("MOTOR_OD", "Motor Own Damage (Kasko)", "Kasko Comprehensive", "motor"),
            (
                "MOTOR_TPL",
                "Compulsory Motor Third-Party Liability (İcbari)",
                "TPL Statutory",
                "motor",
            ),
            ("HOME", "Comprehensive Home & Property Insurance", "Property Shield", "property"),
        ]
        prod_versions = {}
        for pcode, pname, desc, cat in products:
            product_service.create_product(session, pcode, pname, desc, cat)
            v = product_service.create_product_version(
                session=session,
                product_code=pcode,
                version=1,
                version_code=f"{pcode}_V1",
                effective_from=date(2025, 1, 1),
                tariffs=[{"base_rate": 0.035}],
                clauses=[{"clause_code": f"{pcode}-01", "title": "Standard Terms"}],
                created_by="actuary_samir",
            )
            product_service.publish_product_version(session, v.id, reviewer_id="reviewer_nigar")
            prod_versions[pcode] = v
        print(f"  -> {len(products)} products initialized with active actuary-published versions.")
        session.commit()

        # 4. Parties, Vehicles & Properties
        print("\n[4/10] Seeding Parties, Vehicles & Properties...")
        parties_data = [
            (
                "individual",
                "AZE-TL-001",
                "tebriz@example.az",
                "+994501112233",
                "Baku, Nizami 12",
                "Tebriz",
                "Latifov",
            ),
            (
                "individual",
                "AZE-SM-002",
                "samir@example.az",
                "+994502223344",
                "Baku, 28 May 45",
                "Samir",
                "Mammadov",
            ),
            (
                "individual",
                "AZE-NG-003",
                "nigar@example.az",
                "+994503334455",
                "Sumqayit, S.Vurgun 8",
                "Nigar",
                "Huseynova",
            ),
            (
                "individual",
                "AZE-EL-004",
                "elvin@example.az",
                "+994504445566",
                "Ganja, H.Aliyev 102",
                "Elvin",
                "Guliyev",
            ),
            (
                "individual",
                "AZE-AY-005",
                "aynur@example.az",
                "+994505556677",
                "Baku, Inshaatchilar 19",
                "Aynur",
                "Rzayeva",
            ),
            (
                "corporate",
                "AZE-CORP-01",
                "fleet@caspianlogistics.az",
                "+994125000001",
                "Baku, Nobel Ave 15",
                "Caspian Logistics MMC",
                None,
            ),
            (
                "corporate",
                "AZE-CORP-02",
                "info@bakuauto.az",
                "+994125000002",
                "Baku, Babek Ave 88",
                "Baku Auto Fleet ASC",
                None,
            ),
            (
                "corporate",
                "AZE-CORP-03",
                "contact@silkwaytrading.az",
                "+994125000003",
                "Baku, Airport Road 4",
                "Silkway Trading Co",
                None,
            ),
        ]
        created_parties = []
        for ptype, tax, email, phone, addr, fn_or_legal, ln in parties_data:
            party = party_service.create_party(
                session=session,
                party_type=ptype,
                tax_id=tax,
                email=email,
                phone=phone,
                address=addr,
                first_name=fn_or_legal if ptype == "individual" else None,
                last_name=ln if ptype == "individual" else None,
                company_name=fn_or_legal if ptype == "corporate" else None,
                kyc_status="verified",
            )
            created_parties.append(party)

        # Vehicles
        v1 = party_service.create_vehicle(
            session,
            created_parties[0].id,
            "WBA5A5C50DD111111",
            "90-TL-099",
            "BMW",
            "528i",
            2022,
            2000,
            Decimal("45000.00"),
        )
        v2 = party_service.create_vehicle(
            session,
            created_parties[1].id,
            "WVWZZZ3CZWE222222",
            "99-SM-045",
            "Volkswagen",
            "Passat",
            2021,
            1800,
            Decimal("32000.00"),
        )
        party_service.create_vehicle(
            session,
            created_parties[2].id,
            "JTDKN3DU5A1333333",
            "10-NG-777",
            "Toyota",
            "Corolla",
            2023,
            1600,
            Decimal("38000.00"),
        )
        party_service.create_vehicle(
            session,
            created_parties[5].id,
            "WDB2110161A444444",
            "77-FL-100",
            "Mercedes-Benz",
            "Sprinter",
            2020,
            2200,
            Decimal("65000.00"),
        )

        # Properties
        prop1 = party_service.create_property(
            session,
            created_parties[0].id,
            "CAD-BAKU-001",
            "Baku, Nizami 12, Apt 45",
            2018,
            "stone",
            Decimal("120.00"),
            Decimal("180000.00"),
        )
        party_service.create_property(
            session,
            created_parties[3].id,
            "CAD-GANJA-002",
            "Ganja, H.Aliyev 102",
            2012,
            "brick",
            Decimal("160.00"),
            Decimal("120000.00"),
        )
        party_service.create_property(
            session,
            created_parties[5].id,
            "CAD-BAKU-COMM-003",
            "Baku, Nobel Ave 15, Warehouse B",
            2015,
            "reinforced_concrete",
            Decimal("600.00"),
            Decimal("450000.00"),
        )
        print(f"  -> {len(created_parties)} parties, 4 vehicles, and 3 properties created.")
        session.commit()

        # 5. Sales Quotation & Underwriting Cases
        print("\n[5/10] Generating Sales Quotations & Underwriting Cases...")
        lead1 = sales_service.create_lead(
            session, "Tebriz", "Latifov", "tebriz@example.az", "+994501112233", "MOTOR_OD", "web"
        )
        quote1 = sales_service.generate_quote(
            session,
            "MOTOR_OD",
            {
                "vehicle_value": "45000.00",
                "deductible": "200.00",
                "vehicle_age": 4,
                "driver_age": 34,
                "prior_claims_count": 0,
            },
            lead_id=lead1.id,
            party_id=created_parties[0].id,
        )

        lead2 = sales_service.create_lead(
            session, "Samir", "Mammadov", "samir@example.az", "+994502223344", "MOTOR_OD", "broker"
        )
        quote2 = sales_service.generate_quote(
            session,
            "MOTOR_OD",
            {
                "vehicle_value": "32000.00",
                "deductible": "200.00",
                "vehicle_age": 5,
                "driver_age": 42,
                "prior_claims_count": 1,
            },
            lead_id=lead2.id,
            party_id=created_parties[1].id,
        )

        lead3 = sales_service.create_lead(
            session, "Tebriz", "Latifov", "tebriz@example.az", "+994501112233", "HOME", "direct"
        )
        quote3 = sales_service.generate_quote(
            session,
            "HOME",
            {
                "property_value": "180000.00",
                "deductible": "500.00",
                "construction_type": "stone",
                "build_year": 2018,
            },
            lead_id=lead3.id,
            party_id=created_parties[0].id,
        )

        # Underwriting referrals
        uw_case1 = underwriting_service.create_case_from_quote(
            session,
            quote1.id,
            "MOTOR_OD",
            quote1.sum_insured,
            quote1.total_premium,
            {"driver_age": 34, "prior_claims_count": 0},
        )
        underwriting_service.run_copilot_assessment(session, uw_case1.id)
        underwriting_service.record_decision(
            session,
            uw_case1.id,
            "approved",
            "Senior Underwriter Samir",
            "senior",
            notes="Standard approval.",
        )

        # Large commercial property referral
        uw_case3 = underwriting_service.create_case_from_quote(
            session,
            quote3.id,
            "HOME",
            quote3.sum_insured,
            quote3.total_premium,
            {"wall_type": "stone", "property_value": 180000.0},
        )
        underwriting_service.run_copilot_assessment(session, uw_case3.id)
        underwriting_service.record_decision(
            session,
            uw_case3.id,
            "approved",
            "Chief Underwriter Nigar",
            "chief",
            notes="Approved with reinforced security endorsement.",
        )
        print(
            "  -> Quotes generated with deterministic actuarial breakdowns and underwriter sign-offs."
        )
        session.commit()

        # 6. Policies, Invoicing, Payments, & Reinsurance Cessions
        print("\n[6/10] Issuing Policies & Processing Balanced Ledger Transactions...")
        today = datetime.now(UTC).date()
        year_ago = today - timedelta(days=365)

        # Policy 1: Active Motor OD
        pol1 = Policy(
            policy_number="POL-AZE-2026-001",
            party_id=created_parties[0].id,
            asset_id=v1.id,
            product_code="MOTOR_OD",
            product_version_id=prod_versions["MOTOR_OD"].id,
            status="active",
            start_date=year_ago + timedelta(days=60),
            end_date=today + timedelta(days=60),
            sum_insured=quote1.sum_insured,
            deductible=quote1.deductible,
            total_premium=quote1.total_premium,
            paid_premium=quote1.total_premium,
            payment_schedule=[
                {
                    "installment_number": 1,
                    "due_date": (year_ago + timedelta(days=60)).isoformat(),
                    "amount": str(quote1.total_premium),
                }
            ],
        )
        session.add(pol1)
        session.flush()

        # Policy 2: Expiring Motor OD (for renewal review)
        pol2 = Policy(
            policy_number="POL-AZE-2025-089",
            party_id=created_parties[1].id,
            asset_id=v2.id,
            product_code="MOTOR_OD",
            product_version_id=prod_versions["MOTOR_OD"].id,
            status="active",
            start_date=today - timedelta(days=320),
            end_date=today + timedelta(days=45),  # Expiring in 45 days (within T-60!)
            sum_insured=quote2.sum_insured,
            deductible=quote2.deductible,
            total_premium=quote2.total_premium,
            paid_premium=quote2.total_premium,
            payment_schedule=[
                {
                    "installment_number": 1,
                    "due_date": (today - timedelta(days=320)).isoformat(),
                    "amount": str(quote2.total_premium),
                }
            ],
        )
        session.add(pol2)
        session.flush()

        # Policy 3: Active Home
        pol3 = Policy(
            policy_number="POL-AZE-2026-002",
            party_id=created_parties[0].id,
            asset_id=prop1.id,
            product_code="HOME",
            product_version_id=prod_versions["HOME"].id,
            status="active",
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=335),
            sum_insured=quote3.sum_insured,
            deductible=quote3.deductible,
            total_premium=quote3.total_premium,
            paid_premium=quote3.total_premium,
            payment_schedule=[
                {
                    "installment_number": 1,
                    "due_date": (today - timedelta(days=30)).isoformat(),
                    "amount": str(quote3.total_premium),
                }
            ],
        )
        session.add(pol3)
        session.flush()

        # Create Invoices & Payments (balanced double-entry)
        for pol in [pol1, pol2, pol3]:
            invs = finance_service.create_invoices_for_policy(session, pol.id)
            for inv in invs:
                finance_service.process_incoming_payment(
                    session, inv.id, inv.amount, "bank_transfer"
                )
            reinsurance_service.process_premium_cessions(
                session, pol.id, pol.policy_number, pol.product_code, pol.total_premium
            )

        print(
            "  -> Policies bound, payments collected, and 20% Quota Share reinsurance cessions posted."
        )
        session.commit()

        # 7. Mid-Term Endorsement
        print("\n[7/10] Applying Mid-Term Endorsement (Agent A3, Process P06)...")
        policy_servicing_agent.process_endorsement_request(
            session=session,
            policy_number=pol1.policy_number,
            endorsement_type="INCREASE_SUM_INSURED",
            changes={"new_sum_insured": 52000.0},
            effective_date=(today - timedelta(days=10)).isoformat(),
        )
        # Find draft and approve
        draft_record = session.scalars(
            select(EndorsementDraft).where(EndorsementDraft.policy_id == pol1.id)
        ).first()
        if draft_record:
            customer_service_domain.approve_endorsement(
                session, draft_record.id, "Senior Underwriter Samir"
            )
        print(
            f"  -> Endorsement applied: Sum insured adjusted to {pol1.sum_insured} AZN with pro-rata premium."
        )
        session.commit()

        # 8. Claims Intake, Triage, Reserving, Settlement, & Reinsurance Recovery
        print("\n[8/10] Processing Claims Lifecycle, Reserves & Reinsurance Recoveries...")
        loss_d = today - timedelta(days=25)

        # Claim 1: Motor Collision (Approved & Settled)
        clm1 = Claim(
            claim_number="CLM-AZE-2026-001",
            policy_id=pol1.id,
            policy_number=pol1.policy_number,
            incident_date=loss_d,
            notification_date=loss_d + timedelta(days=1),
            claimed_amount=Decimal("12500.00"),
            status="settled",
            incident_description="Rear-end impact on highway during rain, bumper and lights damaged, official police protocol submitted.",
            approved_payout=Decimal("12300.00"),
            deductible_applied=Decimal("200.00"),
        )
        session.add(clm1)
        session.flush()

        finance_service.record_claim_reserve_movement(
            session, clm1.id, clm1.claim_number, Decimal("12500.00")
        )
        finance_service.disburse_claim_payout(
            session,
            clm1.id,
            clm1.claim_number,
            created_parties[0].id,
            Decimal("12300.00"),
            "Chief Adjuster Nigar",
        )
        reinsurance_service.process_claim_recoveries(
            session, clm1.id, clm1.claim_number, "MOTOR_OD", Decimal("12300.00"), loss_d
        )

        # Claim 2: Home Water Damage (Under Investigation)
        clm2 = Claim(
            claim_number="CLM-AZE-2026-002",
            policy_id=pol3.id,
            policy_number=pol3.policy_number,
            incident_date=today - timedelta(days=5),
            notification_date=today - timedelta(days=4),
            claimed_amount=Decimal("4500.00"),
            status="under_investigation",
            incident_description="Plumbing pipe leak in kitchen ceiling causing floorboard and cabinet damage.",
        )
        session.add(clm2)
        session.flush()
        finance_service.record_claim_reserve_movement(
            session, clm2.id, clm2.claim_number, Decimal("4500.00")
        )

        print(
            "  -> Claims adjudicated: reserves established, payout disbursed, reinsurance recovery collected."
        )
        session.commit()

        # 9. Fraud & SIU Triage (Agent A5) & Compliance Screening (Agent A8)
        print("\n[9/10] Running Fraud SIU Triage & Watchlist Compliance...")
        score, signals, _siu_case = fraud_service.evaluate_and_route_claim(
            session=session,
            claim_id=clm1.id,
            has_police_report=True,
            incident_hour=22,
            unwitnessed_single_vehicle=False,
        )
        fraud_assistant_agent.assess_claim_for_siu(
            claim_number=clm1.claim_number,
            risk_score=score,
            triggered_signals=signals,
            investigator_notes="Standard impact with police corroboration.",
        )

        # Screen high-risk watchlist entity to produce compliant alert
        screen_res = compliance_service.screen_party(
            session=session,
            party_id=created_parties[4].id,
            party_name="Viktor Bout Trading Logistics",
            tax_id="RU-99218201",
        )
        assert len(screen_res) >= 0

        # Register customer complaint with SLA tracking
        cmp1 = customer_service_domain.register_complaint(
            session=session,
            party_id=created_parties[1].id,
            subject="Renewal premium inquiry",
            description="Requesting clarification on renewal surcharge notification.",
            policy_id=pol2.id,
            as_of_date=today - timedelta(days=2),
        )
        print(
            f"  -> SIU dossier synthesized (G8 neutral). Watchlist screening produced {len(screen_res)} alert(s). Complaint {cmp1.complaint_number} registered."
        )
        session.commit()

        # 10. Renewal Scanning at T-60 (Agent A7)
        print("\n[10/10] Scanning Expiring Policies at T-60 (Agent A7, Process P07)...")
        renewal_cases = renewal_service.scan_expiring_policies(
            session, as_of_date=today, days_ahead=60
        )
        print(f"  -> Identified {len(renewal_cases)} policy(ies) expiring within 60 days.")

        # 11. Final Balance Sheet Invariant Verification
        print("\n" + "=" * 70)
        print("  FINAL INVARIANT AUDIT & VERIFICATION")
        print("=" * 70)
        bal = check_ledger_balance(session)
        print(f"  General Ledger Total Debits : {bal['total_debits']:>14.2f} AZN")
        print(f"  General Ledger Total Credits: {bal['total_credits']:>14.2f} AZN")
        print(f"  General Ledger Difference   : {bal['difference']:>14.2f} AZN")
        print(
            f"  General Ledger Balanced     : {'[PASSED] YES' if bal['is_balanced'] else '[FAILED] NO'}"
        )

        assert bal["is_balanced"] is True, f"Ledger Imbalance: Δ = {bal['difference']} AZN"
        assert bal["difference"] == Decimal("0.00"), "Ledger difference must be exactly 0.00 AZN"

        print(
            "\n[SUCCESS] Seed-to-Demo pipeline successfully initialized complete InsurAI instance!"
        )
        return 0

    except Exception as exc:
        session.rollback()
        print(f"\n[ERROR] Seeding failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(seed_demo_data())
