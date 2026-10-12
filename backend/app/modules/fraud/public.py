"""Public API and contracts for the fraud detection and SIU module.
Other modules must import ONLY from this file.
"""

from app.modules.fraud.agent import (
    FraudAssistantAgent,
    SIUAnomalyAssessment,
    fraud_assistant_agent,
    sanitize_neutral_language,
    validate_neutral_language,
)
from app.modules.fraud.engine import (
    FairnessViolationError,
    evaluate_fraud_signals,
)
from app.modules.fraud.models import FraudSignalRecord, SIUCase
from app.modules.fraud.service import FraudService, fraud_service

__all__: list[str] = [
    # Models
    "FraudSignalRecord",
    "SIUCase",
    # Engine & Fairness
    "evaluate_fraud_signals",
    "FairnessViolationError",
    # Agent A5 & G8 Neutral Language
    "FraudAssistantAgent",
    "fraud_assistant_agent",
    "SIUAnomalyAssessment",
    "validate_neutral_language",
    "sanitize_neutral_language",
    # Service
    "FraudService",
    "fraud_service",
]
