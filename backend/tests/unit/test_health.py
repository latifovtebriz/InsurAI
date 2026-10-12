"""Unit tests for system health and readiness endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient


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
        assert "outbox_backlog" in data


def test_readiness_check_when_db_disconnected(client: TestClient) -> None:
    """Verifies that GET /ready returns 503 when database connectivity fails."""
    with patch("app.main.check_db_connectivity", return_value=False):
        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["database"] == "disconnected"


def test_metrics_endpoint(client: TestClient) -> None:
    """Verifies that GET /metrics exposes Prometheus formatted metrics."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "http_requests_total" in body
    assert "general_ledger_balance_difference" in body
    assert "agent_run_duration_seconds" in body
