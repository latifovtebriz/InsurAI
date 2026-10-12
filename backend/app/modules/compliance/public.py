"""Public API and contracts for the compliance module.
Other modules must import ONLY from this file.
"""

from app.modules.compliance.agent import (
    ComplianceExplainerAgent,
    ComplianceExplanation,
    compliance_explainer_agent,
)
from app.modules.compliance.matcher import (
    compute_string_similarity,
    ensure_watchlist_seed,
    screen_entity,
)
from app.modules.compliance.models import ComplianceAlert, WatchlistEntity
from app.modules.compliance.service import ComplianceService, compliance_service

__all__: list[str] = [
    # Models
    "WatchlistEntity",
    "ComplianceAlert",
    # Matcher
    "ensure_watchlist_seed",
    "compute_string_similarity",
    "screen_entity",
    # Agent A8
    "ComplianceExplainerAgent",
    "compliance_explainer_agent",
    "ComplianceExplanation",
    # Service
    "ComplianceService",
    "compliance_service",
]
