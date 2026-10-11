"""Public API and contracts for the platform module.
Other modules must import ONLY from this file.
"""

from app.modules.platform.audit import record_audit_event
from app.modules.platform.errors import InsurAIException, create_problem_response
from app.modules.platform.job_runner import JobRunner, job_runner
from app.modules.platform.knowledge.embedder import (
    DeterministicFakeEmbedder,
    fake_embedder,
)
from app.modules.platform.knowledge.models import KBChunk
from app.modules.platform.knowledge.service import (
    Citation,
    KnowledgeService,
    knowledge_service,
)
from app.modules.platform.llm.client import (
    FakeLLMClient,
    GeminiLLMClient,
    LLMClient,
    LLMMessage,
    LLMResponse,
    RecordReplayLLMClient,
)
from app.modules.platform.llm.gateway import (
    DailyCapExceededError,
    LLMGateway,
    StructuredOutputValidationError,
    gateway,
)
from app.modules.platform.models import (
    AuditLog,
    BusinessRuleModel,
    Job,
    OutboxEvent,
    ProcessedEvent,
    RolePermission,
    User,
)
from app.modules.platform.outbox import OutboxDispatcher, dispatcher, publish_outbox_event
from app.modules.platform.rbac import (
    create_access_token,
    decode_access_token,
    has_permission,
    hash_password,
    require_permission,
    verify_password,
)
from app.modules.platform.rules_catalog import (
    BUSINESS_RULES_CATALOG,
    BusinessRuleDefinition,
    get_rule_by_code,
)
from app.modules.platform.workflow import (
    CLAIM_WORKFLOW,
    INVOICE_WORKFLOW,
    POLICY_WORKFLOW,
    QUOTE_WORKFLOW,
    GuardConditionFailedError,
    InvalidStateTransitionError,
    StateMachineDefinition,
    Transition,
)

__all__: list[str] = [
    # Models
    "User",
    "RolePermission",
    "AuditLog",
    "OutboxEvent",
    "ProcessedEvent",
    "Job",
    "BusinessRuleModel",
    # Rules
    "BUSINESS_RULES_CATALOG",
    "BusinessRuleDefinition",
    "get_rule_by_code",
    # RBAC
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "has_permission",
    "require_permission",
    # Audit
    "record_audit_event",
    # Workflow
    "QUOTE_WORKFLOW",
    "POLICY_WORKFLOW",
    "CLAIM_WORKFLOW",
    "INVOICE_WORKFLOW",
    "InvalidStateTransitionError",
    "GuardConditionFailedError",
    "StateMachineDefinition",
    "Transition",
    # Outbox
    "publish_outbox_event",
    "dispatcher",
    "OutboxDispatcher",
    # Jobs
    "job_runner",
    "JobRunner",
    # Errors
    "InsurAIException",
    "create_problem_response",
    # LLM & Gateway
    "LLMClient",
    "FakeLLMClient",
    "RecordReplayLLMClient",
    "GeminiLLMClient",
    "LLMMessage",
    "LLMResponse",
    "LLMGateway",
    "gateway",
    "DailyCapExceededError",
    "StructuredOutputValidationError",
    # Knowledge (RAG)
    "KBChunk",
    "Citation",
    "KnowledgeService",
    "knowledge_service",
    "DeterministicFakeEmbedder",
    "fake_embedder",
]
