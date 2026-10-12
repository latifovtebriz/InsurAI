"""Agent execution trace endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.platform.public import AgentRun, AgentStep, require_permission

router = APIRouter(prefix="/traces", tags=["Traces"])


class AgentStepResponse(BaseModel):
    id: str
    step_index: int
    step_kind: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: dict[str, Any] | None = None
    tokens_used: int
    latency_ms: int
    error_message: str | None = None
    created_at: str


class AgentRunDetailResponse(BaseModel):
    id: str
    agent_id: str
    correlation_id: str
    status: str
    input_payload: dict[str, Any]
    final_output: dict[str, Any] | None = None
    step_count: int
    total_tokens: int
    total_cost_usd: float
    duration_seconds: float
    created_at: str
    completed_at: str | None = None
    steps: list[AgentStepResponse]


class AgentRunSummaryResponse(BaseModel):
    id: str
    agent_id: str
    correlation_id: str
    status: str
    step_count: int
    total_tokens: int
    total_cost_usd: float
    duration_seconds: float
    created_at: str


@router.get("", response_model=list[AgentRunSummaryResponse])
def list_traces(
    agent_id: str | None = Query(None),
    correlation_id: str | None = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("traces:read")),
) -> list[AgentRunSummaryResponse]:
    """Retrieves recent agent execution runs."""
    stmt = select(AgentRun)
    if agent_id:
        stmt = stmt.where(AgentRun.agent_id == agent_id)
    if correlation_id:
        stmt = stmt.where(AgentRun.correlation_id == correlation_id)
    stmt = stmt.order_by(AgentRun.created_at.desc()).limit(limit)

    runs = db.scalars(stmt).all()
    return [
        AgentRunSummaryResponse(
            id=r.id,
            agent_id=r.agent_id,
            correlation_id=r.correlation_id,
            status=r.status,
            step_count=r.step_count,
            total_tokens=r.total_tokens,
            total_cost_usd=r.total_cost_usd,
            duration_seconds=r.duration_seconds,
            created_at=r.created_at.isoformat(),
        )
        for r in runs
    ]


@router.get("/{run_id}", response_model=AgentRunDetailResponse)
def get_trace_detail(
    run_id: str,
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("traces:read")),
) -> AgentRunDetailResponse:
    """Retrieves full trace and execution steps for a specific agent run."""
    run = db.get(AgentRun, run_id)
    if not run:
        # Also allow finding by correlation_id (e.g. triage-CLM-2026-0001)
        stmt = select(AgentRun).where(AgentRun.correlation_id == run_id)
        run = db.scalars(stmt).first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trace run '{run_id}' not found",
            )

    steps_stmt = select(AgentStep).where(AgentStep.run_id == run.id).order_by(AgentStep.step_index.asc())
    steps = db.scalars(steps_stmt).all()

    step_responses = [
        AgentStepResponse(
            id=s.id,
            step_index=s.step_index,
            step_kind=s.step_kind,
            tool_name=s.tool_name,
            tool_input=s.tool_input,
            tool_output=s.tool_output,
            tokens_used=s.tokens_used,
            latency_ms=s.latency_ms,
            error_message=s.error_message,
            created_at=s.created_at.isoformat(),
        )
        for s in steps
    ]

    return AgentRunDetailResponse(
        id=run.id,
        agent_id=run.agent_id,
        correlation_id=run.correlation_id,
        status=run.status,
        input_payload=run.input_payload,
        final_output=run.final_output,
        step_count=run.step_count,
        total_tokens=run.total_tokens,
        total_cost_usd=run.total_cost_usd,
        duration_seconds=run.duration_seconds,
        created_at=run.created_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        steps=step_responses,
    )
