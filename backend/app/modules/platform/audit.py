"""Audit logging service capturing entity state changes atomically."""

import uuid
from typing import Any

from app.logging import correlation_id_ctx
from app.modules.platform.models import AuditLog
from sqlalchemy.orm import Session


def record_audit_event(
    session: Session,
    action: str,
    entity_type: str,
    entity_id: str,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    user_id: str | None = None,
    correlation_id: str | None = None,
) -> AuditLog:
    """
    Appends an audit log entry to the active database session.
    Commits or rolls back atomically with the surrounding transaction.
    """
    corr_id = correlation_id or correlation_id_ctx.get() or str(uuid.uuid4())
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        correlation_id=corr_id,
    )
    session.add(log_entry)
    return log_entry
