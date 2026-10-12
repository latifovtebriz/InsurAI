"""SQLAlchemy models for the sales module."""

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


class Lead(Base):
    """Prospective insurance customer lead."""

    __tablename__ = "leads"
    __table_args__ = {"schema": "sales"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(
        String(30), default="web", nullable=False
    )  # web, agent, broker, chat
    status: Mapped[str] = mapped_column(
        String(30), default="new", nullable=False, index=True
    )  # new, qualified, quoted, converted, lost
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Quote(Base):
    """Itemized insurance quotation."""

    __tablename__ = "quotes"
    __table_args__ = {"schema": "sales"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quote_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    lead_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    party_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default="draft", nullable=False, index=True
    )  # draft, offered, referred_to_uw, accepted, declined, expired
    sum_insured: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deductible: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    total_premium: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    rating_inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    installment_options: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    valid_until: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    underwriting_case_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
