from collections.abc import Generator

import pytest
from app.db import Base
from app.modules.platform.knowledge.models import KBChunk
from app.modules.platform.knowledge.service import KnowledgeService
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from data.synthetic.products_catalog import PRODUCTS_DATA


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Isolated SQLite in-memory DB with schema translation."""
    engine = create_engine(
        "sqlite:///:memory:",
        execution_options={"schema_translate_map": {"platform": None}},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_wording_ingestion_idempotency(db_session: Session) -> None:
    """Verifies that re-ingesting product versions does not duplicate chunks."""
    svc = KnowledgeService()
    motor_od = next(p for p in PRODUCTS_DATA if p.product_code == "MOTOR_OD")

    # Ingest once
    count_1 = svc.ingest_product_wording(db_session, motor_od)
    total_1 = db_session.scalars(select(KBChunk)).all()
    assert count_1 > 0
    assert len(total_1) == count_1

    # Ingest a second time
    count_2 = svc.ingest_product_wording(db_session, motor_od)
    total_2 = db_session.scalars(select(KBChunk)).all()

    # No new chunks added
    assert count_2 == 0
    assert len(total_2) == len(total_1)


def test_time_travel_effective_dating_retrieval(db_session: Session) -> None:
    """
    CRITICAL TIME-TRAVEL TEST:
    A claim with incident date in 2025 MUST retrieve v1 clauses even when v2 is present.
    A claim with incident date in 2026 MUST retrieve v2 clauses.
    """
    svc = KnowledgeService()
    svc.ingest_all_catalogs(db_session)

    # 1. Historical incident in 2025 (Governed by v1 2025 wording)
    citations_2025 = svc.search_policy_wording(
        session=db_session,
        query="collision with barrier on road",
        product_code="MOTOR_OD",
        incident_date="2025-07-20",
        top_k=5,
    )
    assert len(citations_2025) > 0
    for c in citations_2025:
        # Must be Version 1
        assert c.product_version == 1

    # Version 2 clause (B.7 cyber exclusion) must NOT be present in 2025
    cyber_2025 = svc.search_policy_wording(
        session=db_session,
        query="remote cyber interference and ECU firmware tampering",
        product_code="MOTOR_OD",
        incident_date="2025-07-20",
        top_k=5,
    )
    assert all(c.clause_id != "MOTOR_OD:B.7" for c in cyber_2025)

    # 2. Modern incident in 2026 (Governed by v2 2026 wording)
    citations_2026 = svc.search_policy_wording(
        session=db_session,
        query="collision with barrier on road",
        product_code="MOTOR_OD",
        incident_date="2026-05-10",
        top_k=5,
    )
    assert len(citations_2026) > 0
    for c in citations_2026:
        # Must be Version 2
        assert c.product_version == 2

    # Cyber exclusion B.7 CAN be retrieved in 2026!
    cyber_2026 = svc.search_policy_wording(
        session=db_session,
        query="remote cyber interference and ECU firmware tampering",
        product_code="MOTOR_OD",
        incident_date="2026-05-10",
        top_k=5,
    )
    assert any(c.clause_id == "MOTOR_OD:B.7" for c in cyber_2026)


def test_metadata_isolation_across_products(db_session: Session) -> None:
    """Verifies that retrieval for MOTOR_OD never returns HOME or MOTOR_TPL clauses."""
    svc = KnowledgeService()
    svc.ingest_all_catalogs(db_session)

    citations = svc.search_policy_wording(
        session=db_session,
        query="fire in kitchen apartment water leak",
        product_code="MOTOR_OD",
        incident_date="2026-06-01",
        top_k=5,
    )
    for c in citations:
        assert c.clause_id.startswith("MOTOR_OD:")
        assert not c.clause_id.startswith("HOME:")
