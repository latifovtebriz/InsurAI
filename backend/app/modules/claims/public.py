"""Public API and contracts for the claims module.
Other modules must import ONLY from this file.
"""

from app.modules.claims.extraction import (
    ClaimExtractionService,
    ExtractedClaim,
    check_prompt_injection_heuristic,
)

__all__: list[str] = [
    "ExtractedClaim",
    "ClaimExtractionService",
    "check_prompt_injection_heuristic",
]
