"""Public interface for the underwriting module.
Other modules must import ONLY from this file.
"""

from app.modules.underwriting.agent import (
    UnderwritingAssessment,
    UnderwritingCopilotAgent,
    underwriting_copilot_agent,
)
from app.modules.underwriting.engine import (
    UnderwritingEvaluationResult,
    UnderwritingRuleHit,
    evaluate_underwriting_rules,
    verify_underwriter_authority,
)
from app.modules.underwriting.models import UnderwritingCase
from app.modules.underwriting.service import (
    UnderwritingService,
    underwriting_service,
)

__all__: list[str] = [
    # Models
    "UnderwritingCase",
    # Rule Engine
    "UnderwritingRuleHit",
    "UnderwritingEvaluationResult",
    "evaluate_underwriting_rules",
    "verify_underwriter_authority",
    # Service
    "UnderwritingService",
    "underwriting_service",
    # Agent A2
    "UnderwritingAssessment",
    "UnderwritingCopilotAgent",
    "underwriting_copilot_agent",
]
