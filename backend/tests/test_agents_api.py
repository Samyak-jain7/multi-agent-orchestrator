"""
Tests for /api/v1/agents endpoints.
Covers: POST (happy/422/409), GET list (empty/items), GET {id} (found/404),
PUT update (notfound), DELETE (success/notfound), auth header (missing/wrong/right).
"""
import pytest
from httpx import ASGITransport, AsyncClient


class TestAgentsCreate:
    """POST /api/v1/agents"""

    async def test_create_agent_success(self, client: AsyncClient, sample_agent_data: dict):
        response = await client.post("/api/v1/agents", json=sample_agent_data)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_agent_data["name"]
        assert data["model_provider"] == "minimax"
        assert data["model_name"] == "MiniMax-M2.7"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.parametrize("missing_field", ["name", "system_prompt"])
    async def test_create_agent_missing_required_field(
        self, client: AsyncClient, missing_field: str, sample_agent_data: dict
    ):
        del sample_agent_data[missing_field]
        response = await client.post("/api/v1/agents", json=sample_agent_data)
        assert response.status_code == 422

    async def test_create_agent_name_too_long(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "x" * 200,
                "system_prompt": "You are helpful.",
                "model_provider": "minimax",
                "model_name": "MiniMax-M2.7",
            },
        )
        assert response.status_code == 422

    async def test_create_agent_system_prompt_too_short(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Short Prompt Agent",
                "system_prompt": "",
                "model_provider": "minimax",
                "model_name": "MiniMax-M2.7",
            },
        )
        assert response.status_code == 422

    async def test_create_agent_invalid_provider(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/agents",
            json={
                "name": "Bad Provider Agent",
                "system_prompt": "You are helpful.",
                "model_provider": "invalid_provider",
                "model_name": "MiniMax-M2.7",
            },
        )
        assert response.status_code == 422

    async def test_create_agent_duplicate_name_not_conflict(
        self, client: AsyncClient, sample_agent_data: dict
    ):
        """Names are not unique constraints – two agents can share a name."""
        r1 = await client.post("/api/v1/agents", json=sample_agent_data)
        assert r1.status_code == 201
        r2 = await client.post("/api/v1/agents", json=sample_agent_data)
        assert r2.status_code == 201


class TestAgentsList:
    """GET /api/v1/agents"""

    async def test_list_agents_empty(self, client: AsyncClient):
        response = await client.get("/api/v1/agents")
        assert response.status_code == 200
        assert response.json() == []

    async def test_list_agents_with_items(self, client: AsyncClient, sample_agent):
        response = await client.get("/api/v1/agents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == sample_agent.id

    @pytest.mark.parametrize("skip,limit,expected", [(0, 1, 1), (1, 10, 0), (0, 0, 422)])
    async def test_list_agents_pagination(
        self, client: AsyncClient, sample_agent, skip: int, limit: int, expected: int
    ):
        response = await client.get(f"/api/v1/agents?skip={skip}&limit={limit}")
        if expected == 422:
            assert response.status_code == 422
        else:
            assert response.status_code == 200
            assert len(response.json()) == expected


class TestAgentsGet:
    """GET /api/v1/agents/{agent_id}"""

    async def test_get_agent_found(self, client: AsyncClient, sample_agent):
        response = await client.get(f"/api/v1/agents/{sample_agent.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_agent.id
        assert data["name"] == sample_agent.name

    async def test_get_agent_not_found(self, client: AsyncClient):
        response = await client.get("/api/v1/agents/nonexistent-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestAgentsUpdate:
    """PUT /api/v1/agents/{agent_id}"""

    async def test_update_agent_success(self, client: AsyncClient, sample_agent):
        response = await client.put(
            f"/api/v1/agents/{sample_agent.id}",
            json={"name": "Updated Agent Name"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Agent Name"

    async def test_update_agent_not_found(self, client: AsyncClient):
        response = await client.put(
            "/api/v1/agents/nonexistent-id",
            json={"name": "Should Not Work"},
        )
        assert response.status_code == 404

    async def test_update_agent_partial(self, client: AsyncClient, sample_agent):
        """Only name updated, other fields unchanged."""
        response = await client.put(
            f"/api/v1/agents/{sample_agent.id}",
            json={"description": "New description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_agent.name
        assert data["description"] == "New description"

    async def test_update_agent_invalid_provider(self, client: AsyncClient, sample_agent):
        response = await client.put(
            f"/api/v1/agents/{sample_agent.id}",
            json={"model_provider": "invalid"},
        )
        assert response.status_code == 422


class TestAgentsDelete:
    """DELETE /api/v1/agents/{agent_id}"""

    async def test_delete_agent_success(self, client: AsyncClient, sample_agent):
        response = await client.delete(f"/api/v1/agents/{sample_agent.id}")
        assert response.status_code == 204
        # Verify it's gone
        response2 = await client.get(f"/api/v1/agents/{sample_agent.id}")
        assert response2.status_code == 404

    async def test_delete_agent_not_found(self, client: AsyncClient):
        response = await client.delete("/api/v1/agents/nonexistent-id")
        assert response.status_code == 404


class TestAgentsAuth:
    """Auth header enforcement on agent endpoints."""

    async def test_create_agent_no_auth_header(self, app, sample_agent_data: dict):
        """Without X-API-Key header, request should be rejected."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/agents", json=sample_agent_data)
        assert response.status_code == 403

    async def test_create_agent_wrong_auth_header(self, app, sample_agent_data: dict):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": "wrong-key"},
        ) as ac:
            response = await ac.post("/api/v1/agents", json=sample_agent_data)
        assert response.status_code == 403

    async def test_create_agent_correct_auth_header(self, client: AsyncClient, sample_agent_data: dict):
        response = await client.post("/api/v1/agents", json=sample_agent_data)
        assert response.status_code == 201

    async def test_get_agent_no_auth(self, app, sample_agent):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get(f"/api/v1/agents/{sample_agent.id}")
        assert response.status_code == 403

    async def test_list_agents_no_auth(self, app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/api/v1/agents")
        assert response.status_code == 403

    async def test_list_agents_with_correct_auth(self, client: AsyncClient, sample_agent):
        response = await client.get("/api/v1/agents")
        assert response.status_code == 200

    async def test_delete_agent_no_auth(self, app, sample_agent):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.delete(f"/api/v1/agents/{sample_agent.id}")
        assert response.status_code == 403
