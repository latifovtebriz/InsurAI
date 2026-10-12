"""SQLAlchemy models for compliance, sanctions screening, and AML watchlist management."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.db import Base
from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class WatchlistEntity(Base):
    """Sanctions and politically exposed persons (PEP) watchlist entry."""

    __tablename__ = "watchlist_entities"
    __table_args__ = {"schema": "compliance"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(
        String(30), default="INDIVIDUAL", nullable=False
    )  # INDIVIDUAL, COMPANY
    list_name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # OFAC_SDN, UN_SANCTIONS, LOCAL_WATCHLIST, PEP
    tax_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ComplianceAlert(Base):
    """Compliance alert triggered by fuzzy sanctions or PEP match."""

    __tablename__ = "compliance_alerts"
    __table_args__ = {"schema": "compliance"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    party_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    matched_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    matched_entity_name: Mapped[str] = mapped_column(String(150), nullable=False)
    match_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    match_reasons: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40), default="open", nullable=False, index=True
    )  # open, under_review, confirmed_hit, false_positive_cleared_by_officer
    assigned_officer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    officer_decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
