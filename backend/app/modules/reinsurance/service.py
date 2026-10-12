"""Reinsurance treaty management, cessions, loss recoveries, and bordereaux reporting."""

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.modules.finance.public import finance_service
from app.modules.reinsurance.models import (
    ReinsuranceCession,
    ReinsuranceRecovery,
    ReinsuranceTreaty,
)
from sqlalchemy import select
from sqlalchemy.orm import Session


def quantize_money(amount: Decimal | float | int | str) -> Decimal:
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


DEFAULT_TREATIES = [
    {
        "treaty_code": "TREATY-QS-MOTOR-2026",
        "treaty_name": "Motor Own Damage 20% Quota Share Treaty",
        "treaty_type": "QUOTA_SHARE",
        "product_code": "MOTOR_OD",
        "reinsurer_name": "Swiss Re Europe S.A.",
        "retention_share_pct": Decimal("0.8000"),
        "ceded_share_pct": Decimal("0.2000"),
        "retention_amount": Decimal("0.00"),
        "treaty_limit": Decimal("100000.00"),
        "start_date": date(2025, 1, 1),
        "end_date": date(2027, 12, 31),
    },
    {
        "treaty_code": "TREATY-XOL-MOTOR-2026",
        "treaty_name": "Motor Catastrophic 50k xs 500k Excess of Loss Treaty",
        "treaty_type": "EXCESS_OF_LOSS",
        "product_code": "MOTOR_OD",
        "reinsurer_name": "Munich Reinsurance Company",
        "retention_share_pct": Decimal("1.0000"),
        "ceded_share_pct": Decimal("0.0000"),
        "retention_amount": Decimal("50000.00"),
        "treaty_limit": Decimal("500000.00"),
        "start_date": date(2025, 1, 1),
        "end_date": date(2027, 12, 31),
    },
    {
        "treaty_code": "TREATY-QS-HOME-2026",
        "treaty_name": "Property & Home 30% Quota Share Treaty",
        "treaty_type": "QUOTA_SHARE",
        "product_code": "HOME",
        "reinsurer_name": "Hannover Rück SE",
        "retention_share_pct": Decimal("0.7000"),
        "ceded_share_pct": Decimal("0.3000"),
        "retention_amount": Decimal("0.00"),
        "treaty_limit": Decimal("250000.00"),
        "start_date": date(2025, 1, 1),
        "end_date": date(2027, 12, 31),
    },
]


