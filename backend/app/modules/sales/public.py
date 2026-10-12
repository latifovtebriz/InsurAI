"""Public interface for the sales module.
Other modules must import ONLY from this file.
"""

from app.modules.sales.agent import (
    QuoteAssistantAgent,
    QuoteRequestExtraction,
    extract_quote_intent,
    quote_assistant_agent,
)
from app.modules.sales.models import Lead, Quote
from app.modules.sales.service import (
    SalesService,
    check_kyc_lite_status,
    sales_service,
)

__all__: list[str] = [
    # Models
    "Lead",
    "Quote",
    # Service
    "SalesService",
    "sales_service",
    "check_kyc_lite_status",
    # Agent A1
    "QuoteAssistantAgent",
    "quote_assistant_agent",
    "QuoteRequestExtraction",
    "extract_quote_intent",
]
