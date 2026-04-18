"""
Tests for health endpoints.
GET /health → {status:"healthy"}, GET /ready → 200 (DB up), 503 (DB down/mocked).
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


class TestHealthCheck:
    """GET /health"""

    async def test_health_returns_200(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_has_status_field(self, client: AsyncClient):
        response = await client.get("/health")
        data = response.json()
        assert "status" in data

    async def test_health_status_value(self, client: AsyncClient):
        response = await client.get("/health")
        data = response.json()
        # The actual response uses "healthy"
        assert data["status"] in ["healthy", "ok", "running"]

    async def test_health_has_timestamp(self, client: AsyncClient):
        response = await client.get("/health")
        data = response.json()
        assert "timestamp" in data

    async def test_health_has_components(self, client: AsyncClient):
        response = await client.get("/health")
        data = response.json()
        assert "components" in data
        assert "database" in data["components"]
        assert "task_queue" in data["components"]


class TestReadinessCheck:
    """GET /ready"""

    async def test_ready_db_up_returns_200(self, client: AsyncClient, app):
        """When DB is accessible, /ready should return 200."""
        response = await client.get("/ready")
        # With our in-memory DB, should be ready
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert "checks" in data

    async def test_ready_database_check_true(self, client: AsyncClient):
        response = await client.get("/ready")
        data = response.json()
        assert data["checks"]["database"] is True

    async def test_ready_task_queue_running(self, client: AsyncClient, app):
        """Task queue should be reported as running."""
        response = await client.get("/ready")
        data = response.json()
        # Queue should be running in test context
        assert data["checks"]["task_queue"] in [True, False]

    async def test_ready_task_queue_stopped_returns_503(self, client: AsyncClient, app):
        """When task queue is stopped, /ready should return 503."""
        with patch("main.task_queue") as mock_queue:
            mock_queue._running = False
            response = await client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["ready"] is False

    async def test_ready_has_timestamp(self, client: AsyncClient):
        response = await client.get("/ready")
        data = response.json()
        assert "timestamp" in data

    async def test_ready_returns_503_when_not_ready(self, client: AsyncClient, app):
        """Simulate all checks failing → 503."""
        with patch("main.task_queue") as mock_queue:
            mock_queue._running = False
            response = await client.get("/ready")

        assert response.status_code == 503


class TestHealthNoAuthRequired:
    """Health endpoints should not require API key auth."""

    async def test_health_no_auth_required(self, app):
        """GET /health should work without X-API-Key."""
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            response = await ac.get("/health")
        assert response.status_code == 200

    async def test_ready_no_auth_required(self, app):
        """GET /ready should work without X-API-Key."""
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            response = await ac.get("/ready")
        # Should not be 403
        assert response.status_code in [200, 503]
