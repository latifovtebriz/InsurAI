"""General Ledger double-entry engine and Chart of Accounts definitions."""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.modules.finance.models import Account, GeneralLedgerEntry
from sqlalchemy import func, select
from sqlalchemy.orm import Session

STANDARD_CHART_OF_ACCOUNTS = [
    {
        "account_code": "1010",
        "account_name": "Bank Cash",
        "account_type": "ASSET",
        "normal_balance": "DEBIT",
        "description": "Operating cash held in corporate bank accounts.",
    },
    {
        "account_code": "1200",
        "account_name": "Accounts Receivable (Premium)",
        "account_type": "ASSET",
        "normal_balance": "DEBIT",
        "description": "Outstanding premium amounts owed by policyholders.",
    },
    {
        "account_code": "1300",
        "account_name": "Reinsurance Recoverable",
        "account_type": "ASSET",
        "normal_balance": "DEBIT",
        "description": "Claims recoveries receivable from treaty reinsurers.",
    },
    {
        "account_code": "2010",
        "account_name": "Claims Payable Reserve",
        "account_type": "LIABILITY",
        "normal_balance": "CREDIT",
        "description": "Outstanding claims reported and unpaid loss reserves.",
    },
    {
        "account_code": "2020",
        "account_name": "Commission Payable",
        "account_type": "LIABILITY",
        "normal_balance": "CREDIT",
        "description": "Accrued brokerage and agent distribution commissions.",
    },
    {
        "account_code": "2030",
        "account_name": "Unearned Premium Reserve (UPR)",
        "account_type": "LIABILITY",
        "normal_balance": "CREDIT",
        "description": "Portion of premium written corresponding to unexpired term.",
    },
    {
        "account_code": "2040",
        "account_name": "Reinsurance Payable",
        "account_type": "LIABILITY",
        "normal_balance": "CREDIT",
        "description": "Ceded premium obligations owed to treaty reinsurers.",
    },
    {
        "account_code": "3010",
        "account_name": "Retained Earnings / Capital",
        "account_type": "EQUITY",
        "normal_balance": "CREDIT",
        "description": "Shareholders equity and accumulated underwriting profits.",
    },
    {
        "account_code": "4010",
        "account_name": "Gross Written Premium (GWP)",
        "account_type": "REVENUE",
        "normal_balance": "CREDIT",
        "description": "Total premium revenue written on in-force insurance policies.",
    },
    {
        "account_code": "4020",
        "account_name": "Ceded Reinsurance Premium",
        "account_type": "REVENUE",
        "normal_balance": "DEBIT",
        "description": "Premium ceded to reinsurers (contra-revenue account).",
    },
    {
        "account_code": "5010",
        "account_name": "Incurred Losses Expense",
        "account_type": "EXPENSE",
        "normal_balance": "DEBIT",
        "description": "Losses and claims incurred during the accounting period.",
    },
    {
        "account_code": "5020",
        "account_name": "Commission Acquisition Expense",
        "account_type": "EXPENSE",
        "normal_balance": "DEBIT",
        "description": "Intermediary and agent commission acquisition expenses.",
    },
    {
        "account_code": "5030",
        "account_name": "Reinsurance Loss Recoveries",
        "account_type": "EXPENSE",
        "normal_balance": "CREDIT",
        "description": "Claims expenses recovered from treaty reinsurers (contra-expense).",
    },
]


class LedgerImbalanceError(ValueError):
    """Raised when a GL transaction violates the double-entry invariant (Debits != Credits)."""
    pass


def quantize_money(amount: Decimal | float | int | str) -> Decimal:
    """Quantizes amount to 2 decimal places using ROUND_HALF_UP."""
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ensure_chart_of_accounts(session: Session) -> None:
    """Ensures that all standard chart of accounts exist in the database."""
    for acc in STANDARD_CHART_OF_ACCOUNTS:
        existing = session.get(Account, acc["account_code"])
        if not existing:
            account = Account(
                account_code=acc["account_code"],
                account_name=acc["account_name"],
                account_type=acc["account_type"],
                normal_balance=acc["normal_balance"],
                description=acc["description"],
            )
            session.add(account)
    session.flush()


def validate_balanced_transaction(entries: list[dict[str, Any]]) -> Decimal:
    """
    Validates that a list of journal entries is balanced down to the exact cent.
    Returns the total transaction amount (sum of debits == sum of credits).
    Raises LedgerImbalanceError if debits != credits.
    """
    if not entries or len(entries) < 2:
        raise LedgerImbalanceError("A double-entry transaction must contain at least two entries.")

    total_debits = Decimal("0.00")
    total_credits = Decimal("0.00")

    for idx, entry in enumerate(entries):
        debit = quantize_money(entry.get("debit", Decimal("0.00")))
        credit = quantize_money(entry.get("credit", Decimal("0.00")))

        if debit < Decimal("0.00") or credit < Decimal("0.00"):
            raise LedgerImbalanceError(f"Entry {idx} has negative debit ({debit}) or credit ({credit}). Negative amounts are forbidden.")

        if debit > Decimal("0.00") and credit > Decimal("0.00"):
            raise LedgerImbalanceError(f"Entry {idx} has both debit ({debit}) and credit ({credit}). Each line must be either debit or credit.")

        total_debits += debit
        total_credits += credit

    difference = (total_debits - total_credits).copy_abs()
    if difference != Decimal("0.00"):
        raise LedgerImbalanceError(
            f"Ledger imbalance detected: total debits ({total_debits}) != total credits ({total_credits}). Difference: {difference} AZN."
        )

    return total_debits


def check_ledger_balance(session: Session) -> dict[str, Any]:
    """
    Performs an audit check across all entries in the general ledger.
    Asserts whether total debits equal total credits across the entire ledger.
    """
    stmt = select(
        func.coalesce(func.sum(GeneralLedgerEntry.debit), Decimal("0.00")),
        func.coalesce(func.sum(GeneralLedgerEntry.credit), Decimal("0.00")),
    )
    res = session.execute(stmt).first()
    total_debits = quantize_money(res[0] if res else Decimal("0.00"))
    total_credits = quantize_money(res[1] if res else Decimal("0.00"))
    difference = quantize_money((total_debits - total_credits).copy_abs())
    is_balanced = (difference == Decimal("0.00"))

    return {
        "total_debits": total_debits,
        "total_credits": total_credits,
        "difference": difference,
        "is_balanced": is_balanced,
    }
