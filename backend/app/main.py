"""InsurAI FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import check_db_connectivity
from app.logging import setup_logging
from app.middleware import CorrelationIdMiddleware


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Liveness probe: verifies process is alive and responsive."""
    return {
        "status": "ok",
        "app": "insurai",
        "environment": settings.app_env,
    }


@app.get("/ready", tags=["System"])
def readiness_check(response: Response) -> dict[str, str]:
    """Readiness probe: verifies external dependencies (DB) are reachable."""
    db_ok = check_db_connectivity()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "database": "disconnected",
        }
    return {
        "status": "ready",
        "database": "connected",
    }
