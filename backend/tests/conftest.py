"""Shared pytest configuration, fixtures, and database setup."""

from collections.abc import Generator

import pytest
from app.db import Base
from app.modules.claims.public import Claim, ClaimDocument, ClaimReserve  # noqa: F401
from app.modules.party.public import Intermediary, Party, Property, Vehicle  # noqa: F401
from app.modules.platform.public import (  # noqa: F401
    AgentRun,
    AgentStep,
    AuditLog,
    BusinessRuleModel,
    Job,
    OutboxEvent,
    ProcessedEvent,
    RolePermission,
    User,
)
from app.modules.policy.public import Policy, PolicyCertificate  # noqa: F401
from app.modules.product.public import Product, ProductVersion  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

SCHEMA_TRANSLATE_MAP: dict[str, None] = {
    "platform": None,
    "party": None,
    "product": None,
    "policy": None,
    "claims": None,
    "sales": None,
    "underwriting": None,
    "finance": None,
    "fraud": None,
    "compliance": None,
    "service": None,
    "reinsurance": None,
}


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides an isolated SQLite in-memory session with all schemas translated to flat namespace."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        execution_options={"schema_translate_map": SCHEMA_TRANSLATE_MAP},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
