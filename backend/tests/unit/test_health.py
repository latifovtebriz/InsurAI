"""Unit tests for system health and readiness endpoints."""

from unittest.mock import patch

import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_health_check_returns_200(client: TestClient) -> None:
    """Verifies that GET /health returns HTTP 200 with ok status and correlation ID."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "insurai"
    assert "X-Correlation-ID" in response.headers


def test_readiness_check_when_db_connected(client: TestClient) -> None:
    """Verifies that GET /ready returns 200 when database connectivity succeeds."""
    with patch("app.main.check_db_connectivity", return_value=True):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"


def test_readiness_check_when_db_disconnected(client: TestClient) -> None:
    """Verifies that GET /ready returns 503 when database connectivity fails."""
    with patch("app.main.check_db_connectivity", return_value=False):
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"
