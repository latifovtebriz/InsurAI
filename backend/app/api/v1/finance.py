"""Finance and Double-Entry Ledger REST API endpoints."""

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.finance.engine import check_ledger_balance
from app.modules.finance.models import GeneralLedgerEntry, GeneralLedgerTransaction, Invoice
from app.modules.finance.service import finance_service
from app.modules.platform.public import require_permission

router = APIRouter(prefix="/finance", tags=["Finance & Accounting"])


class PaymentRequest(BaseModel):
    amount: Decimal = Field(description="Exact payment amount in AZN")
    payment_method: str = Field(
        default="bank_transfer", description="bank_transfer, credit_card, debit_card"
    )


class DunningRunRequest(BaseModel):
    as_of_date: str | None = Field(
        default=None, description="ISO date YYYY-MM-DD for dunning evaluation"
    )


@router.get("/invoices", summary="List premium installment invoices")
def list_invoices(
    policy_number: str | None = Query(None, description="Filter by policy number"),
    status: str | None = Query(None, description="Filter by status (issued, paid, overdue)"),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("policy:read")),
) -> list[dict[str, Any]]:
    stmt = select(Invoice)
    if policy_number:
        stmt = stmt.where(Invoice.policy_number == policy_number)
    if status:
        stmt = stmt.where(Invoice.status == status)
    stmt = stmt.order_by(Invoice.due_date)

    invoices = db.scalars(stmt).all()
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "policy_id": inv.policy_id,
            "policy_number": inv.policy_number,
            "party_id": inv.party_id,
            "installment_number": inv.installment_number,
            "amount": float(inv.amount),
            "due_date": inv.due_date.isoformat(),
            "status": inv.status,
            "dunning_level": inv.dunning_level,
            "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
            "created_at": inv.created_at.isoformat(),
        }
        for inv in invoices
    ]


@router.post("/invoices/{invoice_id}/pay", summary="Process payment against invoice")
def pay_invoice(
    invoice_id: str,
    req: PaymentRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("payment:execute")),
) -> dict[str, Any]:
    try:
        user_id = user_payload.get("sub", "system")
        payment = finance_service.process_incoming_payment(
            session=db,
            invoice_id=invoice_id,
            amount=req.amount,
            payment_method=req.payment_method,
            user_id=user_id,
        )
        db.commit()
        return {
            "status": "success",
            "message": "Payment applied successfully; balanced journal recorded.",
            "payment_reference": payment.payment_reference,
            "amount": float(payment.amount),
            "invoice_id": payment.invoice_id,
        }
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/ledger", summary="List General Ledger transactions with balanced entries")
def list_gl_transactions(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("finance:read")),
) -> list[dict[str, Any]]:
    tx_stmt = (
        select(GeneralLedgerTransaction)
        .order_by(GeneralLedgerTransaction.created_at.desc())
        .limit(limit)
    )
    txs = db.scalars(tx_stmt).all()
    result: list[dict[str, Any]] = []

    for tx in txs:
        entries_stmt = (
            select(GeneralLedgerEntry)
            .where(GeneralLedgerEntry.transaction_id == tx.id)
            .order_by(GeneralLedgerEntry.entry_order)
        )
        entries = db.scalars(entries_stmt).all()

        result.append(
            {
                "id": tx.id,
                "transaction_number": tx.transaction_number,
                "transaction_date": tx.transaction_date.isoformat(),
                "reference_type": tx.reference_type,
                "reference_id": tx.reference_id,
                "description": tx.description,
                "total_amount": float(tx.total_amount),
                "entries": [
                    {
                        "account_code": e.account_code,
                        "debit": float(e.debit),
                        "credit": float(e.credit),
                    }
                    for e in entries
                ],
                "created_at": tx.created_at.isoformat(),
            }
        )

    return result


@router.get(
    "/ledger/check", summary="Verify double-entry mathematical invariant (Debits == Credits)"
)
def check_ledger_invariants(
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("finance:read")),
) -> dict[str, Any]:
    check = check_ledger_balance(db)
    return {
        "is_balanced": check["is_balanced"],
        "difference": float(check["difference"]),
        "total_debits": float(check["total_debits"]),
        "total_credits": float(check["total_credits"]),
        "status": "BALANCED" if check["is_balanced"] else "IMBALANCE_DETECTED",
    }


@router.get("/kpis", summary="Financial and actuarial underwriting KPIs")
def get_financial_kpis(
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("finance:read")),
) -> dict[str, Any]:
    kpis = finance_service.get_financial_kpis(db)
    return {
        "gross_written_premium": float(kpis["gross_written_premium"]),
        "incurred_losses": float(kpis["incurred_losses"]),
        "commissions_expense": float(kpis["commissions_expense"]),
        "loss_ratio_pct": kpis["loss_ratio_pct"],
        "expense_ratio_pct": kpis["expense_ratio_pct"],
        "combined_ratio_pct": kpis["combined_ratio_pct"],
        "cash_balance": float(kpis["cash_balance"]),
        "outstanding_receivables": float(kpis["outstanding_receivables"]),
        "claims_payable_reserve": float(kpis["claims_payable_reserve"]),
        "ledger_balanced": kpis["ledger_balanced"],
        "ledger_difference": float(kpis["ledger_difference"]),
    }


@router.post("/dunning/run", summary="Trigger automated dunning evaluation run")
def run_dunning_job(
    req: DunningRunRequest,
    db: Session = Depends(get_db),
    user_payload: dict[str, Any] = Depends(require_permission("policy:write")),
) -> dict[str, Any]:
    from datetime import date

    as_of = date.fromisoformat(req.as_of_date) if req.as_of_date else None
    notices = finance_service.run_dunning_job(db, as_of_date=as_of)
    db.commit()
    return {
        "status": "completed",
        "notices_generated_count": len(notices),
        "notices": notices,
    }
