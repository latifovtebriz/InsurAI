"""Unit tests for Platform Core: RBAC, Workflow, Outbox, Audit, and Job Runner."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from app.db import Base
from app.modules.platform.audit import record_audit_event
from app.modules.platform.job_runner import JobRunner
from app.modules.platform.models import AuditLog, OutboxEvent
from app.modules.platform.outbox import OutboxDispatcher, publish_outbox_event
from app.modules.platform.rbac import (
    create_access_token,
    decode_access_token,
    has_permission,
    hash_password,
    verify_password,
)
from app.modules.platform.workflow import (
    CLAIM_WORKFLOW,
    InvalidStateTransitionError,
)
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides an isolated SQLite in-memory session with schema translation."""
    engine = create_engine(
        "sqlite:///:memory:",
        execution_options={"schema_translate_map": {"platform": None}},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


# ==============================================================================
# RBAC Tests
# ==============================================================================


def test_password_hashing_and_verification() -> None:
    """Verifies that PBKDF2 hashing is salted, non-reversible, and verifiable."""
    pwd = "SecureInsurancePassword123!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert "$" in hashed
    assert verify_password(pwd, hashed)
    assert not verify_password("WrongPassword!", hashed)


def test_jwt_token_generation_and_decoding() -> None:
    """Verifies access token generation and claims decoding."""
    token = create_access_token(subject="user_123", role="adjuster")
    claims = decode_access_token(token)
    assert claims["sub"] == "user_123"
    assert claims["role"] == "adjuster"


def test_rbac_permission_matrix() -> None:
    """Verifies role permissions match the architecture 3.12 matrix."""
    # Admin has all permissions
    assert has_permission("admin", "claims:settle")
    assert has_permission("admin", "anything:action")

    # Adjuster permissions
    assert has_permission("adjuster", "claims:read")
    assert has_permission("adjuster", "claims:approve")
    assert has_permission("adjuster", "fraud:read")
    assert not has_permission("adjuster", "finance:disburse")
    assert not has_permission("adjuster", "sales:create_quote")

    # Underwriter permissions
    assert has_permission("underwriter", "underwriting:approve")
    assert has_permission("underwriter", "sales:review")
    assert not has_permission("underwriter", "claims:approve")

    # Customer permissions
    assert has_permission("customer", "claims:create")
    assert has_permission("customer", "policy:read_own")
    assert not has_permission("customer", "claims:approve")


# ==============================================================================
# Workflow Engine Tests
# ==============================================================================


def test_workflow_valid_transitions() -> None:
    """Verifies valid state transitions in the claim state machine."""
    s1 = CLAIM_WORKFLOW.trigger("fnol_received", "register_claim")
    assert s1 == "registered"

    s2 = CLAIM_WORKFLOW.trigger("registered", "start_triage")
    assert s2 == "triage_in_progress"

    s3 = CLAIM_WORKFLOW.trigger("triage_in_progress", "submit_recommendation")
    assert s3 == "awaiting_review"

    s4 = CLAIM_WORKFLOW.trigger("awaiting_review", "confirm_approval")
    assert s4 == "approved"

    s5 = CLAIM_WORKFLOW.trigger("approved", "disburse_payment")
    assert s5 == "settled"

    s6 = CLAIM_WORKFLOW.trigger("settled", "close_claim")
    assert s6 == "closed"


def test_workflow_illegal_transition_raises_error() -> None:
    """Verifies that unauthorized transitions raise an error and mutate nothing."""
    with pytest.raises(InvalidStateTransitionError):
        # Cannot jump from fnol_received straight to approved
        CLAIM_WORKFLOW.trigger("fnol_received", "confirm_approval")

    with pytest.raises(InvalidStateTransitionError):
        # Cannot approve an already closed claim
        CLAIM_WORKFLOW.trigger("closed", "confirm_approval")


# ==============================================================================
# Outbox & Idempotency Tests
# ==============================================================================


def test_outbox_atomic_rollback(db_session: Session) -> None:
    """Verifies that an aborted transaction rolls back both business mutation and outbox event."""
    try:
        # Simulate business action
        publish_outbox_event(
            session=db_session,
            event_type="ClaimRegistered",
            aggregate_type="Claim",
            aggregate_id="CLM-001",
            payload={"claim_number": "CLM-001", "amount": 1000.0},
        )
        # Force a failure before commit
        raise ValueError("Simulated unexpected business error during registration!")
    except ValueError:
        db_session.rollback()

    # Verify outbox event was NOT saved
    events = db_session.scalars(select(OutboxEvent)).all()
    assert len(events) == 0


def test_outbox_idempotent_event_dispatch(db_session: Session) -> None:
    """Verifies that registered consumers process a duplicated event exactly once."""
    dispatcher = OutboxDispatcher()
    processed_calls: list[str] = []

    def sample_consumer(event: OutboxEvent) -> None:
        processed_calls.append(event.id)

    dispatcher.register_consumer("PolicyIssued", "PolicyEmailConsumer", sample_consumer)

    # Publish an event
    evt = publish_outbox_event(
        session=db_session,
        event_type="PolicyIssued",
        aggregate_type="Policy",
        aggregate_id="POL-001",
        payload={"policy_number": "POL-001"},
    )
    db_session.commit()

    # First dispatch
    count_1 = dispatcher.dispatch_pending(db_session)
    assert count_1 == 1
    assert len(processed_calls) == 1

    # Verify event status is published
    db_session.refresh(evt)
    assert evt.status == "published"

    # Reset status to pending to simulate a duplicated redelivery
    evt.status = "pending"
    db_session.commit()

    # Second dispatch: consumer should be skipped due to ProcessedEvent deduplication
    count_2 = dispatcher.dispatch_pending(db_session)
    assert count_2 == 1  # event marked published again
    assert len(processed_calls) == 1  # consumer was NOT called a second time!


# ==============================================================================
# Job Runner & Crash Recovery Tests
# ==============================================================================


def test_job_runner_crash_recovery_and_execution(db_session: Session) -> None:
    """
    Verifies that if a worker crashes mid-job, the job is reclaimed after timeout
    and completed exactly once.
    """
    runner = JobRunner()
    execution_results: list[str] = []

    def mock_report_job(payload: dict[str, Any]) -> None:
        execution_results.append(payload["report_name"])

    runner.register_handler("GenerateReport", mock_report_job)

    # 1. Enqueue job
    job = runner.enqueue_job(
        session=db_session,
        job_type="GenerateReport",
        payload={"report_name": "MonthlyClaimsSummary"},
    )
    assert job.status == "pending"

    # 2. Worker 1 claims job
    claimed_1 = runner.claim_next_job(db_session, worker_id="worker_alpha")
    assert claimed_1 is not None
    assert claimed_1.status == "running"
    assert claimed_1.locked_by == "worker_alpha"

    # Simulate crash: worker_alpha dies without completing.
    # We fast-forward lock time to simulate lock timeout.
    claimed_1.locked_at = datetime.now(UTC) - timedelta(seconds=400)
    db_session.commit()

    # 3. Worker 2 claims next job (reclaims the timed-out crashed job!)
    claimed_2 = runner.claim_next_job(db_session, worker_id="worker_beta", lock_timeout_seconds=300)
    assert claimed_2 is not None
    assert claimed_2.id == job.id
    assert claimed_2.locked_by == "worker_beta"

    # 4. Worker 2 executes and finishes job
    success = runner.execute_claimed_job(db_session, claimed_2)
    assert success is True
    assert claimed_2.status == "completed"
    assert execution_results == ["MonthlyClaimsSummary"]


# ==============================================================================
# Audit Log Tests
# ==============================================================================


def test_audit_log_records_changes_atomically(db_session: Session) -> None:
    """Verifies that audit logging records before/after state with correlation ID."""
    entry = record_audit_event(
        session=db_session,
        action="update_status",
        entity_type="Claim",
        entity_id="CLM-999",
        before_state={"status": "registered"},
        after_state={"status": "approved"},
        user_id="USR-42",
        correlation_id="corr-test-1234",
    )
    db_session.commit()

    saved = db_session.get(AuditLog, entry.id)
    assert saved is not None
    assert saved.action == "update_status"
    assert saved.entity_id == "CLM-999"
    assert saved.before_state == {"status": "registered"}
    assert saved.after_state == {"status": "approved"}
    assert saved.correlation_id == "corr-test-1234"
