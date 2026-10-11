"""SQLAlchemy models for the product module."""

import uuid
from datetime import UTC, date, datetime
from typing import Any

from app.db import Base
from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(UTC)


class Product(Base):
    """Insurance product line definition."""

    __tablename__ = "products"
    __table_args__ = {"schema": "product"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    line_of_business: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "motor", "property", "liability"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ProductVersion(Base):
    """Effective-dated version of an insurance product with tariffs and legal wording."""

    __tablename__ = "product_versions"
    __table_args__ = {"schema": "product"}

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    version_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="draft", nullable=False, index=True
    )  # "draft", "published", "archived"
    tariffs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    clauses: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
