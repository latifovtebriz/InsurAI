"""Knowledge service database models for chunked policy wording and guidelines."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.db import Base
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON


def utcnow() -> datetime:
    return datetime.now(UTC)


class KBChunk(Base):
    """Semantic knowledge chunk representing a numbered clause or guideline section."""

    __tablename__ = "kb_chunks"
    __table_args__ = (
        UniqueConstraint(
            "collection", "product_code", "version", "clause_id", name="uq_kb_chunks_clause"
        ),
        {"schema": "platform"},
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    collection: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    clause_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    effective_from: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    effective_to: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
