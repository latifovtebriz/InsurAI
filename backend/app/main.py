"""InsurAI FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1.router import api_v1_router
from app.config import settings
from app.db import check_db_connectivity, get_db
from app.logging import setup_logging
from app.middleware import CorrelationIdMiddleware, MaxPayloadSizeMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Lifespan event handler for startup and shutdown."""
    setup_logging(settings.log_level)
    yield


app = FastAPI(
    title="InsurAI Core Platform API",
    description="Autonomous Agentic P&C Insurance Core System",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(MaxPayloadSizeMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Domain Routers
app.include_router(api_v1_router)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Liveness probe: verifies process is alive and responsive."""
    return {
        "status": "ok",
        "app": "insurai",
        "environment": settings.app_env,
    }


@app.get("/ready", tags=["System"])
def readiness_check(response: Response, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Readiness probe: verifies external dependencies (DB) and outbox health."""
    db_ok = check_db_connectivity()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "database": "disconnected",
            "detail": "Database engine is unreachable",
        }

    from sqlalchemy import func, select

    from app.modules.platform.public import OutboxEvent

    pending_outbox = (
        db.scalar(select(func.count(OutboxEvent.id)).where(OutboxEvent.status == "pending")) or 0
    )
    return {
        "status": "ready",
        "database": "connected",
        "outbox_backlog": pending_outbox,
    }


@app.get("/metrics", tags=["System"], response_class=Response)
def root_metrics(db: Session = Depends(get_db)) -> Response:
    """Standard Prometheus metrics exposition endpoint per Architecture 3.13."""
    from app.api.v1.metrics import format_prometheus_metrics

    return Response(
        content=format_prometheus_metrics(db),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