class ReinsuranceService:
    """Handles treaty administration, premium cessions, claims recovery, and bordereaux."""

    def ensure_default_treaties(self, session: Session) -> list[ReinsuranceTreaty]:
        """Ensures standard market treaties are initialized in the database."""
        treaties: list[ReinsuranceTreaty] = []
        for defn in DEFAULT_TREATIES:
            existing = session.scalars(
                select(ReinsuranceTreaty).where(
                    ReinsuranceTreaty.treaty_code == defn["treaty_code"]
                )
            ).first()
            if not existing:
                treaty = ReinsuranceTreaty(
                    treaty_code=defn["treaty_code"],
                    treaty_name=defn["treaty_name"],
                    treaty_type=defn["treaty_type"],
                    product_code=defn["product_code"],
                    reinsurer_name=defn["reinsurer_name"],
                    retention_share_pct=defn["retention_share_pct"],
                    ceded_share_pct=defn["ceded_share_pct"],
                    retention_amount=defn["retention_amount"],
                    treaty_limit=defn["treaty_limit"],
                    start_date=defn["start_date"],
                    end_date=defn["end_date"],
                    is_active=True,
                )
                session.add(treaty)
                treaties.append(treaty)
            else:
                treaties.append(existing)
        session.flush()
        return treaties

    def process_premium_cessions(
        self,
        session: Session,
        policy_id: str,
        policy_number: str,
        product_code: str,
        gross_premium: Decimal,
        cession_date: date | None = None,
        user_id: str | None = None,
    ) -> list[ReinsuranceCession]:
        """
        Calculates premium cessions under active Quota Share treaties and records GL entries.
        Debit: Ceded Reinsurance Premium (4020)
        Credit: Reinsurance Payable (2040)
        """
        self.ensure_default_treaties(session)
        c_date = cession_date or datetime.now(UTC).date()

        stmt = select(ReinsuranceTreaty).where(
            ReinsuranceTreaty.is_active == True,  # noqa: E712
            ReinsuranceTreaty.treaty_type == "QUOTA_SHARE",
            ReinsuranceTreaty.product_code.in_([product_code, "ALL"]),
            ReinsuranceTreaty.start_date <= c_date,
            ReinsuranceTreaty.end_date >= c_date,
        )
        treaties = session.scalars(stmt).all()
        cessions: list[ReinsuranceCession] = []

        for treaty in treaties:
            # Check existing cession for this policy and treaty
            existing = session.scalars(
                select(ReinsuranceCession).where(
                    ReinsuranceCession.treaty_id == treaty.id,
                    ReinsuranceCession.policy_id == policy_id,
                )
            ).first()
            if existing:
                continue

            gross = quantize_money(gross_premium)
            ceded = quantize_money(gross * treaty.ceded_share_pct)
            net = quantize_money(gross - ceded)

            cession = ReinsuranceCession(
                treaty_id=treaty.id,
                treaty_code=treaty.treaty_code,
                policy_id=policy_id,
                policy_number=policy_number,
                gross_premium=gross,
                ceded_premium=ceded,
                net_premium=net,
                cession_date=c_date,
            )
            session.add(cession)
            cessions.append(cession)

            # Record GL journal for reinsurance cession
            entries = [
                {"account_code": "4020", "debit": ceded, "credit": Decimal("0.00")},
                {"account_code": "2040", "debit": Decimal("0.00"), "credit": ceded},
            ]
            finance_service.record_gl_transaction(
                session=session,
                reference_type="REINSURANCE_CESSION",
                reference_id=policy_number,
                description=f"Premium cession ({float(treaty.ceded_share_pct) * 100:.0f}%) under treaty {treaty.treaty_code} for Policy {policy_number}",
                entries=entries,
                transaction_date=c_date,
                user_id=user_id,
            )

        session.flush()
        return cessions

    def process_claim_recoveries(
        self,
        session: Session,
        claim_id: str,
        claim_number: str,
        product_code: str,
        gross_loss: Decimal,
        incident_date: date | None = None,
        user_id: str | None = None,
    ) -> list[ReinsuranceRecovery]:
        """
        Calculates loss recoveries under Quota Share and Excess of Loss treaties.
        Posts GL entries:
        Debit: Reinsurance Recoverable (1300)
        Credit: Reinsurance Loss Recoveries (5030)
        """
        self.ensure_default_treaties(session)
        i_date = incident_date or datetime.now(UTC).date()
        gross = quantize_money(gross_loss)

        stmt = select(ReinsuranceTreaty).where(
            ReinsuranceTreaty.is_active == True,  # noqa: E712
            ReinsuranceTreaty.product_code.in_([product_code, "ALL"]),
            ReinsuranceTreaty.start_date <= i_date,
            ReinsuranceTreaty.end_date >= i_date,
        )
        treaties = session.scalars(stmt).all()
        recoveries: list[ReinsuranceRecovery] = []

        for treaty in treaties:
            # Check existing recovery
            existing = session.scalars(
                select(ReinsuranceRecovery).where(
                    ReinsuranceRecovery.treaty_id == treaty.id,
                    ReinsuranceRecovery.claim_id == claim_id,
                )
            ).first()
            if existing:
                continue

            retention_deducted = Decimal("0.00")
            recovered_amount = Decimal("0.00")

            if treaty.treaty_type == "QUOTA_SHARE":
                recovered_amount = quantize_money(gross * treaty.ceded_share_pct)
                retention_deducted = quantize_money(gross - recovered_amount)
            elif treaty.treaty_type == "EXCESS_OF_LOSS":
                if gross > treaty.retention_amount:
                    attachable = gross - treaty.retention_amount
                    recovered_amount = quantize_money(min(attachable, treaty.treaty_limit))
                    retention_deducted = treaty.retention_amount
                else:
                    retention_deducted = gross
                    recovered_amount = Decimal("0.00")

            if recovered_amount > Decimal("0.00"):
                net_loss = quantize_money(gross - recovered_amount)
                recovery = ReinsuranceRecovery(
                    treaty_id=treaty.id,
                    treaty_code=treaty.treaty_code,
                    claim_id=claim_id,
                    claim_number=claim_number,
                    gross_loss=gross,
                    retention_deducted=retention_deducted,
                    recovered_amount=recovered_amount,
                    net_loss=net_loss,
                    status="accrued",
                )
                session.add(recovery)
                recoveries.append(recovery)

                # Post GL journal for reinsurance recovery
                entries = [
                    {"account_code": "1300", "debit": recovered_amount, "credit": Decimal("0.00")},
                    {"account_code": "5030", "debit": Decimal("0.00"), "credit": recovered_amount},
                ]
                finance_service.record_gl_transaction(
                    session=session,
                    reference_type="REINSURANCE_RECOVERY",
                    reference_id=claim_number,
                    description=f"Reinsurance loss recovery from {treaty.reinsurer_name} under treaty {treaty.treaty_code} for Claim {claim_number}",
                    entries=entries,
                    transaction_date=i_date,
                    user_id=user_id,
                )

        session.flush()
        return recoveries

    def generate_bordereau_report(
        self,
        session: Session,
        treaty_code: str,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> dict[str, Any]:
        """
        Generates structured monthly/quarterly bordereau statement for treaty reinsurers.
        """
        treaty = session.scalars(
            select(ReinsuranceTreaty).where(ReinsuranceTreaty.treaty_code == treaty_code)
        ).first()
        if not treaty:
            raise ValueError(f"Treaty with code '{treaty_code}' not found.")

        p_start = period_start or treaty.start_date
        p_end = period_end or treaty.end_date

        cessions_stmt = select(ReinsuranceCession).where(
            ReinsuranceCession.treaty_id == treaty.id,
            ReinsuranceCession.cession_date >= p_start,
            ReinsuranceCession.cession_date <= p_end,
        )
        cessions = session.scalars(cessions_stmt).all()

        recoveries_stmt = select(ReinsuranceRecovery).where(
            ReinsuranceRecovery.treaty_id == treaty.id,
        )
        recoveries = session.scalars(recoveries_stmt).all()

        total_gross_prem = quantize_money(sum((c.gross_premium for c in cessions), Decimal("0.00")))
        total_ceded_prem = quantize_money(sum((c.ceded_premium for c in cessions), Decimal("0.00")))
        total_net_prem = quantize_money(sum((c.net_premium for c in cessions), Decimal("0.00")))

        total_gross_loss = quantize_money(sum((r.gross_loss for r in recoveries), Decimal("0.00")))
        total_recovered_loss = quantize_money(
            sum((r.recovered_amount for r in recoveries), Decimal("0.00"))
        )
        total_net_loss = quantize_money(sum((r.net_loss for r in recoveries), Decimal("0.00")))

        return {
            "treaty_code": treaty.treaty_code,
            "treaty_name": treaty.treaty_name,
            "treaty_type": treaty.treaty_type,
            "reinsurer_name": treaty.reinsurer_name,
            "period_start": p_start.isoformat(),
            "period_end": p_end.isoformat(),
            "summary": {
                "cessions_count": len(cessions),
                "total_gross_premium": total_gross_prem,
                "total_ceded_premium": total_ceded_prem,
                "total_net_premium": total_net_prem,
                "recoveries_count": len(recoveries),
                "total_gross_loss": total_gross_loss,
                "total_recovered_claims": total_recovered_loss,
                "total_net_loss": total_net_loss,
            },
            "cessions": [
                {
                    "policy_number": c.policy_number,
                    "cession_date": c.cession_date.isoformat(),
                    "gross_premium": str(c.gross_premium),
                    "ceded_premium": str(c.ceded_premium),
                    "net_premium": str(c.net_premium),
                }
                for c in cessions
            ],
            "recoveries": [
                {
                    "claim_number": r.claim_number,
                    "gross_loss": str(r.gross_loss),
                    "retention_deducted": str(r.retention_deducted),
                    "recovered_amount": str(r.recovered_amount),
                    "net_loss": str(r.net_loss),
                }
                for r in recoveries
            ],
        }


reinsurance_service = ReinsuranceService()
