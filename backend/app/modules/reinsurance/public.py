"""Public API and contracts for the reinsurance module.
Other modules must import ONLY from this file.
"""

from app.modules.reinsurance.models import (
    ReinsuranceCession,
    ReinsuranceRecovery,
    ReinsuranceTreaty,
)
from app.modules.reinsurance.service import (
    ReinsuranceService,
    reinsurance_service,
)

__all__: list[str] = [
    # Models
    "ReinsuranceTreaty",
    "ReinsuranceCession",
    "ReinsuranceRecovery",
    # Service
    "ReinsuranceService",
    "reinsurance_service",
]
