"""Database engine and session management."""

import logging
from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

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


def _create_app_engine() -> Any:
    """Creates database engine with automatic zero-hang fallback to SQLite if PostgreSQL is unreachable."""
    if "sqlite" in settings.database_url:
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            execution_options={"schema_translate_map": SCHEMA_TRANSLATE_MAP},
            pool_pre_ping=True,
            echo=False,
        )

    # Fast probe: check if PostgreSQL port is open
    import socket

    is_pg_up = False
    try:
        with socket.create_connection(("localhost", 5432), timeout=0.5):
            is_pg_up = True
    except (OSError, TimeoutError):
        is_pg_up = False

    if is_pg_up:
        try:
            pg_eng = create_engine(
                settings.database_url,
                pool_pre_ping=True,
                echo=False,
            )
            with pg_eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return pg_eng
        except Exception:
            pass

    logger.info("PostgreSQL service is offline. Running with standalone demo SQLite database.")
    return create_engine(
        "sqlite:///insurai_demo.db",
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": SCHEMA_TRANSLATE_MAP},
        pool_pre_ping=True,
        echo=False,
    )


engine = _create_app_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy entities."""

    pass


def get_db() -> Generator[Session, None, None]:
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connectivity() -> bool:
    """Verifies database connectivity with a simple SELECT 1 query."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning(f"Database connectivity check failed: {exc}")
        return False
