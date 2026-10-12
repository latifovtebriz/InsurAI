"""SQLAlchemy models for the policy administration module."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from app.db import Base
from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(UTC)


class Policy(Base):
    """Core insurance policy contract."""

    __tablename__ = "policies"
    __table_args__ = {"schema": "policy"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )  # vehicle or property
    product_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_version_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default="draft", nullable=False, index=True
    )  # draft, quoted, bound, pending_payment, active, cancelled, expired
    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sum_insured: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    deductible: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("200.00"), nullable=False
    )
    total_premium: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    paid_premium: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    payment_schedule: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class PolicyCertificate(Base):
    """Legal Certificate of Insurance and document integrity ledger."""

    __tablename__ = "policy_certificates"
    __table_args__ = {"schema": "policy"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    certificate_number: Mapped[str] = mapped_column(
        String(60), unique=True, nullable=False, index=True
    )
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 digest
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class RenewalCase(Base):
    """Annual policy renewal review, claim loss rating, and statutory notice enforcement."""

    __tablename__ = "renewal_cases"
    __table_args__ = {"schema": "policy"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    current_end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    days_to_expiry: Mapped[int] = mapped_column(Integer, nullable=False)
    claims_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_claims_incurred: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    current_premium: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    proposed_premium: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    recommendation: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # STANDARD_RENEWAL, SURCHARGED_RENEWAL, NON_RENEWAL
    status: Mapped[str] = mapped_column(
        String(30), default="pending_review", nullable=False, index=True
    )  # pending_review, offer_generated, non_renewal_alert, accepted, declined
    notice_deadline: Mapped[date] = mapped_column(Date, nullable=False)  # T-30 statutory deadline
    notice_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    statutory_deadline_breached: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    advisor_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    underwriter_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
