"""SQLAlchemy models for the party module."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.db import Base
from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(UTC)


class Party(Base):
    """Customer, claimant, insured, or corporate entity."""

    __tablename__ = "parties"
    __table_args__ = {"schema": "party"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    party_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "individual" or "organization"
    tax_id: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )  # FIN or VÖEN
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    kyc_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, index=True
    )  # "pending", "verified", "rejected"
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Vehicle(Base):
    """Motor vehicle asset belonging to a party."""

    __tablename__ = "vehicles"
    __table_args__ = {"schema": "party"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    vin: Mapped[str] = mapped_column(String(17), unique=True, nullable=False, index=True)
    registration_number: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    make: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    manufacture_year: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_capacity_cc: Mapped[int] = mapped_column(Integer, nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Property(Base):
    """Real estate residential property asset belonging to a party."""

    __tablename__ = "properties"
    __table_args__ = {"schema": "party"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cadastral_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    build_year: Mapped[int] = mapped_column(Integer, nullable=False)
    construction_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # "brick", "concrete", "wooden"
    floor_area_sqm: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estimated_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Intermediary(Base):
    """Licensed broker or insurance agent."""

    __tablename__ = "intermediaries"
    __table_args__ = {"schema": "party"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    party_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    broker_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    license_number: Mapped[str] = mapped_column(String(50), nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), default=Decimal("0.1000"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
