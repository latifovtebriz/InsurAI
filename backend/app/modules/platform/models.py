"""SQLAlchemy 2.0 platform models and schema declarations."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.db import Base
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    """Returns current UTC timestamp with timezone."""
    return datetime.now(UTC)


class TimestampMixin:
    """Common timestamp columns for all platform entities."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    """Platform user for RBAC and identity."""

    __tablename__ = "users"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RolePermission(Base, TimestampMixin):
    """Explicit mapping of roles to module:action permission codes."""

    __tablename__ = "role_permissions"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    permission: Mapped[str] = mapped_column(String(100), nullable=False, index=True)


class AuditLog(Base):
    """Append-only audit trail written within the same transaction."""

    __tablename__ = "audit_log"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class OutboxEvent(Base, TimestampMixin):
    """Transactional outbox event record."""

    __tablename__ = "outbox_events"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, published, failed
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessedEvent(Base):
    """Deduplication tracker ensuring idempotent event processing."""

    __tablename__ = "processed_events"
    __table_args__ = {"schema": "platform"}

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    consumer_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Job(Base, TimestampMixin):
    """Database-backed background job queue with skip-locked support."""

    __tablename__ = "jobs"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, running, completed, failed
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BusinessRuleModel(Base, TimestampMixin):
    """Effective-dated business rule configuration stored in DB."""

    __tablename__ = "business_rules"
    __table_args__ = {"schema": "platform"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    effective_from: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_to: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
