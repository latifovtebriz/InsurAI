"""Shared pytest configuration, fixtures, and database setup."""

from collections.abc import Generator

import pytest
from app.db import Base, get_db
from app.main import app
from app.modules.claims.public import Claim, ClaimDocument, ClaimReserve  # noqa: F401
from app.modules.finance.public import (  # noqa: F401
    Account,
    Commission,
    Disbursement,
    GeneralLedgerEntry,
    GeneralLedgerTransaction,
    Invoice,
    Payment,
)
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
from app.modules.policy.public import Policy, PolicyCertificate, RenewalCase  # noqa: F401
from app.modules.product.public import Product, ProductVersion  # noqa: F401
from app.modules.reinsurance.public import (  # noqa: F401
    ReinsuranceCession,
    ReinsuranceRecovery,
    ReinsuranceTreaty,
)
from app.modules.sales.public import Lead, Quote  # noqa: F401
from app.modules.underwriting.public import UnderwritingCase  # noqa: F401
from fastapi.testclient import TestClient
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


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provides a TestClient with database session overridden."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()
