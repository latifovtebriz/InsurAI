"""Audit log inspection endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.platform.public import AuditLog, require_permission

router = APIRouter(prefix="/audit", tags=["Audit"])


class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None = None
    action: str
    entity_type: str
    entity_id: str
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    correlation_id: str | None = None
    timestamp: str


@router.get("", response_model=list[AuditLogResponse])
def list_audit_events(
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    user_id: str | None = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(require_permission("audit:read")),
) -> list[AuditLogResponse]:
    """Retrieves immutable audit trail entries."""
    stmt = select(AuditLog)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)

    logs = db.scalars(stmt).all()
    return [
        AuditLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            before_state=log.before_state,
            after_state=log.after_state,
            correlation_id=log.correlation_id,
            timestamp=log.timestamp.isoformat(),
        )
        for log in logs
    ]
