"""SQLAlchemy models for the underwriting module."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.db import Base
from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(UTC)


class UnderwritingCase(Base):
    """Underwriting referral case requiring human assessment or copilot assistance."""

    __tablename__ = "cases"
    __table_args__ = {"schema": "underwriting"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    quote_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sum_insured: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    proposed_premium: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="pending_review", nullable=False, index=True
    )  # pending_review, approved_standard, approved_with_conditions, declined, referred_senior
    assigned_underwriter_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    authority_tier_required: Mapped[str] = mapped_column(
        String(20), default="junior", nullable=False
    )  # junior, senior, chief
    rule_hits: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    risk_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    copilot_assessment: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    underwriter_decision: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
