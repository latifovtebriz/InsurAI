"""SQLAlchemy models for customer service inquiries, complaints, and endorsement drafts."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.db import Base
from sqlalchemy import Boolean, Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(UTC)


class ServiceInquiry(Base):
    """Customer chat or helpline inquiry record."""

    __tablename__ = "service_inquiries"
    __table_args__ = {"schema": "service"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    party_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    customer_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    is_authenticated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="faq", nullable=False, index=True
    )  # faq, policy_info, claim_status, complaint
    status: Mapped[str] = mapped_column(
        String(30), default="resolved", nullable=False
    )  # open, resolved, escalated
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    agent_response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Complaint(Base):
    """Formal customer complaint with statutory SLA resolution tracking."""

    __tablename__ = "complaints"
    __table_args__ = {"schema": "service"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    claim_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="received", nullable=False, index=True
    )  # received, under_investigation, escalated_to_ombudsman, resolved
    initial_response_deadline: Mapped[date] = mapped_column(
        Date, nullable=False
    )  # T+5 statutory SLA
    final_resolution_deadline: Mapped[date] = mapped_column(
        Date, nullable=False
    )  # T+15 statutory SLA
    initial_responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_breached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class EndorsementDraft(Base):
    """Proposed mid-term policy adjustment / endorsement draft (P06)."""

    __tablename__ = "endorsement_drafts"
    __table_args__ = {"schema": "service"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    draft_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    endorsement_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # ADD_DRIVER, INCREASE_SUM_INSURED, ADDRESS_CHANGE, VEHICLE_SUBSTITUTION
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    proposed_changes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    prorata_premium_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="draft", nullable=False, index=True
    )  # draft, approved, applied, rejected
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
