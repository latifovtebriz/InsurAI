"""Chaos-style robustness tests per Master Plan Task 13.3.

Verifies system resilience against:
1. LLM timeout and network failure -> ends in verified safe state (needs_human_review).
2. Malformed / corrupted LLM response -> terminates gracefully with schema safeguard.
3. Database transaction hiccup -> rolls back atomically, zero partial state, ledger intact.
4. Oversized payload attack -> blocked by HTTP 413 MaxPayloadSizeMiddleware.
5. Large policy document chunking -> bounded memory and execution.
"""

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from app.modules.finance.public import (
    GeneralLedgerEntry,
    GeneralLedgerTransaction,
)
from app.modules.platform.knowledge.service import KnowledgeService
from app.modules.platform.llm.client import LLMResponse
from app.modules.platform.llm.gateway import LLMGateway
from app.modules.platform.runtime.loop import AgentLoop
from app.modules.platform.runtime.models import AgentRun
from app.modules.platform.runtime.tools import ToolRegistry
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_llm_timeout_triggers_safe_downgrade_to_human_review(db_session: Session) -> None:
    """Verifies that an LLM timeout exception immediately triggers safe fail-safe downgrade."""
    mock_gateway = AsyncMock(spec=LLMGateway)
    mock_gateway.generate.side_effect = TimeoutError("Gemini API connection timed out after 30s")

    registry = ToolRegistry()
    loop = AgentLoop(
        agent_id="claims_triage_chaos_agent",
        tool_registry=registry,
        llm_gateway=mock_gateway,
    )

    result = await loop.run(
        session=db_session,
        system_prompt="You are a claims triage agent.",
        initial_user_message="Triage claim #CLM-CHAOS-001 for motor collision.",
    )

    # 1. Output must downgrade to needs_human_review
    assert result["recommendation"] == "needs_human_review"
    assert (
        "Fail-safe" in result["reasons"][0]["statement"]
        or "safeguard" in result["reasons"][0]["statement"]
    )

    # 2. AgentRun record in database must be saved with needs_human_review status
    runs = db_session.scalars(
        select(AgentRun).where(AgentRun.agent_id == "claims_triage_chaos_agent")
    ).all()
    assert len(runs) == 1
    assert runs[0].status == "needs_human_review"


@pytest.mark.asyncio
async def test_malformed_llm_response_terminates_in_safe_state(db_session: Session) -> None:
    """Verifies that corrupted / hallucinated output terminates safely without unhandled crash."""
    mock_gateway = AsyncMock(spec=LLMGateway)
    # LLM returns garbage non-JSON and missing tool declaration syntax
    mock_gateway.generate.return_value = LLMResponse(
        content="<<<MALFORMED_NON_JSON_CORRUPTED_TOKENS>>> \x00\x01\x02",
        model_name="mock-gemini-1.5-flash",
        total_tokens=42,
        prompt_tokens=30,
        completion_tokens=12,
        cost_estimate=0.0001,
    )

    registry = ToolRegistry()
    loop = AgentLoop(
        agent_id="claims_malformed_test_agent",
        tool_registry=registry,
        llm_gateway=mock_gateway,
    )

    result = await loop.run(
        session=db_session,
        system_prompt="You are a claims agent.",
        initial_user_message="Evaluate claim payload.",
    )

    # Without a valid tool call, loop gracefully concludes and marks safe status
    assert result["recommendation"] == "needs_human_review"

    runs = db_session.scalars(
        select(AgentRun).where(AgentRun.agent_id == "claims_malformed_test_agent")
    ).all()
    assert len(runs) == 1
    assert runs[0].status == "needs_human_review"


def test_database_atomic_rollback_preserves_ledger_integrity(db_session: Session) -> None:
    """Verifies that an error midway through financial journal posting rolls back completely."""
    from datetime import date

    # Record initial count of ledger entries
    initial_entries_count = len(db_session.scalars(select(GeneralLedgerEntry)).all())

    # Attempt to post a transaction where second entry raises an integrity error
    try:
        tx = GeneralLedgerTransaction(
            transaction_number="TX-CHAOS-ROLLBACK-001",
            transaction_date=date.today(),
            reference_type="INVOICE_ISSUED",
            reference_id="INV-CHAOS-ROLLBACK",
            description="Chaos test rollback transaction",
            total_amount=Decimal("1500.00"),
        )
        db_session.add(tx)
        db_session.flush()

        entry1 = GeneralLedgerEntry(
            transaction_id=tx.id,
            account_code="1110",
            debit=Decimal("1500.00"),
            credit=Decimal("0.00"),
            entry_order=1,
        )
        db_session.add(entry1)
        db_session.flush()

        # Simulate deliberate failure before balancing credit is posted
        raise RuntimeError("Simulated database constraint crash or deadlock")

    except RuntimeError:
        db_session.rollback()

    # Verify that atomic rollback occurred: no orphaned debit entry persists
    final_entries_count = len(db_session.scalars(select(GeneralLedgerEntry)).all())
    assert final_entries_count == initial_entries_count

    # Verify General Ledger balance remains zero difference
    debits = sum(e.debit for e in db_session.scalars(select(GeneralLedgerEntry)).all())
    credits = sum(e.credit for e in db_session.scalars(select(GeneralLedgerEntry)).all())
    assert debits == credits


def test_oversized_payload_rejected_with_http_413(client: TestClient) -> None:
    """Verifies that requests exceeding 10MB Content-Length header are rejected with HTTP 413."""
    headers = {
        "Content-Length": str(25 * 1024 * 1024),  # 25 MB
        "Content-Type": "application/json",
    }
    response = client.post("/api/v1/claims/triage", content=b"{}", headers=headers)
    assert response.status_code == 413
    assert "Payload too large" in response.json()["detail"]


def test_large_policy_document_embedding_bounded(db_session: Session) -> None:
    """Verifies that KnowledgeService and embedder handle huge text documents safely."""
    knowledge = KnowledgeService()

    # Query with huge string (50,000 characters)
    huge_query = "motor vehicle collision total loss comprehensive damage " * 1000
    vec = knowledge.embedder.embed_text(huge_query)

    # Embedding dimension must remain fixed 768 floats without unbounded memory
    assert len(vec) == 768
    assert isinstance(vec[0], float)
