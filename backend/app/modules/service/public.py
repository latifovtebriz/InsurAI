"""Public API and contracts for the customer service module.
Other modules must import ONLY from this file.
"""

from app.modules.service.customer_agent import (
    CustomerChatResponse,
    CustomerServiceAgent,
    customer_service_agent,
)
from app.modules.service.models import Complaint, EndorsementDraft, ServiceInquiry
from app.modules.service.service import (
    CustomerServiceDomain,
    customer_service_domain,
)
from app.modules.service.servicing_agent import (
    EndorsementDraftResult,
    PolicyServicingAgent,
    policy_servicing_agent,
)

__all__: list[str] = [
    # Models
    "ServiceInquiry",
    "Complaint",
    "EndorsementDraft",
    # Agent A6 Customer Service
    "CustomerServiceAgent",
    "customer_service_agent",
    "CustomerChatResponse",
    # Agent A3 Policy Servicing Assistant
    "PolicyServicingAgent",
    "policy_servicing_agent",
    "EndorsementDraftResult",
    # Domain Service
    "CustomerServiceDomain",
    "customer_service_domain",
]
