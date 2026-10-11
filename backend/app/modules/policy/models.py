"""SQLAlchemy models for the policy administration module."""

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
