"""SQLAlchemy models for the claims module."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.db import Base
from sqlalchemy import Date, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(UTC)


class Claim(Base):
    """Insurance claim lifecycle record."""

    __tablename__ = "claims"
    __table_args__ = {"schema": "claims"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    policy_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    incident_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notification_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(
        String(50), default="MOTOR_OD", nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), default="fnol_received", nullable=False, index=True
    )  # fnol_received, registered, triage_in_progress, awaiting_review, approved, rejected, settled, closed
    claimed_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estimated_reserve: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    approved_payout: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    deductible_applied: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    autonomy_level: Mapped[str] = mapped_column(
        String(10), default="L2", nullable=False
    )  # L1, L2, L3
    incident_description: Mapped[str] = mapped_column(Text, nullable=False)
    raw_documents: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    extraction_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    triage_recommendation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    adjuster_decision: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ClaimDocument(Base):
    """Uploaded claim supporting documents (repair estimate, police report, etc.)."""

    __tablename__ = "claim_documents"
    __table_args__ = {"schema": "claims"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # estimate, police_report, statement, photo
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ClaimReserve(Base):
    """Actuarial reserve ledger for claims."""

    __tablename__ = "claim_reserves"
    __table_args__ = {"schema": "claims"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reserve_type: Mapped[str] = mapped_column(
        String(30), default="initial", nullable=False
    )  # initial, revised, final
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
