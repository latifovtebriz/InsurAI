"""Finance and accounting domain services."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.modules.finance.engine import (
    check_ledger_balance,
    ensure_chart_of_accounts,
    quantize_money,
    validate_balanced_transaction,
)
from app.modules.finance.models import (
    Commission,
    Disbursement,
    GeneralLedgerEntry,
    GeneralLedgerTransaction,
    Invoice,
    Payment,
)
from app.modules.platform.public import publish_outbox_event, record_audit_event
from app.modules.policy.public import Policy
from sqlalchemy import select
from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(UTC)


class FinanceService:
    """Service managing financial operations, balanced ledger entries, and invoicing."""

    def record_gl_transaction(
        self,
        session: Session,
        reference_type: str,
        reference_id: str,
        description: str,
        entries: list[dict[str, Any]],
        transaction_date: date | None = None,
        user_id: str | None = None,
    ) -> GeneralLedgerTransaction:
        """
        Atomically records a balanced double-entry GL transaction.
        Raises LedgerImbalanceError if debits != credits.
        """
        ensure_chart_of_accounts(session)
        total_amount = validate_balanced_transaction(entries)

        t_date = transaction_date or datetime.now(UTC).date()
        random_suffix = uuid.uuid4().hex[:6].upper()
        tx_number = f"TX-{t_date.strftime('%Y%m%d')}-{random_suffix}"

        tx = GeneralLedgerTransaction(
            transaction_number=tx_number,
            transaction_date=t_date,
            reference_type=reference_type,
            reference_id=reference_id,
            description=description,
            total_amount=total_amount,
        )
        session.add(tx)
        session.flush()

        for idx, entry in enumerate(entries):
            gl_entry = GeneralLedgerEntry(
                transaction_id=tx.id,
                account_code=entry["account_code"],
                debit=quantize_money(entry.get("debit", Decimal("0.00"))),
                credit=quantize_money(entry.get("credit", Decimal("0.00"))),
                entry_order=idx,
            )
            session.add(gl_entry)

        session.flush()

        record_audit_event(
            session=session,
            action="gl_transaction_recorded",
            entity_type="gl_transaction",
            entity_id=tx.id,
            after_state={
                "transaction_number": tx.transaction_number,
                "reference_type": reference_type,
                "reference_id": reference_id,
                "total_amount": str(total_amount),
                "entries_count": len(entries),
            },
            user_id=user_id,
        )

        return tx

    def create_invoices_for_policy(
        self,
        session: Session,
        policy_id: str,
        user_id: str | None = None,
    ) -> list[Invoice]:
        """
        Generates invoices corresponding to policy payment schedule and posts initial GL entries.
        Debits Accounts Receivable (1200) and Credits Gross Written Premium (4010).
        """
        policy = session.get(Policy, policy_id)
        if not policy:
            raise ValueError(f"Policy with id '{policy_id}' not found.")

        # Check existing invoices
        existing = session.scalars(
            select(Invoice).where(Invoice.policy_id == policy_id)
        ).all()
        if existing:
            return list(existing)

        invoices: list[Invoice] = []
        schedule = policy.payment_schedule

        if not schedule:
            # Default to single lump-sum invoice
            schedule = [
                {
                    "installment_number": 1,
                    "due_date": policy.start_date.isoformat(),
                    "amount": str(policy.total_premium),
                }
            ]

        for item in schedule:
            inst_num = int(item.get("installment_number", 1))
            due_d = item.get("due_date")
            if isinstance(due_d, str):
                due_date_val = date.fromisoformat(due_d)
            elif isinstance(due_d, date):
                due_date_val = due_d
            else:
                due_date_val = policy.start_date

            amt = quantize_money(item.get("amount", policy.total_premium))
            inv_number = f"INV-{policy.policy_number}-{inst_num:02d}"

            invoice = Invoice(
                invoice_number=inv_number,
                policy_id=policy.id,
                policy_number=policy.policy_number,
                party_id=policy.party_id,
                installment_number=inst_num,
                amount=amt,
                due_date=due_date_val,
                status="issued",
                dunning_level=0,
            )
            session.add(invoice)
            invoices.append(invoice)

        session.flush()

        # Post balanced GL transaction for policy issuance
        # Debit: Accounts Receivable (1200)
        # Credit: Gross Written Premium (4010)
        entries = [
            {"account_code": "1200", "debit": policy.total_premium, "credit": Decimal("0.00")},
            {"account_code": "4010", "debit": Decimal("0.00"), "credit": policy.total_premium},
        ]
        self.record_gl_transaction(
            session=session,
            reference_type="INVOICE_ISSUED",
            reference_id=policy.policy_number,
            description=f"Initial premium receivables for Policy {policy.policy_number}",
            entries=entries,
            transaction_date=policy.start_date,
            user_id=user_id,
        )

        publish_outbox_event(
            session=session,
            event_type="InvoicesCreatedEvent",
            aggregate_type="policy",
            aggregate_id=policy.id,
            payload={
                "policy_number": policy.policy_number,
                "invoices_count": len(invoices),
                "total_amount": str(policy.total_premium),
            },
        )

        return invoices

    def process_incoming_payment(
        self,
        session: Session,
        invoice_id: str,
        amount: Decimal,
        payment_method: str = "bank_transfer",
        payment_date: date | None = None,
        user_id: str | None = None,
    ) -> Payment:
        """
        Applies a payment to an invoice, posts GL journal (Cash vs AR),
        updates policy paid premium, and activates policy if applicable.
        """
        invoice = session.get(Invoice, invoice_id)
        if not invoice:
            raise ValueError(f"Invoice with id '{invoice_id}' not found.")

        if invoice.status == "paid":
            raise ValueError(f"Invoice '{invoice.invoice_number}' is already fully paid.")

        pay_amount = quantize_money(amount)
        if pay_amount != invoice.amount:
            raise ValueError(
                f"Payment amount ({pay_amount}) does not match exact invoice amount ({invoice.amount})."
            )

        pay_date = payment_date or datetime.now(UTC).date()
        random_suffix = uuid.uuid4().hex[:6].upper()
        pay_ref = f"PAY-{pay_date.strftime('%Y%m%d')}-{random_suffix}"

        payment = Payment(
            payment_reference=pay_ref,
            invoice_id=invoice.id,
            amount=pay_amount,
            payment_date=pay_date,
            payment_method=payment_method,
            status="completed",
        )
        session.add(payment)

        invoice.status = "paid"
        invoice.paid_at = utcnow()

        # Update policy
        policy = session.get(Policy, invoice.policy_id)
        if policy:
            policy.paid_premium = quantize_money(policy.paid_premium + pay_amount)
            if policy.status in ("pending_payment", "bound", "draft"):
                policy.status = "active"

        session.flush()

        # Post balanced GL transaction:
        # Debit: Bank Cash (1010)
        # Credit: Accounts Receivable (1200)
        entries = [
            {"account_code": "1010", "debit": pay_amount, "credit": Decimal("0.00")},
            {"account_code": "1200", "debit": Decimal("0.00"), "credit": pay_amount},
        ]
        self.record_gl_transaction(
            session=session,
            reference_type="PAYMENT_RECEIVED",
            reference_id=payment.payment_reference,
            description=f"Premium payment collected for Invoice {invoice.invoice_number}",
            entries=entries,
            transaction_date=pay_date,
            user_id=user_id,
        )

        publish_outbox_event(
            session=session,
            event_type="PaymentReceivedEvent",
            aggregate_type="invoice",
            aggregate_id=invoice.id,
            payload={
                "payment_reference": payment.payment_reference,
                "invoice_number": invoice.invoice_number,
                "amount": str(pay_amount),
                "policy_number": invoice.policy_number,
            },
        )

        return payment

    def record_claim_reserve_movement(
        self,
        session: Session,
        claim_id: str,
        claim_number: str,
        reserve_amount: Decimal,
        user_id: str | None = None,
    ) -> GeneralLedgerTransaction:
        """
        Posts balanced double-entry for claim reserve establishment:
        Debit: Incurred Losses Expense (5010)
        Credit: Claims Payable Reserve (2010)
        """
        amt = quantize_money(reserve_amount)
        entries = [
            {"account_code": "5010", "debit": amt, "credit": Decimal("0.00")},
            {"account_code": "2010", "debit": Decimal("0.00"), "credit": amt},
        ]
        return self.record_gl_transaction(
            session=session,
            reference_type="CLAIM_RESERVE",
            reference_id=claim_number,
            description=f"Incurred loss reserve established for Claim {claim_number}",
            entries=entries,
            user_id=user_id,
        )

    def disburse_claim_payout(
        self,
        session: Session,
        claim_id: str,
        claim_number: str,
        payee_party_id: str,
        amount: Decimal,
        approved_by: str,
        user_id: str | None = None,
    ) -> Disbursement:
        """
        Disburses approved claim payout and posts balanced double-entry:
        Debit: Claims Payable Reserve (2010)
        Credit: Bank Cash (1010)
        """
        payout_amt = quantize_money(amount)
        random_suffix = uuid.uuid4().hex[:6].upper()
        disb_ref = f"DISB-{datetime.now(UTC).strftime('%Y%m%d')}-{random_suffix}"

        disbursement = Disbursement(
            disbursement_reference=disb_ref,
            claim_id=claim_id,
            payee_party_id=payee_party_id,
            amount=payout_amt,
            status="disbursed",
            approved_by=approved_by,
            approved_at=utcnow(),
            disbursed_at=utcnow(),
        )
        session.add(disbursement)
        session.flush()

        entries = [
            {"account_code": "2010", "debit": payout_amt, "credit": Decimal("0.00")},
            {"account_code": "1010", "debit": Decimal("0.00"), "credit": payout_amt},
        ]
        self.record_gl_transaction(
            session=session,
            reference_type="CLAIM_PAYOUT",
            reference_id=disb_ref,
            description=f"Disbursement of approved payout for Claim {claim_number} to payee {payee_party_id}",
            entries=entries,
            user_id=user_id,
        )

        publish_outbox_event(
            session=session,
            event_type="ClaimDisbursedEvent",
            aggregate_type="claim",
            aggregate_id=claim_id,
            payload={
                "disbursement_reference": disb_ref,
                "claim_number": claim_number,
                "amount": str(payout_amt),
                "approved_by": approved_by,
            },
        )

        return disbursement

    def accrue_commission(
        self,
        session: Session,
        policy_id: str,
        policy_number: str,
        agent_party_id: str,
        premium_amount: Decimal,
        rate: Decimal = Decimal("0.1000"),
        user_id: str | None = None,
    ) -> Commission:
        """
        Accrues sales agent distribution commission:
        Debit: Commission Acquisition Expense (5020)
        Credit: Commission Payable (2020)
        """
        comm_amt = quantize_money(premium_amount * rate)
        commission = Commission(
            policy_id=policy_id,
            agent_party_id=agent_party_id,
            commission_rate=rate,
            amount=comm_amt,
            status="accrued",
        )
        session.add(commission)
        session.flush()

        entries = [
            {"account_code": "5020", "debit": comm_amt, "credit": Decimal("0.00")},
            {"account_code": "2020", "debit": Decimal("0.00"), "credit": comm_amt},
        ]
        self.record_gl_transaction(
            session=session,
            reference_type="COMMISSION_ACCRUAL",
            reference_id=policy_number,
            description=f"Commission accrual ({float(rate)*100:.1f}%) for policy {policy_number}",
            entries=entries,
            user_id=user_id,
        )

        return commission

    def run_dunning_job(
        self,
        session: Session,
        as_of_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """
        Scans unpaid invoices and updates dunning levels:
        - T+7 days: Level 1 (first reminder)
        - T+14 days: Level 2 (final notice)
        - T+30 days: Level 3 (default / cancellation notice)
        """
        check_date = as_of_date or datetime.now(UTC).date()
        stmt = select(Invoice).where(
            Invoice.status.in_(["issued", "overdue"]),
            Invoice.due_date < check_date,
        )
        overdue_invoices = session.scalars(stmt).all()
        notices: list[dict[str, Any]] = []

        for inv in overdue_invoices:
            days_overdue = (check_date - inv.due_date).days
            old_level = inv.dunning_level

            if days_overdue >= 30:
                inv.dunning_level = 3
                inv.status = "overdue"
                notice_type = "cancellation_default_notice"
            elif days_overdue >= 14:
                inv.dunning_level = 2
                inv.status = "overdue"
                notice_type = "final_notice"
            elif days_overdue >= 7:
                inv.dunning_level = 1
                inv.status = "overdue"
                notice_type = "first_reminder"
            else:
                notice_type = "grace_period"

            if inv.dunning_level != old_level and notice_type != "grace_period":
                notices.append(
                    {
                        "invoice_number": inv.invoice_number,
                        "policy_number": inv.policy_number,
                        "days_overdue": days_overdue,
                        "dunning_level": inv.dunning_level,
                        "notice_type": notice_type,
                        "amount_due": str(inv.amount),
                    }
                )

        session.flush()
        return notices

    def get_financial_kpis(self, session: Session) -> dict[str, Any]:
        """
        Calculates key operational and actuarial ratios:
        Gross Written Premium (GWP), Incurred Losses, Loss Ratio, Combined Ratio, Cash Position.
        """
        balance_check = check_ledger_balance(session)

        # Calculate GWP (Credit sum of 4010)
        gwp_stmt = select(
            GeneralLedgerEntry.account_code,
            GeneralLedgerEntry.debit,
            GeneralLedgerEntry.credit,
        )
        entries = session.execute(gwp_stmt).all()

        gwp = Decimal("0.00")
        losses = Decimal("0.00")
        commissions = Decimal("0.00")
        cash = Decimal("0.00")
        receivables = Decimal("0.00")
        claims_payable = Decimal("0.00")

        for acc_code, deb, cred in entries:
            deb_val = quantize_money(deb)
            cred_val = quantize_money(cred)

            if acc_code == "4010":
                gwp += (cred_val - deb_val)
            elif acc_code in ("5010", "5030"):
                losses += (deb_val - cred_val)
            elif acc_code == "5020":
                commissions += (deb_val - cred_val)
            elif acc_code == "1010":
                cash += (deb_val - cred_val)
            elif acc_code == "1200":
                receivables += (deb_val - cred_val)
            elif acc_code == "2010":
                claims_payable += (cred_val - deb_val)

        gwp = quantize_money(gwp)
        losses = quantize_money(losses)
        commissions = quantize_money(commissions)
        cash = quantize_money(cash)
        receivables = quantize_money(receivables)
        claims_payable = quantize_money(claims_payable)

        loss_ratio = (
            float((losses / gwp).quantize(Decimal("0.0001"), rounding="ROUND_HALF_UP"))
            if gwp > Decimal("0.00")
            else 0.0
        )
        expense_ratio = (
            float((commissions / gwp).quantize(Decimal("0.0001"), rounding="ROUND_HALF_UP"))
            if gwp > Decimal("0.00")
            else 0.0
        )
        combined_ratio = loss_ratio + expense_ratio

        return {
            "gross_written_premium": gwp,
            "incurred_losses": losses,
            "commissions_expense": commissions,
            "loss_ratio_pct": round(loss_ratio * 100, 2),
            "expense_ratio_pct": round(expense_ratio * 100, 2),
            "combined_ratio_pct": round(combined_ratio * 100, 2),
            "cash_balance": cash,
            "outstanding_receivables": receivables,
            "claims_payable_reserve": claims_payable,
            "ledger_balanced": balance_check["is_balanced"],
            "ledger_difference": balance_check["difference"],
        }


finance_service = FinanceService()
