"""SQLAlchemy models for the finance and double-entry accounting module."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.db import Base
from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Account(Base):
    """Chart of Accounts definition."""

    __tablename__ = "accounts"
    __table_args__ = {"schema": "finance"}

    account_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE
    normal_balance: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # DEBIT, CREDIT
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class GeneralLedgerTransaction(Base):
    """Header record for a double-entry accounting journal transaction."""

    __tablename__ = "gl_transactions"
    __table_args__ = {"schema": "finance"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    transaction_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reference_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # INVOICE_ISSUED, PAYMENT_RECEIVED, CLAIM_RESERVE, CLAIM_PAYOUT, COMMISSION_ACCRUAL, REINSURANCE_CESSION
    reference_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class GeneralLedgerEntry(Base):
    """Individual debit/credit line item belonging to a GeneralLedgerTransaction."""

    __tablename__ = "gl_entries"
    __table_args__ = {"schema": "finance"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    transaction_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    account_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    debit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    credit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00"), nullable=False
    )
    entry_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Invoice(Base):
    """Premium installment invoice issued to policyholder."""

    __tablename__ = "invoices"
    __table_args__ = {"schema": "finance"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    invoice_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    installment_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30), default="issued", nullable=False, index=True
    )  # issued, paid, overdue, cancelled
    dunning_level: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0=current, 1=T+7, 2=T+14, 3=T+30
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Payment(Base):
    """Payment received against an invoice."""

    __tablename__ = "payments"
    __table_args__ = {"schema": "finance"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    payment_reference: Mapped[str] = mapped_column(
        String(60), unique=True, nullable=False, index=True
    )
    invoice_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[str] = mapped_column(
        String(30), default="bank_transfer", nullable=False
    )  # bank_transfer, credit_card, debit_card, cash
    status: Mapped[str] = mapped_column(
        String(30), default="completed", nullable=False
    )  # completed, failed, refunded
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Disbursement(Base):
    """Claims payout disbursement requiring approval."""

    __tablename__ = "disbursements"
    __table_args__ = {"schema": "finance"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    disbursement_reference: Mapped[str] = mapped_column(
        String(60), unique=True, nullable=False, index=True
    )
    claim_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payee_party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="pending_approval", nullable=False, index=True
    )  # pending_approval, approved, disbursed, rejected
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    disbursed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Commission(Base):
    """Sales agent commission accrual."""

    __tablename__ = "commissions"
    __table_args__ = {"schema": "finance"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    agent_party_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="accrued", nullable=False
    )  # accrued, paid
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
