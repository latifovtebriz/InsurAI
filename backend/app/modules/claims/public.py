"""Public API and contracts for the claims module.
Other modules must import ONLY from this file.
"""

from app.modules.claims.agent import (
    ClaimReason,
    ClaimRecommendation,
    ClaimsTriageAgent,
    PayoutBreakdown,
    ReasonEvidence,
)
from app.modules.claims.calculator import (
    FraudSignal,
    NotificationDeadlineReport,
    PayoutResult,
    calculate_claim_payout,
    check_notification_deadline,
    get_rule_based_fraud_signals,
)
from app.modules.claims.extraction import (
    ClaimExtractionService,
    ExtractedClaim,
    check_prompt_injection_heuristic,
    claim_extraction_service,
)
from app.modules.claims.models import Claim, ClaimDocument, ClaimReserve
from app.modules.claims.service import ClaimsService, claims_service

__all__: list[str] = [
    # Models
    "Claim",
    "ClaimDocument",
    "ClaimReserve",
    # Service
    "ClaimsService",
    "claims_service",
    # Extraction
    "ExtractedClaim",
    "ClaimExtractionService",
    "claim_extraction_service",
    "check_prompt_injection_heuristic",
    # A4 Agent & Contracts
    "ClaimsTriageAgent",
    "ClaimRecommendation",
    "ClaimReason",
    "ReasonEvidence",
    "PayoutBreakdown",
    # Calculation & Engines
    "calculate_claim_payout",
    "check_notification_deadline",
    "get_rule_based_fraud_signals",
    "PayoutResult",
    "NotificationDeadlineReport",
    "FraudSignal",
]
