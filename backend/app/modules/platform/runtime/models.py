"""Tracing database models for agent runs, execution steps, and guardrails."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.db import Base
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(UTC)


class AgentRun(Base):
    """Execution trace of an autonomous agent session."""

    __tablename__ = "agent_runs"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default="running", nullable=False, index=True
    )  # running, completed, needs_human_review, failed
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    final_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentStep(Base):
    """Individual reasoning, tool call, or guardrail check in an agent run."""

    __tablename__ = "agent_steps"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_kind: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # "llm_call", "tool_call", "guardrail"
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_input: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tool_output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
