"""SQLAlchemy models for the fraud detection and Special Investigation Unit (SIU) module."""

import uuid
from datetime import UTC, datetime

from app.db import Base
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class FraudSignalRecord(Base):
    """Specific fraud signal detected on a claim."""

    __tablename__ = "fraud_signals"
    __table_args__ = {"schema": "fraud"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    claim_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    claim_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    signal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    signal_name: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class SIUCase(Base):
    """Special Investigation Unit (SIU) referral case for suspicious or high-risk claims."""

    __tablename__ = "siu_cases"
    __table_args__ = {"schema": "fraud"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    claim_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="open", nullable=False, index=True
    )  # open, under_investigation, cleared, referred_legal, closed
    investigator_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    findings_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
