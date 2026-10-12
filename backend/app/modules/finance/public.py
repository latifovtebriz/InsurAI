"""Public API and contracts for the finance module.
Other modules must import ONLY from this file.
"""

from app.modules.finance.engine import (
    LedgerImbalanceError,
    check_ledger_balance,
    ensure_chart_of_accounts,
    quantize_money,
    validate_balanced_transaction,
)
from app.modules.finance.models import (
    Account,
    Commission,
    Disbursement,
    GeneralLedgerEntry,
    GeneralLedgerTransaction,
    Invoice,
    Payment,
)
from app.modules.finance.service import (
    FinanceService,
    finance_service,
)

__all__: list[str] = [
    # Models
    "Account",
    "GeneralLedgerTransaction",
    "GeneralLedgerEntry",
    "Invoice",
    "Payment",
    "Disbursement",
    "Commission",
    # Engine & Math
    "quantize_money",
    "validate_balanced_transaction",
    "check_ledger_balance",
    "ensure_chart_of_accounts",
    "LedgerImbalanceError",
    # Service
    "FinanceService",
    "finance_service",
]
