"""Public API for the policy module.
Other modules must import ONLY from this file.
"""

from app.modules.policy.cancellation import (
    RefundCalculation,
    calculate_cancellation_refund,
)
from app.modules.policy.models import Policy, PolicyCertificate, RenewalCase
from app.modules.policy.rating import (
    FactorApplication,
    Installment,
    RatingBreakdown,
    calculate_home_premium,
    calculate_motor_od_premium,
    calculate_motor_tpl_premium,
    generate_installment_schedule,
    quantize_money,
)
from app.modules.policy.renewal import RenewalService, renewal_service
from app.modules.policy.renewal_agent import (
    RenewalAdvisorAgent,
    RenewalAssessment,
    renewal_advisor_agent,
)
from app.modules.policy.service import (
    PolicyService,
    PolicyStatusReport,
    policy_service,
)

__all__: list[str] = [
    # Models
    "Policy",
    "PolicyCertificate",
    "RenewalCase",
    # Service & Checker
    "PolicyService",
    "policy_service",
    "PolicyStatusReport",
    "RenewalService",
    "renewal_service",
    "RenewalAdvisorAgent",
    "renewal_advisor_agent",
    "RenewalAssessment",
    # Rating Engine
    "calculate_motor_od_premium",
    "calculate_motor_tpl_premium",
    "calculate_home_premium",
    "generate_installment_schedule",
    "quantize_money",
    "RatingBreakdown",
    "FactorApplication",
    "Installment",
    # Cancellation & Refund
    "calculate_cancellation_refund",
    "RefundCalculation",
]
