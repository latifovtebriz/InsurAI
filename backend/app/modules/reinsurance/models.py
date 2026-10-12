"""SQLAlchemy models for the reinsurance module."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.db import Base
from sqlalchemy import Boolean, Date, DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class ReinsuranceTreaty(Base):
    """Reinsurance treaty contract (Quota Share or Excess of Loss)."""

    __tablename__ = "treaties"
    __table_args__ = {"schema": "reinsurance"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    treaty_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    treaty_name: Mapped[str] = mapped_column(String(100), nullable=False)
    treaty_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # QUOTA_SHARE, EXCESS_OF_LOSS
    product_code: Mapped[str] = mapped_column(
        String(50), default="ALL", nullable=False, index=True
    )  # MOTOR_OD, HOME, ALL
    reinsurer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    retention_share_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.8000"), nullable=False
    )
    ceded_share_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.2000"), nullable=False
    )
    retention_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    treaty_limit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("500000.00"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ReinsuranceCession(Base):
    """Premium cession record under an active treaty."""

    __tablename__ = "cessions"
    __table_args__ = {"schema": "reinsurance"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    treaty_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    treaty_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    gross_premium: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    ceded_premium: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_premium: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cession_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ReinsuranceRecovery(Base):
    """Claim recovery allocation from a reinsurance treaty."""

    __tablename__ = "recoveries"
    __table_args__ = {"schema": "reinsurance"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    treaty_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    treaty_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    claim_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    gross_loss: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    retention_deducted: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    recovered_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_loss: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="accrued", nullable=False
    )  # accrued, collected
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
